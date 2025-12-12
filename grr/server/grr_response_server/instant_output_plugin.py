#!/usr/bin/env python
"""Instant output plugins used by the API for on-the-fly conversion."""

import abc
import functools
import logging
import re
from typing import Callable, Iterable, Iterator, Optional, Sequence

from google.protobuf import message
from grr_response_core.lib import rdfvalue
from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_server import export
from grr_response_server import export_converters_registry
from grr_response_server.databases import db_utils


class InstantOutputPluginProto:
  """The base class for instant output plugins.

  Instant output plugins do on-the-fly data conversion and are used in
  GetExportedFlowResults/GetExportedHuntResults methods.
  """

  __abstract = True  # pylint: disable=g-bad-name

  plugin_name = None
  friendly_name = None
  description = None
  output_file_extension = ""

  def __init__(self, source_urn: Optional[rdfvalue.RDFURN] = None):
    """OutputPlugin constructor.

    Args:
      source_urn: URN identifying source of the data (hunt or flow).

    Raises:
      ValueError: If one of the keyword arguments is empty.
    """
    super().__init__()

    if not source_urn:
      raise ValueError("source_urn can't be empty.")

    self.source_urn = source_urn

  @property
  def output_file_name(self) -> str:
    """Name of the file where plugin's output should be written to."""

    safe_path = re.sub(r":|/", "_", self.source_urn.Path().lstrip("/"))
    return "results_%s%s" % (safe_path, self.output_file_extension)

  def Start(self) -> Iterable[bytes]:
    """Start method is called in the beginning of the export.

    Yields:
      Chunks of bytes.
    """

  def ProcessValuesOfType(
      self,
      type_url: str,
      type_url_results_generator_fn: Callable[
          [], Iterable[flows_pb2.FlowResult]
      ],
  ) -> Iterator[bytes]:
    """Processes a batch of values with the same type.

    ProcessValuesOfType is called *once per value type_url* for each value
    type in the flow/hunt results collection. type_url_results_generator_fn
    yields FlowResults of type type_url.

    Args:
      type_url: Type URL identifying the type of the values to be processed.
      type_url_results_generator_fn: Function returning an iterable with values.
        Each value is a FlowResult wrapping a value of a type_url type.
        type_url_results_generator_fn may be called multiple times within 1
        ProcessValuesOfType() call - for example, when multiple passes over the
        data are required.
    """
    raise NotImplementedError()

  def Finish(self):
    """Finish method is called at the very end of the export.

    Yields:
      Chunks of bytes.
    """


class InstantOutputPluginWithExportConversionProto(InstantOutputPluginProto):
  """Instant output plugin that flattens data before exporting."""

  __abstract = True  # pylint: disable=g-bad-name

  BATCH_SIZE = 5000

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._cached_metadata = {}

  @abc.abstractmethod
  def ProcessUniqueOriginalExportedTypePair(
      self, original_type_name: str, exported_values: Iterable[message.Message]
  ) -> Iterator[bytes]:
    """Processes a unique pair of original type and exported type.

    Exported_values are guaranteed to have the same type. Consequently, this
    function may be called multiple times with the same original_type_name
    argument. Typical example: when export converters generate multiple
    kinds of exported values for a given source value (for example,
    Process is converted to ExportedProcess and ExportedNetworkConnection
    values).

    Args:
      original_type_name: Name of the original set of values that were converted
        to exported_values. This name is only used for naming files and tracking
        conversion statistics. It is important that it is a unique identifier of
        the original type.
      exported_values: An iterator with exported value. All values are
        guaranteed to have the same class.

    Yields:
       Chunks of bytes.
    """
    raise NotImplementedError()

  def ProcessValuesOfType(
      self,
      type_url: str,
      type_url_results_generator_fn: Callable[
          [], Iterable[flows_pb2.FlowResult]
      ],
  ) -> Iterator[bytes]:
    converter_classes = export_converters_registry.GetConvertersByTypeUrl(
        type_url
    )
    if not converter_classes:
      logging.warning("No export converters found for type url: %s", type_url)
      return

    original_rdf_type_name = db_utils.TypeURLToRDFTypeName(type_url)
    next_types = set()
    processed_types = set()
    while True:
      converted_responses = export.FetchMetadataAndConvertFlowResults(
          source_urn=self.source_urn,
          options=export_pb2.ExportOptions(),
          flow_results=type_url_results_generator_fn(),
          cached_metadata=self._cached_metadata,
      )

      generator = self._GenerateSingleExportedTypeIteration(
          next_types, processed_types, converted_responses
      )

      for chunk in self.ProcessUniqueOriginalExportedTypePair(
          original_rdf_type_name, generator
      ):
        yield chunk

      if not next_types:
        break

  def _GenerateSingleExportedTypeIteration(
      self,
      next_types: set[type[message.Message]],
      processed_types: set[type[message.Message]],
      converted_responses: Iterable[message.Message],
  ):
    """Yields responses of a given type only.

    _GenerateSingleExportedTypeIteration iterates through converted_responses
    and only yields responses of the same type. The type is either popped from
    next_types or inferred from the first item of converted_responses.
    The type is added to a set of processed_types.

    Along the way _GenerateSingleExportedTypeIteration updates next_types set.
    All newly encountered and not previously processed types are added to
    next_types set.

    Calling _GenerateSingleExportedTypeIteration multiple times allows doing
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


def GetExportedFlowResults(
    plugin: InstantOutputPluginProto,
    type_urls: Sequence[str],
    fetch_flow_results_by_type_url_fn: Callable[
        [str], Iterator[flows_pb2.FlowResult]
    ],
) -> Iterator[bytes]:
  """Applies instant output plugin to a collection of results.

  Args:
    plugin: InstantOutputPlugin instance.
    type_urls: List of type URLs (strings) to be processed.
    fetch_flow_results_by_type_url_fn: Function that takes a type URL as an
      argument and returns available items (FlowResult) corresponding to this
      type. Items are returned as a generator

  Yields:
    Bytes chunks, as generated by the plugin.
  """
  for chunk in plugin.Start():
    yield chunk

  def GetFlowResultsOfType(type_url):
    for flow_result in fetch_flow_results_by_type_url_fn(type_url):
      yield flow_result

  for type_url in sorted(type_urls):
    for chunk in plugin.ProcessValuesOfType(
        type_url, functools.partial(GetFlowResultsOfType, type_url)
    ):
      yield chunk

  for chunk in plugin.Finish():
    yield chunk
