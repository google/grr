#!/usr/bin/env python
"""ExportConverters base class."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2


class ExportedMetadata(rdf_structs.RDFProtoStruct):
  """ExportMetadata RDF value."""

  protobuf = export_pb2.ExportedMetadata
  rdf_deps = [
      rdf_client.ClientURN,
      rdf_client.HardwareInfo,
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
      rdfvalue.SessionID,
  ]

  def __init__(self, initializer=None, payload=None, **kwarg):
    super().__init__(initializer=initializer, **kwarg)

    if not self.timestamp:
      self.timestamp = rdfvalue.RDFDatetime.Now()


class ExportOptions(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportOptions


class ExportConverter():
  """Base ExportConverter class.

  ExportConverters are used to convert RDFValues to export-friendly RDFValues.
  "Export-friendly" means 2 things:
    * Flat structure
    * No repeated fields (i.e. lists)

  In order to use ExportConverters, users have to use ConvertValues.
  These methods will look up all the available ExportConverters descendants
  and will choose the ones that have input_rdf_type attribute equal to the
  type of the values being converted. It's ok to have multiple converters with
  the same input_rdf_type value. They will be applied sequentially and their
  cumulative results will be returned.
  """

  # Type of values that this converter accepts.
  input_rdf_type = None

  def __init__(self, options=None):
    """Constructor.

    Args:
      options: ExportOptions value, which contains settings that may or or may
        not affect this converter's behavior.
    """
    super().__init__()
    self.options = options or ExportOptions()

  def Convert(self, metadata, value):
    """Converts given RDFValue to other RDFValues.

    Metadata object is provided by the caller. It contains basic information
    about where the value is coming from (i.e. client_urn, session_id, etc)
    as well as timestamps corresponding to when data was generated and
    exported.

    ExportConverter should use the metadata when constructing export-friendly
    RDFValues.

    Args:
      metadata: ExportedMetadata to be used for conversion.
      value: RDFValue to be converted.

    Yields:
      Resulting RDFValues. Empty list is a valid result and means that
      conversion wasn't possible. Resulting RDFValues may be of different
      types.
    """
    raise NotImplementedError()

  def BatchConvert(self, metadata_value_pairs):
    """Converts a batch of RDFValues at once.

    This is a default non-optimized dumb implementation. Subclasses are
    supposed to have their own optimized implementations.

    Metadata object is provided by the caller. It contains basic information
    about where the value is coming from (i.e. client_urn, session_id, etc)
    as well as timestamps corresponding to when data was generated and
    exported.

    ExportConverter should use the metadata when constructing export-friendly
    RDFValues.

    Args:
      metadata_value_pairs: a list or a generator of tuples (metadata, value),
        where metadata is ExportedMetadata to be used for conversion and value
        is an RDFValue to be converted.

    Yields:
      Resulting RDFValues. Empty list is a valid result and means that
      conversion wasn't possible. Resulting RDFValues may be of different
      types.
    """
    for metadata, value in metadata_value_pairs:
      for result in self.Convert(metadata, value):
        yield result
