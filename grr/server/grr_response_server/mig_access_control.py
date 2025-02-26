#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import deprecated_pb2
from grr_response_server import access_control


def ToProtoACLToken(rdf: access_control.ACLToken) -> deprecated_pb2.ACLToken:
  return rdf.AsPrimitiveProto()


def ToRDFACLToken(proto: deprecated_pb2.ACLToken) -> access_control.ACLToken:
  return access_control.ACLToken.FromSerializedBytes(proto.SerializeToString())
