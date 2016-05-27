#!/usr/bin/env python
"""CSV single-pass output plugin."""



import csv

from grr.lib import export
from grr.lib import output_plugin
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import output_plugin_pb2


class CSVOutputPluginArgs(rdf_structs.RDFProtoStruct):
  protobuf = output_plugin_pb2.CSVOutputPluginArgs


class CSVOutputPlugin(output_plugin.OutputPluginWithOutputStreams):
  """Output plugin that writes hunt's results to a CSV file."""

  name = "csv"
  description = "Output ZIP archive with CSV files."
  args_type = CSVOutputPluginArgs

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

    # This is not thread-safe, therefore WriteValueToCSVFile is synchronized.
    self.WriteValuesToCSVFile(converted_responses)

  def GetCSVHeader(self, value_class, prefix=""):
    header = []
    for type_info in value_class.type_infos:
      if type_info.__class__.__name__ == "ProtoEmbedded":
        header.extend(self.GetCSVHeader(type_info.type,
                                        prefix=type_info.name + "."))
      else:
        header.append(utils.SmartStr(prefix + type_info.name))

    return header

  def WriteCSVHeader(self, output_file, value_type):
    value_class = rdfvalue.RDFValue.classes[value_type]
    csv.writer(output_file).writerow(self.GetCSVHeader(value_class))

  def GetCSVRow(self, value):
    row = []
    for type_info in value.__class__.type_infos:
      if type_info.__class__.__name__ == "ProtoEmbedded":
        row.extend(self.GetCSVRow(value.Get(type_info.name)))
      else:
        row.append(utils.SmartStr(value.Get(type_info.name)))

    return row

  def WriteCSVRow(self, output_file, value):
    csv.writer(output_file).writerow(self.GetCSVRow(value))

  def GetOutputFd(self, value_type):
    """Initializes output AFF4Image for a given value type."""
    file_name = value_type + ".csv"
    try:
      output_stream = self._GetOutputStream(file_name)
    except KeyError:
      output_stream = self._CreateOutputStream(file_name)

      self.WriteCSVHeader(output_stream, value_type)

    return output_stream

  @utils.Synchronized
  def WriteValuesToCSVFile(self, values):
    output_files = {}
    for value in values:
      output_file = self.GetOutputFd(value.__class__.__name__)
      output_files[value.__class__.__name__] = output_file

      self.WriteCSVRow(output_file, value)

    for fd in output_files.values():
      fd.Flush()
