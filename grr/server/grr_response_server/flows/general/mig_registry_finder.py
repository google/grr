#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_server.flows.general import registry_finder


def ToProtoRegistryFinderCondition(
    rdf: registry_finder.RegistryFinderCondition,
) -> flows_pb2.RegistryFinderCondition:
  return rdf.AsPrimitiveProto()


def ToRDFRegistryFinderCondition(
    proto: flows_pb2.RegistryFinderCondition,
) -> registry_finder.RegistryFinderCondition:
  return registry_finder.RegistryFinderCondition.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoRegistryFinderArgs(
    rdf: registry_finder.RegistryFinderArgs,
) -> flows_pb2.RegistryFinderArgs:
  return rdf.AsPrimitiveProto()


def ToRDFRegistryFinderArgs(
    proto: flows_pb2.RegistryFinderArgs,
) -> registry_finder.RegistryFinderArgs:
  return registry_finder.RegistryFinderArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
