#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_server.flows.general import network


def ToProtoNetstatArgs(rdf: network.NetstatArgs) -> flows_pb2.NetstatArgs:
  return rdf.AsPrimitiveProto()


def ToRDFNetstatArgs(proto: flows_pb2.NetstatArgs) -> network.NetstatArgs:
  return network.NetstatArgs.FromSerializedBytes(proto.SerializeToString())
