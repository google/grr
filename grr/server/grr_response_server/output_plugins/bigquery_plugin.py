#!/usr/bin/env python
"""BigQuery output plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import json
import logging
import os
import tempfile


from future.utils import itervalues

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2
from grr_response_server import bigquery
from grr_response_server import export
from grr_response_server import output_plugin


class TempOutputTracker(object):
  """Track temp output files for BigQuery JSON data and schema."""

  def __init__(self,
               output_type=None,
               gzip_filehandle=None,
               gzip_filehandle_parent=None,
               schema=None):
    """Create tracker.

    This class is used to track a gzipped filehandle for each type of output
    (e.g. ExportedFile) during ProcessResponses. Then during Flush the data
    from the temp file is sent to bigquery. Flush is guaranteed to be called on
    the same worker so holding local file references is OK.

    Args:
      output_type: string, e.g. "ExportedFile"
      gzip_filehandle: open handle to a gzip.GzipFile opened on
        gzip_filehandle_parent. JSON data will be written here.
      gzip_filehandle_parent: open parent filehandle for gzip_filehandle.
        Reading from this handle gives you the gzip content.
      schema: Bigquery schema, array of dicts
    """
    self.output_type = output_type
    self.gzip_filehandle = gzip_filehandle
    self.schema = schema
    self.gzip_filehandle_parent = gzip_filehandle_parent


class BigQueryOutputPluginArgs(rdf_structs.RDFProtoStruct):
  protobuf = output_plugin_pb2.BigQueryOutputPluginArgs
  rdf_deps = [
      export.ExportOptions,
  ]


class BigQueryOutputPlugin(output_plugin.OutputPlugin):
  """Output plugin that uploads hunt results to BigQuery.

  We write gzipped JSON data and a BigQuery schema to temporary files. One file
  for each output type is created during ProcessResponses, then we upload the
  data and schema to BigQuery during Flush. On failure we retry a few times.

  We choose JSON output for BigQuery so we can support simply export fields that
  contain newlines, including when users choose to export file content. This is
  a bigquery recommendation for performance:
  https://cloud.google.com/bigquery/preparing-data-for-bigquery?hl=en
  """

  name = "bigquery"
  description = "Send output to bigquery."
  args_type = BigQueryOutputPluginArgs
  GZIP_COMPRESSION_LEVEL = 9
  RDF_BIGQUERY_TYPE_MAP = {
      "bool": "BOOLEAN",
      "float": "FLOAT",
      "uint32": "INTEGER",
      "uint64": "INTEGER"
  }

  def __init__(self, *args, **kwargs):
    super(BigQueryOutputPlugin, self).__init__(*args, **kwargs)
    self.temp_output_trackers = {}
    self.output_jobids = {}
    self.failure_count = 0

  def InitializeState(self, state):
    # Total number of BigQuery upload failures.
    state.failure_count = 0

  def UpdateState(self, state):
    state.failure_count += self.failure_count

  def ProcessResponses(self, state, responses):
    default_metadata = export.ExportedMetadata(
        annotations=u",".join(self.args.export_options.annotations),
        source_urn=self.source_urn)

    if self.args.convert_values:
      # This is thread-safe - we just convert the values.
      converted_responses = export.ConvertValues(
          default_metadata,
          responses,
          token=self.token,
          options=self.args.export_options)
    else:
      converted_responses = responses

    # This is not thread-safe, therefore WriteValueToJSONFile is synchronized.
    self.WriteValuesToJSONFile(state, converted_responses)

  def _GetNestedDict(self, value):
    """Turn Exported* protos with embedded metadata into a nested dict."""
    row = {}
    for type_info in value.__class__.type_infos:
      # We only expect the metadata proto to be included as ProtoEmbedded.
      if type_info.__class__.__name__ == "ProtoEmbedded":
        row[type_info.name] = self._GetNestedDict(value.Get(type_info.name))
      else:
        row[type_info.name] = utils.SmartStr(value.Get(type_info.name))

    return row

  def _WriteJSONValue(self, output_file, value, delimiter=None):
    if delimiter:
      output_file.write("{0}{1}".format(delimiter,
                                        json.dumps(self._GetNestedDict(value))))
    else:
      output_file.write(json.dumps(self._GetNestedDict(value)))

  def _CreateOutputFileHandles(self, output_type):
    """Creates a new gzipped output tempfile for the output type.

    We write to JSON data to gzip_filehandle to get compressed data. We hold a
    reference to the original filehandle (gzip_filehandle_parent) so we can pass
    the gzip data to bigquery.

    Args:
      output_type: string of export type to be used in filename. e.g.
        ExportedFile

    Returns:
      A TempOutputTracker object
    """
    gzip_filehandle_parent = tempfile.NamedTemporaryFile(suffix=output_type)
    gzip_filehandle = gzip.GzipFile(gzip_filehandle_parent.name, "wb",
                                    self.GZIP_COMPRESSION_LEVEL,
                                    gzip_filehandle_parent)
    self.temp_output_trackers[output_type] = TempOutputTracker(
        output_type=output_type,
        gzip_filehandle=gzip_filehandle,
        gzip_filehandle_parent=gzip_filehandle_parent)
    return self.temp_output_trackers[output_type]

  def _GetTempOutputFileHandles(self, value_type):
    """Returns the tracker for a given value type."""
    try:
      return self.temp_output_trackers[value_type], False
    except KeyError:
      return self._CreateOutputFileHandles(value_type), True

  def Flush(self, state):
    """Finish writing JSON files, upload to cloudstorage and bigquery."""
    self.bigquery = bigquery.GetBigQueryClient()
    # BigQuery job ids must be alphanum plus dash and underscore.
    urn_str = self.source_urn.RelativeName("aff4:/").replace("/", "_").replace(
        ":", "").replace(".", "-")

    for tracker in itervalues(self.temp_output_trackers):
      # Close out the gzip handle and pass the original file handle to the
      # bigquery client so it sees the gzip'd content.
      tracker.gzip_filehandle.write("\n")
      tracker.gzip_filehandle.close()
      tracker.gzip_filehandle_parent.seek(0)

      # e.g. job_id: hunts_HFFE1D044_Results_ExportedFile_1446056474
      job_id = "{0}_{1}_{2}".format(
          urn_str, tracker.output_type,
          rdfvalue.RDFDatetime.Now().AsSecondsSinceEpoch())

      # If we have a job id stored, that means we failed last time. Re-use the
      # job id and append to the same file if it continues to fail. This avoids
      # writing many files on failure.
      if tracker.output_type in self.output_jobids:
        job_id = self.output_jobids[tracker.output_type]
      else:
        self.output_jobids[tracker.output_type] = job_id

      if (state.failure_count + self.failure_count >=
          config.CONFIG["BigQuery.max_upload_failures"]):
        logging.error(
            "Exceeded BigQuery.max_upload_failures for %s, giving up.",
            self.source_urn)
      else:
        try:
          self.bigquery.InsertData(tracker.output_type,
                                   tracker.gzip_filehandle_parent,
                                   tracker.schema, job_id)
          self.failure_count = max(0, self.failure_count - 1)
          del self.output_jobids[tracker.output_type]
        except bigquery.BigQueryJobUploadError:
          self.failure_count += 1

    # Now that everything is in bigquery we can remove the output streams
    self.temp_output_trackers = {}

  def RDFValueToBigQuerySchema(self, value):
    """Convert Exported* rdfvalue into a BigQuery schema."""
    fields_array = []
    for type_info in value.__class__.type_infos:
      # Nested structures are indicated by setting type "RECORD"
      if type_info.__class__.__name__ == "ProtoEmbedded":
        fields_array.append({
            "name": type_info.name,
            "type": "RECORD",
            "description": type_info.description,
            "fields": self.RDFValueToBigQuerySchema(value.Get(type_info.name))
        })
      else:
        # If we don't have a specific map use string.
        bq_type = self.RDF_BIGQUERY_TYPE_MAP.get(type_info.proto_type_name,
                                                 None) or "STRING"

        # For protos with RDF types we need to do some more checking to properly
        # covert types.
        if hasattr(type_info, "original_proto_type_name"):
          if type_info.original_proto_type_name in [
              "RDFDatetime", "RDFDatetimeSeconds"
          ]:
            bq_type = "TIMESTAMP"
          elif type_info.proto_type_name == "uint64":
            # This is to catch fields like st_mode which are stored as ints but
            # exported as more useful strings. Things which are just plain ints
            # won't have an RDF type specified and so will be exported as
            # INTEGER
            bq_type = "STRING"

        fields_array.append({
            "name": type_info.name,
            "type": bq_type,
            "description": type_info.description
        })
    return fields_array

  @utils.Synchronized
  def WriteValuesToJSONFile(self, state, values):
    """Write newline separated JSON dicts for each value.

    We write each dict separately so we don't have to hold all of the output
    streams in memory. We open and close the JSON array manually with [].

    Args:
      state: rdf_protodict.AttributedDict with the plugin's state.
      values: RDF values to export.
    """
    value_counters = {}
    max_post_size = config.CONFIG["BigQuery.max_file_post_size"]
    for value in values:
      class_name = value.__class__.__name__
      output_tracker, created = self._GetTempOutputFileHandles(class_name)

      # If our output stream is getting huge we should flush everything now and
      # set up new output files. Only start checking when we are getting within
      # range of the limit because we need to flush the stream to check the
      # size. Start counting at 0 so we check each file the first time.
      value_counters[class_name] = value_counters.get(class_name, -1) + 1
      if not value_counters[class_name] % max_post_size // 1000:

        # Flush our temp gzip handle so we can stat it to see how big it is.
        output_tracker.gzip_filehandle.flush()
        if os.path.getsize(output_tracker.gzip_filehandle.name) > max_post_size:
          # Flush what we have and get new temp output handles.
          self.Flush(state)
          value_counters[class_name] = 0
          output_tracker, created = self._GetTempOutputFileHandles(class_name)

      if not output_tracker.schema:
        output_tracker.schema = self.RDFValueToBigQuerySchema(value)

      if created:
        # Omit the leading newline for the first entry in the file.
        self._WriteJSONValue(output_tracker.gzip_filehandle, value)
      else:
        self._WriteJSONValue(
            output_tracker.gzip_filehandle, value, delimiter="\n")

    for output_tracker in itervalues(self.temp_output_trackers):
      output_tracker.gzip_filehandle.flush()
