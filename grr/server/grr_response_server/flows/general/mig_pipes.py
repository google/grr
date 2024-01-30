#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import pipes_pb2
from grr_response_server.flows.general import pipes


def ToProtoListNamedPipesFlowArgs(
    rdf: pipes.ListNamedPipesFlowArgs,
) -> pipes_pb2.ListNamedPipesFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFListNamedPipesFlowArgs(
    proto: pipes_pb2.ListNamedPipesFlowArgs,
) -> pipes.ListNamedPipesFlowArgs:
  return pipes.ListNamedPipesFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoListNamedPipesFlowResult(
    rdf: pipes.ListNamedPipesFlowResult,
) -> pipes_pb2.ListNamedPipesFlowResult:
  return rdf.AsPrimitiveProto()


def ToRDFListNamedPipesFlowResult(
    proto: pipes_pb2.ListNamedPipesFlowResult,
) -> pipes.ListNamedPipesFlowResult:
  return pipes.ListNamedPipesFlowResult.FromSerializedBytes(
      proto.SerializeToString()
  )
