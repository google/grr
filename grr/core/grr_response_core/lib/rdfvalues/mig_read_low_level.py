#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr_response_proto import read_low_level_pb2


def ToProtoReadLowLevelRequest(
    rdf: rdf_read_low_level.ReadLowLevelRequest,
) -> read_low_level_pb2.ReadLowLevelRequest:
  return rdf.AsPrimitiveProto()


def ToRDFReadLowLevelRequest(
    proto: read_low_level_pb2.ReadLowLevelRequest,
) -> rdf_read_low_level.ReadLowLevelRequest:
  return rdf_read_low_level.ReadLowLevelRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoReadLowLevelResult(
    rdf: rdf_read_low_level.ReadLowLevelResult,
) -> read_low_level_pb2.ReadLowLevelResult:
  return rdf.AsPrimitiveProto()


def ToRDFReadLowLevelResult(
    proto: read_low_level_pb2.ReadLowLevelResult,
) -> rdf_read_low_level.ReadLowLevelResult:
  return rdf_read_low_level.ReadLowLevelResult.FromSerializedBytes(
      proto.SerializeToString()
  )
