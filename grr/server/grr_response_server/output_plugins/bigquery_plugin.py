#!/usr/bin/env python
"""BigQuery output plugin."""

import gzip
import json
import logging
import os
import tempfile


from grr import config
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2
from grr.server.grr_response_server import bigquery
from grr.server.grr_response_server import export
from grr.server.grr_response_server import output_plugin


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


class BigQueryOutputPlugin(output_plugin.OutputPluginWithOutputStreams):
  """Output plugin that uploads hunt results to BigQuery.

  We write gzipped JSON data and a BigQuery schema to temporary files. One file
  for each output type is created during ProcessResponses, then we upload the
  data and schema to BigQuery during Flush.

  On failure we retry a few times. If that doesn't work we fall back to writing
  the same data to AFF4 so that the user can upload to BigQuery manually later.

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

  def InitializeState(self):
    super(BigQueryOutputPlugin, self).InitializeState()
    # The last job ID if there was a failure. Keys are output types.
    self.state.output_jobids = {}
    # Total number of BigQuery upload failures.
    self.state.failure_count = 0

  def ProcessResponses(self, responses):
    default_metadata = export.ExportedMetadata(
        annotations=u",".join(self.args.export_options.annotations),
        source_urn=self.state.source_urn)

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
    self.WriteValuesToJSONFile(converted_responses)

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
      output_file.write(
          "{0}{1}".format(delimiter, json.dumps(self._GetNestedDict(value))))
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
    """Initializes output AFF4Image for a given value type."""
    try:
      return self.temp_output_trackers[value_type], False
    except KeyError:
      return self._CreateOutputFileHandles(value_type), True

  def _WriteToAFF4(self, job_id, schema, gzip_filehandle_parent, token):
    """When upload to bigquery fails, write to AFF4."""
    with self._CreateOutputStream(
        ".".join((job_id, "schema"))) as schema_stream:

      logging.error("Upload to bigquery failed, will write schema to %s",
                    schema_stream.urn)

      # Only need to write the schema once.
      if schema_stream.size == 0:
        schema_stream.write(json.dumps(schema))

    with self._CreateOutputStream(".".join((job_id, "data"))) as data_stream:

      logging.error("Upload to bigquery failed, will write results to %s",
                    data_stream.urn)

      gzip_filehandle_parent.flush()
      gzip_filehandle_parent.seek(0)
      for line in gzip_filehandle_parent:
        data_stream.write(line)

  def Flush(self):
    """Finish writing JSON files, upload to cloudstorage and bigquery."""
    self.bigquery = bigquery.GetBigQueryClient()
    # BigQuery job ids must be alphanum plus dash and underscore.
    urn_str = self.state.source_urn.RelativeName("aff4:/").replace(
        "/", "_").replace(":", "").replace(".", "-")

    for tracker in self.temp_output_trackers.values():
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
      if tracker.output_type in self.state.output_jobids:
        job_id = self.state.output_jobids[tracker.output_type]
      else:
        self.state.output_jobids[tracker.output_type] = job_id

      if (self.state.failure_count >=
          config.CONFIG["BigQuery.max_upload_failures"]):
        logging.error("Exceeded BigQuery.max_upload_failures for %s. Giving up "
                      "on BigQuery and writing to AFF4.", self.state.source_urn)
        self._WriteToAFF4(job_id, tracker.schema,
                          tracker.gzip_filehandle_parent, self.token)

      else:
        try:
          self.bigquery.InsertData(tracker.output_type,
                                   tracker.gzip_filehandle_parent,
                                   tracker.schema, job_id)
          self.state.failure_count = max(0, self.state.failure_count - 1)
          del self.state.output_jobids[tracker.output_type]
        except bigquery.BigQueryJobUploadError:
          self.state.failure_count += 1

          self._WriteToAFF4(job_id, tracker.schema,
                            tracker.gzip_filehandle_parent, self.token)

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
  def WriteValuesToJSONFile(self, values):
    """Write newline separated JSON dicts for each value.

    We write each dict separately so we don't have to hold all of the output
    streams in memory. We open and close the JSON array manually with [].

    Args:
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
          self.Flush()
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

    for output_tracker in self.temp_output_trackers.values():
      output_tracker.gzip_filehandle.flush()
