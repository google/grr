#!/usr/bin/env python
"""Plugins that produce results in YAML."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import zipfile

import yaml

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_server import instant_output_plugin


def _SerializeToYaml(value):
  preserialized = []
  if isinstance(value, rdf_structs.RDFProtoStruct):
    preserialized.append(value.ToPrimitiveDict(serialize_leaf_fields=True))
  else:
    preserialized.append(utils.SmartStr(value))
  # Produce a YAML list entry in block format.
  # Note that the order of the fields is not guaranteed to correspond to that of
  # other output formats.
  return yaml.safe_dump(preserialized, default_flow_style=False)


class YamlInstantOutputPluginWithExportConversion(
    instant_output_plugin.InstantOutputPluginWithExportConversion):
  """Instant output plugin that flattens results into YAML."""

  plugin_name = "flattened-yaml-zip"
  friendly_name = "Flattened YAML (zipped)"
  description = "Output ZIP archive with YAML files (flattened)."
  output_file_extension = ".zip"

  ROW_BATCH = 100

  def __init__(self, *args, **kwargs):
    super(YamlInstantOutputPluginWithExportConversion, self).__init__(
        *args, **kwargs)
    self.archive_generator = None  # Created in Start()
    self.export_counts = {}

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
        "%s/%s/from_%s.yaml" % (self.path_prefix,
                                first_value.__class__.__name__,
                                original_value_type.__name__))
    yield self.archive_generator.WriteFileChunk(_SerializeToYaml(first_value))
    counter = 1
    for batch in collection.Batch(exported_values, self.ROW_BATCH):
      counter += len(batch)
      # TODO(hanuszczak): YAML is supposed to be a unicode file format so we
      # should use `StringIO` here instead. However, because PyYAML dumps to
      # `bytes` instead of `unicode` we have to use `BytesIO`. It should be
      # investigated whether there is a way to adjust behaviour of PyYAML.
      buf = io.BytesIO()
      for value in batch:
        buf.write(b"\n")
        buf.write(_SerializeToYaml(value))

      yield self.archive_generator.WriteFileChunk(buf.getvalue())
    yield self.archive_generator.WriteFileFooter()

    counts_for_original_type = self.export_counts.setdefault(
        original_value_type.__name__, dict())
    counts_for_original_type[first_value.__class__.__name__] = counter

  def Finish(self):
    manifest = {"export_stats": self.export_counts}

    yield self.archive_generator.WriteFileHeader(self.path_prefix + "/MANIFEST")
    yield self.archive_generator.WriteFileChunk(yaml.safe_dump(manifest))
    yield self.archive_generator.WriteFileFooter()
    yield self.archive_generator.Close()
