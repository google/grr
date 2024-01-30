#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_server.flows.general import discovery


def ToProtoInterrogateArgs(
    rdf: discovery.InterrogateArgs,
) -> flows_pb2.InterrogateArgs:
  return rdf.AsPrimitiveProto()


def ToRDFInterrogateArgs(
    proto: flows_pb2.InterrogateArgs,
) -> discovery.InterrogateArgs:
  return discovery.InterrogateArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
