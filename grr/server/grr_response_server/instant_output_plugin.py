#!/usr/bin/env python
"""Instant output plugins used by the API for on-the-fly conversion."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import re


from builtins import zip  # pylint: disable=redefined-builtin
from future.utils import itervalues
from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.util import collection
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import export


class InstantOutputPlugin(with_metaclass(registry.MetaclassRegistry, object)):
  """The base class for instant output plugins.

  Instant output plugins do on-the-fly data conversion and are used in
  GetExportedFlowResults/GetExportedHuntResults methods.
  """
  __abstract = True  # pylint: disable=g-bad-name

  plugin_name = None
  friendly_name = None
  description = None
  output_file_extension = ""

  @classmethod
  def GetPluginClassByPluginName(cls, name):
    for plugin_cls in itervalues(cls.classes):
      if plugin_cls.plugin_name == name:
        return plugin_cls

    raise KeyError("No plugin with name attribute '%s'." % name)

  def __init__(self, source_urn=None, token=None):
    """OutputPlugin constructor.

    Args:
      source_urn: URN identifying source of the data (hunt or flow).
      token: Security token.

    Raises:
      ValueError: If one of the keyword arguments is empty.
    """
    super(InstantOutputPlugin, self).__init__()

    if not source_urn:
      raise ValueError("source_urn can't be empty.")

    if not token:
      raise ValueError("token can't be empty.")

    self.source_urn = source_urn
    self.token = token

  @property
  def output_file_name(self):
    """Name of the file where plugin's output should be written to."""

    safe_path = re.sub(r":|/", "_", self.source_urn.Path().lstrip("/"))
    return "results_%s%s" % (safe_path, self.output_file_extension)

  def Start(self):
    """Start method is called in the beginning of the export.

    Yields:
      Chunks of bytes.
    """

  def ProcessValues(self, value_cls, values_generator_fn):
    """Processes a batch of values with the same type.

    ProcessValues is called *once per value type* for each value type in
    the flow/hunt results collection.

    Args:
      value_cls: Class identifying type of the values to be processed.
      values_generator_fn: Function returning an iterable with values. Each
        value is a GRRMessage wrapping a value of a value_cls type.
        values_generator_fn may be called multiple times within 1
        ProcessValues() call - for example, when multiple passes over the data
        are required.
    """
    raise NotImplementedError()

  def Finish(self):
    """Finish method is called at the very end of the export.

    Yields:
      Chunks of bytes.
    """


