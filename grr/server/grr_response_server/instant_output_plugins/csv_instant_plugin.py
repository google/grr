#!/usr/bin/env python
"""CSV single-pass output plugin."""

import csv
import io
import os
from typing import Iterator
import zipfile

import yaml

from google.protobuf import descriptor as proto_descriptor
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import text
from grr_response_server import instant_output_plugin


class CSVInstantOutputPluginProto(
    instant_output_plugin.InstantOutputPluginWithExportConversionProto
):
  """Instant Output plugin that writes results to an archive of CSV files."""

  plugin_name = "csv-zip"
  friendly_name = "CSV (zipped)"
  description = "Output ZIP archive with CSV files."
  output_file_extension = ".zip"

  archive_generator: utils.StreamingZipGenerator
  export_counts: dict[str, dict[str, int]]

  ROW_BATCH = 100

  def _GetCSVHeader(self, descriptor, prefix=""):
    header = []
    for field_name, field_descriptor in descriptor.fields_by_name.items():
      if field_descriptor.type == proto_descriptor.FieldDescriptor.TYPE_MESSAGE:
        header.extend(
            self._GetCSVHeader(
                field_descriptor.message_type, prefix=prefix + field_name + "."
            )
        )
      else:
        header.append(prefix + field_name)
    return header

  def _GetCSVRow(self, value):
    row = []
    for field_name, field_descriptor in value.DESCRIPTOR.fields_by_name.items():
      field_value = getattr(value, field_name)
      if field_descriptor.type == proto_descriptor.FieldDescriptor.TYPE_MESSAGE:
        row.extend(self._GetCSVRow(field_value))
      elif field_descriptor.type == proto_descriptor.FieldDescriptor.TYPE_BYTES:
        row.append(text.Asciify(field_value))
      else:
        row.append(str(field_value))
    return row

  @property
  def path_prefix(self):
    prefix, _ = os.path.splitext(self.output_file_name)
    return prefix

  def Start(self):
    self.archive_generator = utils.StreamingZipGenerator(
        compression=zipfile.ZIP_DEFLATED
    )
    self.export_counts = {}
    return []

  def ProcessUniqueOriginalExportedTypePair(
      self, original_rdf_type_name, exported_values
  ) -> Iterator[bytes]:
    first_value = next(exported_values, None)
    if not first_value:
      return

    yield self.archive_generator.WriteFileHeader(
        "%s/%s/from_%s.csv"
        % (
            self.path_prefix,
            first_value.__class__.__name__,
            original_rdf_type_name,
        )
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    # Write the CSV header based on first value class and write
    # the first value itself. All other values are guaranteed
    # to have the same class (see ProcessUniqueOriginalExportedTypePair
    # definition).
    writer.writerow(self._GetCSVHeader(first_value.DESCRIPTOR))
    writer.writerow(self._GetCSVRow(first_value))

    chunk = buffer.getvalue().encode("utf-8")
    yield self.archive_generator.WriteFileChunk(chunk)

    # Counter starts from 1, as 1 value has already been written.
    counter = 1
    for batch in collection.Batch(exported_values, self.ROW_BATCH):
      counter += len(batch)

      buffer = io.StringIO()
      writer = csv.writer(buffer)
      for value in batch:
        writer.writerow(self._GetCSVRow(value))

      chunk = buffer.getvalue().encode("utf-8")
      yield self.archive_generator.WriteFileChunk(chunk)

    yield self.archive_generator.WriteFileFooter()

    self.export_counts.setdefault(original_rdf_type_name, dict())[
        first_value.__class__.__name__
    ] = counter

  def Finish(self):
    manifest = {"export_stats": self.export_counts}
    manifest_bytes = yaml.safe_dump(manifest).encode("utf-8")

    yield self.archive_generator.WriteFileHeader(self.path_prefix + "/MANIFEST")
    yield self.archive_generator.WriteFileChunk(manifest_bytes)
    yield self.archive_generator.WriteFileFooter()
    yield self.archive_generator.Close()
