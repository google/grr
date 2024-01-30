#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import dummy_pb2
from grr_response_server.flows.general import dummy


def ToProtoDummyArgs(rdf: dummy.DummyArgs) -> dummy_pb2.DummyArgs:
  return rdf.AsPrimitiveProto()


def ToRDFDummyArgs(proto: dummy_pb2.DummyArgs) -> dummy.DummyArgs:
  return dummy.DummyArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoDummyFlowResult(
    rdf: dummy.DummyFlowResult,
) -> dummy_pb2.DummyFlowResult:
  return rdf.AsPrimitiveProto()


def ToRDFDummyFlowResult(
    proto: dummy_pb2.DummyFlowResult,
) -> dummy.DummyFlowResult:
  return dummy.DummyFlowResult.FromSerializedBytes(proto.SerializeToString())