class InstantOutputPluginWithExportConversion(InstantOutputPlugin):
  """Instant output plugin that flattens data before exporting."""

  __abstract = True  # pylint: disable=g-bad-name

  BATCH_SIZE = 5000

  def __init__(self, *args, **kwargs):
    super(InstantOutputPluginWithExportConversion, self).__init__(
        *args, **kwargs)
    self._cached_metadata = {}

  def _GetMetadataForClients(self, client_urns):
    """Fetches metadata for a given list of clients."""

    result = {}
    metadata_to_fetch = set()

    for urn in client_urns:
      try:
        result[urn] = self._cached_metadata[urn]
      except KeyError:
        metadata_to_fetch.add(urn)

    if metadata_to_fetch:
      if data_store.RelationalDBReadEnabled():
        client_ids = set(urn.Basename() for urn in metadata_to_fetch)
        infos = data_store.REL_DB.MultiReadClientFullInfo(client_ids)

        fetched_metadata = [
            export.GetMetadata(client_id, info)
            for client_id, info in infos.items()
        ]
      else:
        client_fds = aff4.FACTORY.MultiOpen(
            metadata_to_fetch, mode="r", token=self.token)

        fetched_metadata = [
            export.GetMetadataLegacy(client_fd, token=self.token)
            for client_fd in client_fds
        ]

      for metadata in fetched_metadata:
        metadata.source_urn = self.source_urn

        self._cached_metadata[metadata.client_urn] = metadata
        result[metadata.client_urn] = metadata
        metadata_to_fetch.remove(metadata.client_urn)

      for urn in metadata_to_fetch:
        default_mdata = export.ExportedMetadata(source_urn=self.source_urn)
        result[urn] = default_mdata
        self._cached_metadata[urn] = default_mdata

    return [result[urn] for urn in client_urns]

  def GetExportOptions(self):
    """Rerturns export options to be used by export converter."""
    return export.ExportOptions()

  def ProcessSingleTypeExportedValues(self, original_type, exported_values):
    """Processes exported values of the same type.

    Exported_values are guaranteed to have the same type. Consequently, this
    function may be called multiple times with the same original_type
    argument. Typical example: when export converters generate multiple
    kinds of exported values for a given source value (for example,
    Process is converted to ExportedProcess and ExportedNetworkConnection
    values).

    Args:
      original_type: Class of the original set of values that were converted to
        exported_values.
      exported_values: An iterator with exported value. All values are
        guaranteed to have the same class.

    Yields:
       Chunks of bytes.
    """
    raise NotImplementedError()

  def _GenerateSingleTypeIteration(self, next_types, processed_types,
                                   converted_responses):
    """Yields responses of a given type only.

    _GenerateSingleTypeIteration iterates through converted_responses and
    only yields responses of the same type. The type is either popped from
    next_types or inferred from the first item of converted_responses.
    The type is added to a set of processed_types.

    Along the way _GenerateSingleTypeIteration updates next_types set.
    All newly encountered and not previously processed types are added to
    next_types set.

    Calling _GenerateSingleTypeIteration multiple times allows doing
    multiple passes on converted responses and emitting converted responses
    of the same type continuously (so that they can be written into
    the same file by the plugin).

    Args:
      next_types: List of value type classes that will be used in further
        iterations.
      processed_types: List of value type classes that have been used already.
      converted_responses: Iterable with values to iterate over.

    Yields:
      Values from converted_response with the same type. Type is either
      popped from the next_types set or inferred from the first
      converted_responses value.
    """
    if not next_types:
      current_type = None
    else:
      current_type = next_types.pop()
      processed_types.add(current_type)

    for converted_response in converted_responses:
      if not current_type:
        current_type = converted_response.__class__
        processed_types.add(current_type)

      if converted_response.__class__ != current_type:
        if converted_response.__class__ not in processed_types:
          next_types.add(converted_response.__class__)
        continue

      yield converted_response

  def _GenerateConvertedValues(self, converter, grr_messages):
    """Generates converted values using given converter from given messages.

    Groups values in batches of BATCH_SIZE size and applies the converter
    to each batch.

    Args:
      converter: ExportConverter instance.
      grr_messages: An iterable (a generator is assumed) with GRRMessage values.

    Yields:
      Values generated by the converter.

    Raises:
      ValueError: if any of the GrrMessage objects doesn't have "source" set.
    """
    for batch in collection.Batch(grr_messages, self.BATCH_SIZE):
      metadata_items = self._GetMetadataForClients([gm.source for gm in batch])
      batch_with_metadata = zip(metadata_items, [gm.payload for gm in batch])

      for result in converter.BatchConvert(
          batch_with_metadata, token=self.token):
        yield result

  def ProcessValues(self, value_type, values_generator_fn):
    converter_classes = export.ExportConverter.GetConvertersByClass(value_type)
    if not converter_classes:
      return
    converters = [cls(self.GetExportOptions()) for cls in converter_classes]

    next_types = set()
    processed_types = set()
    while True:
      converted_responses = itertools.chain.from_iterable(
          self._GenerateConvertedValues(converter, values_generator_fn())
          for converter in converters)

      generator = self._GenerateSingleTypeIteration(next_types, processed_types,
                                                    converted_responses)

      for chunk in self.ProcessSingleTypeExportedValues(value_type, generator):
        yield chunk

      if not next_types:
        break


def ApplyPluginToMultiTypeCollection(plugin, output_collection,
                                     source_urn=None):
  """Applies instant output plugin to a multi-type collection.

  Args:
    plugin: InstantOutputPlugin instance.
    output_collection: MultiTypeCollection instance.
    source_urn: If not None, override source_urn for collection items. This has
      to be used when exporting flow results - their GrrMessages don't have
      "source" attribute set.

  Yields:
    Bytes chunks, as generated by the plugin.
  """
  for chunk in plugin.Start():
    yield chunk

  for stored_type_name in sorted(output_collection.ListStoredTypes()):
    stored_cls = rdfvalue.RDFValue.classes[stored_type_name]

    # pylint: disable=cell-var-from-loop
    def GetValues():
      for timestamp, value in output_collection.ScanByType(stored_type_name):
        _ = timestamp
        if source_urn:
          value.source = source_urn
        yield value

    # pylint: enable=cell-var-from-loop

    for chunk in plugin.ProcessValues(stored_cls, GetValues):
      yield chunk

  for chunk in plugin.Finish():
    yield chunk
