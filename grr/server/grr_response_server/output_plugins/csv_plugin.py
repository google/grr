#!/usr/bin/env python
"""CSV single-pass output plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import zipfile

import yaml

from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import csv
from grr_response_server import instant_output_plugin


class CSVInstantOutputPlugin(
    instant_output_plugin.InstantOutputPluginWithExportConversion):
  """Instant Output plugin that writes results to an archive of CSV files."""

  plugin_name = "csv-zip"
  friendly_name = "CSV (zipped)"
  description = "Output ZIP archive with CSV files."
  output_file_extension = ".zip"

  ROW_BATCH = 100

  def _GetCSVHeader(self, value_class, prefix=u""):
    header = []
    for type_info in value_class.type_infos:
      if type_info.__class__.__name__ == "ProtoEmbedded":
        header.extend(
            self._GetCSVHeader(
                type_info.type, prefix=prefix + type_info.name + u"."))
      else:
        header.append(prefix + type_info.name)

    return header

  def _GetCSVRow(self, value):
    row = []
    for type_info in value.__class__.type_infos:
      if type_info.__class__.__name__ == "ProtoEmbedded":
        row.extend(self._GetCSVRow(value.Get(type_info.name)))
      else:
        row.append(unicode(value.Get(type_info.name)))

    return row

  @property
  def path_prefix(self):
    prefix, _ = os.path.splitext(self.output_file_name)
    return prefix

  def Start(self):
    self.archive_generator = utils.StreamingZipGenerator(
        compression=zipfile.ZIP_DEFLATED)
    self.export_counts = {}
    return []

  def ProcessSingleTypeExportedValues(self, original_value_type,
                                      exported_values):
    first_value = next(exported_values, None)
    if not first_value:
      return

    yield self.archive_generator.WriteFileHeader(
        "%s/%s/from_%s.csv" % (self.path_prefix, first_value.__class__.__name__,
                               original_value_type.__name__))

    writer = csv.Writer()
    # Write the CSV header based on first value class and write
    # the first value itself. All other values are guaranteed
    # to have the same class (see ProcessSingleTypeExportedValues definition).
    writer.WriteRow(self._GetCSVHeader(first_value.__class__))
    writer.WriteRow(self._GetCSVRow(first_value))

    chunk = writer.Content().encode("utf-8")
    yield self.archive_generator.WriteFileChunk(chunk)

    # Counter starts from 1, as 1 value has already been written.
    counter = 1
    for batch in collection.Batch(exported_values, self.ROW_BATCH):
      counter += len(batch)

      writer = csv.Writer()
      for value in batch:
        writer.WriteRow(self._GetCSVRow(value))

      chunk = writer.Content().encode("utf-8")
      yield self.archive_generator.WriteFileChunk(chunk)

    yield self.archive_generator.WriteFileFooter()

    self.export_counts.setdefault(
        original_value_type.__name__,
        dict())[first_value.__class__.__name__] = counter

  def Finish(self):
    manifest = {"export_stats": self.export_counts}

    yield self.archive_generator.WriteFileHeader(self.path_prefix + "/MANIFEST")
    yield self.archive_generator.WriteFileChunk(yaml.safe_dump(manifest))
    yield self.archive_generator.WriteFileFooter()
    yield self.archive_generator.Close()
