#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import semantic_pb2


def ToProtoSemanticDescriptor(
    rdf: rdf_structs.SemanticDescriptor,
) -> semantic_pb2.SemanticDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFSemanticDescriptor(
    proto: semantic_pb2.SemanticDescriptor,
) -> rdf_structs.SemanticDescriptor:
  return rdf_structs.SemanticDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoAny(rdf: rdf_structs.AnyValue) -> any_pb2.Any:
  return rdf.AsPrimitiveProto()


def ToRDFAnyValue(proto: any_pb2.Any) -> rdf_structs.AnyValue:
  return rdf_structs.AnyValue.FromSerializedBytes(proto.SerializeToString())
