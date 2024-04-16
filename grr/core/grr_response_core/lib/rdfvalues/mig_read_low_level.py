#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr_response_proto import read_low_level_pb2


def ToProtoReadLowLevelArgs(
    rdf: rdf_read_low_level.ReadLowLevelArgs,
) -> read_low_level_pb2.ReadLowLevelArgs:
  return rdf.AsPrimitiveProto()


def ToRDFReadLowLevelArgs(
    proto: read_low_level_pb2.ReadLowLevelArgs,
) -> rdf_read_low_level.ReadLowLevelArgs:
  return rdf_read_low_level.ReadLowLevelArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoReadLowLevelFlowResult(
    rdf: rdf_read_low_level.ReadLowLevelFlowResult,
) -> read_low_level_pb2.ReadLowLevelFlowResult:
  return rdf.AsPrimitiveProto()


def ToRDFReadLowLevelFlowResult(
    proto: read_low_level_pb2.ReadLowLevelFlowResult,
) -> rdf_read_low_level.ReadLowLevelFlowResult:
  return rdf_read_low_level.ReadLowLevelFlowResult.FromSerializedBytes(
      proto.SerializeToString()
  )


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
