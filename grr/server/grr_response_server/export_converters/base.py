#!/usr/bin/env python
"""ExportConverters base class."""

import abc
from typing import Generic, Iterable, Optional, TypeVar

from google.protobuf import message
from grr_response_proto import export_pb2


_ProtoInputTypeT = TypeVar("_ProtoInputTypeT", bound=message.Message)


class ExportConverterProto(Generic[_ProtoInputTypeT], metaclass=abc.ABCMeta):
  """Base ExportConverter class.

  ExportConverters are used to convert Protos to export-friendly Protos.
  "Export-friendly" means 2 things:
    * Flat structure
    * No repeated fields (i.e. lists)

  Child classes must:
    * specify input_proto_type set to the proto type it accepts
    * specify output_proto_types set to a list of proto types it can produce
    * implement a Convert method that accepts a single proto and returns a list
      of protos.
    * (Optional) override the BatchConvert method that accepts a list of protos
      and returns a list of protos.

  For an ExportConverter to be available for use at runtime, it must be
  registered in the registry first. It is expected that the registry contains
  multiple converters that can convert a given input proto type.
  """

  # The input proto type that this converter accepts.
  input_proto_type: type[_ProtoInputTypeT] = None
  # The output proto types that this converter can produce.
  output_proto_types: tuple[message.Message, ...] = None

  options: export_pb2.ExportOptions

  def __init__(self, options: Optional[export_pb2.ExportOptions] = None):
    """Constructor.

    Args:
      options: ExportOptions value, which contains settings that may or or may
        not affect this converter's behavior.
    """
    super().__init__()
    self.options = options or export_pb2.ExportOptions()

  @abc.abstractmethod
  def Convert(
      self, metadata: export_pb2.ExportedMetadata, value: _ProtoInputTypeT
  ) -> Iterable[message.Message]:
    """Converts given proto to other exported protos.

    Metadata object is provided by the caller. It contains basic information
    about where the value is coming from (i.e. client_id, os, etc)
    as well as timestamps corresponding to when data was exported.

    ExportConverter should use the metadata when constructing export-friendly
    protos.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      value: Proto to be converted (of input_proto_type).

    Yields:
      Resulting protos. Empty list is a valid result and means that
      conversion wasn't possible. Resulting protos may be of different
      types, which are specified in output_proto_types.
    """
    raise NotImplementedError()

  def BatchConvert(
      self,
      metadata_value_pairs: Iterable[
          tuple[export_pb2.ExportedMetadata, _ProtoInputTypeT]
      ],
  ) -> Iterable[message.Message]:
    """Converts a batch of protos at once.

    This is a default non-optimized dumb implementation. Subclasses are
    supposed to have their own optimized implementations.

    Metadata objects are provided by the caller. It contains basic information
    about where the value is coming from (i.e. client_id, os, etc)
    as well as timestamps corresponding to when data was exported.

    ExportConverter should use the metadata when constructing export-friendly
    protos.

    Args:
      metadata_value_pairs: a list or a generator of tuples (metadata, value),
        where metadata is ExportedMetadata to be used for conversion and value
        is a proto to be converted.

    Yields:
      Resulting protos. Empty list is a valid result and means that
      conversion wasn't possible. Resulting protos may be of different
      types, which are specified in output_proto_types.
    """
    for metadata, value in metadata_value_pairs:
      yield from self.Convert(metadata, value)
