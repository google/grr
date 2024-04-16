#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import large_file as rdf_large_file
from grr_response_proto import large_file_pb2


def ToProtoCollectLargeFileArgs(
    rdf: rdf_large_file.CollectLargeFileArgs,
) -> large_file_pb2.CollectLargeFileArgs:
  return rdf.AsPrimitiveProto()


def ToRDFCollectLargeFileArgs(
    proto: large_file_pb2.CollectLargeFileArgs,
) -> rdf_large_file.CollectLargeFileArgs:
  return rdf_large_file.CollectLargeFileArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCollectLargeFileResult(
    rdf: rdf_large_file.CollectLargeFileResult,
) -> large_file_pb2.CollectLargeFileResult:
  return rdf.AsPrimitiveProto()


def ToRDFCollectLargeFileResult(
    proto: large_file_pb2.CollectLargeFileResult,
) -> rdf_large_file.CollectLargeFileResult:
  return rdf_large_file.CollectLargeFileResult.FromSerializedBytes(
      proto.SerializeToString()
  )
