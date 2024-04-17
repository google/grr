#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_proto import flows_pb2


def ToProtoYaraSignatureShard(
    rdf: rdf_memory.YaraSignatureShard,
) -> flows_pb2.YaraSignatureShard:
  return rdf.AsPrimitiveProto()


def ToRDFYaraSignatureShard(
    proto: flows_pb2.YaraSignatureShard,
) -> rdf_memory.YaraSignatureShard:
  return rdf_memory.YaraSignatureShard.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraProcessScanRequest(
    rdf: rdf_memory.YaraProcessScanRequest,
) -> flows_pb2.YaraProcessScanRequest:
  return rdf.AsPrimitiveProto()


def ToRDFYaraProcessScanRequest(
    proto: flows_pb2.YaraProcessScanRequest,
) -> rdf_memory.YaraProcessScanRequest:
  return rdf_memory.YaraProcessScanRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoProcessMemoryError(
    rdf: rdf_memory.ProcessMemoryError,
) -> flows_pb2.ProcessMemoryError:
  return rdf.AsPrimitiveProto()


def ToRDFProcessMemoryError(
    proto: flows_pb2.ProcessMemoryError,
) -> rdf_memory.ProcessMemoryError:
  return rdf_memory.ProcessMemoryError.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraStringMatch(
    rdf: rdf_memory.YaraStringMatch,
) -> flows_pb2.YaraStringMatch:
  return rdf.AsPrimitiveProto()


def ToRDFYaraStringMatch(
    proto: flows_pb2.YaraStringMatch,
) -> rdf_memory.YaraStringMatch:
  return rdf_memory.YaraStringMatch.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraMatch(rdf: rdf_memory.YaraMatch) -> flows_pb2.YaraMatch:
  return rdf.AsPrimitiveProto()


def ToRDFYaraMatch(proto: flows_pb2.YaraMatch) -> rdf_memory.YaraMatch:
  return rdf_memory.YaraMatch.FromSerializedBytes(proto.SerializeToString())


def ToProtoYaraProcessScanMatch(
    rdf: rdf_memory.YaraProcessScanMatch,
) -> flows_pb2.YaraProcessScanMatch:
  return rdf.AsPrimitiveProto()


def ToRDFYaraProcessScanMatch(
    proto: flows_pb2.YaraProcessScanMatch,
) -> rdf_memory.YaraProcessScanMatch:
  return rdf_memory.YaraProcessScanMatch.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraProcessScanMiss(
    rdf: rdf_memory.YaraProcessScanMiss,
) -> flows_pb2.YaraProcessScanMiss:
  return rdf.AsPrimitiveProto()


def ToRDFYaraProcessScanMiss(
    proto: flows_pb2.YaraProcessScanMiss,
) -> rdf_memory.YaraProcessScanMiss:
  return rdf_memory.YaraProcessScanMiss.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraProcessScanResponse(
    rdf: rdf_memory.YaraProcessScanResponse,
) -> flows_pb2.YaraProcessScanResponse:
  return rdf.AsPrimitiveProto()


def ToRDFYaraProcessScanResponse(
    proto: flows_pb2.YaraProcessScanResponse,
) -> rdf_memory.YaraProcessScanResponse:
  return rdf_memory.YaraProcessScanResponse.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraProcessDumpArgs(
    rdf: rdf_memory.YaraProcessDumpArgs,
) -> flows_pb2.YaraProcessDumpArgs:
  return rdf.AsPrimitiveProto()


def ToRDFYaraProcessDumpArgs(
    proto: flows_pb2.YaraProcessDumpArgs,
) -> rdf_memory.YaraProcessDumpArgs:
  return rdf_memory.YaraProcessDumpArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoProcessMemoryRegion(
    rdf: rdf_memory.ProcessMemoryRegion,
) -> flows_pb2.ProcessMemoryRegion:
  return rdf.AsPrimitiveProto()


def ToRDFProcessMemoryRegion(
    proto: flows_pb2.ProcessMemoryRegion,
) -> rdf_memory.ProcessMemoryRegion:
  return rdf_memory.ProcessMemoryRegion.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraProcessDumpInformation(
    rdf: rdf_memory.YaraProcessDumpInformation,
) -> flows_pb2.YaraProcessDumpInformation:
  return rdf.AsPrimitiveProto()


def ToRDFYaraProcessDumpInformation(
    proto: flows_pb2.YaraProcessDumpInformation,
) -> rdf_memory.YaraProcessDumpInformation:
  return rdf_memory.YaraProcessDumpInformation.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoYaraProcessDumpResponse(
    rdf: rdf_memory.YaraProcessDumpResponse,
) -> flows_pb2.YaraProcessDumpResponse:
  return rdf.AsPrimitiveProto()


def ToRDFYaraProcessDumpResponse(
    proto: flows_pb2.YaraProcessDumpResponse,
) -> rdf_memory.YaraProcessDumpResponse:
  return rdf_memory.YaraProcessDumpResponse.FromSerializedBytes(
      proto.SerializeToString()
  )
