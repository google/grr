#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_server import artifact


def ToProtoKnowledgeBaseInitializationArgs(
    rdf: artifact.KnowledgeBaseInitializationArgs,
) -> flows_pb2.KnowledgeBaseInitializationArgs:
  return rdf.AsPrimitiveProto()


def ToRDFKnowledgeBaseInitializationArgs(
    proto: flows_pb2.KnowledgeBaseInitializationArgs,
) -> artifact.KnowledgeBaseInitializationArgs:
  return artifact.KnowledgeBaseInitializationArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
