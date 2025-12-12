#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import flow_pb2
from grr_response_server.gui.api_plugins import flow


def ToProtoApiFlowReference(
    rdf: flow.ApiFlowReference,
) -> flow_pb2.ApiFlowReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlowReference(
    proto: flow_pb2.ApiFlowReference,
) -> flow.ApiFlowReference:
  return flow.ApiFlowReference.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiFlow(rdf: flow.ApiFlow) -> flow_pb2.ApiFlow:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlow(proto: flow_pb2.ApiFlow) -> flow.ApiFlow:
  return flow.ApiFlow.FromSerializedBytes(proto.SerializeToString())
