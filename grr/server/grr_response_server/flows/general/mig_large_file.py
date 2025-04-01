#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import large_file_pb2
from grr_response_server.flows.general import large_file


def ToProtoCollectLargeFileFlowArgs(
    rdf: large_file.CollectLargeFileFlowArgs,
) -> large_file_pb2.CollectLargeFileFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFCollectLargeFileFlowArgs(
    proto: large_file_pb2.CollectLargeFileFlowArgs,
) -> large_file.CollectLargeFileFlowArgs:
  return large_file.CollectLargeFileFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
