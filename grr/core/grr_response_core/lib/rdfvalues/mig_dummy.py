#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import dummy as rdf_dummy
from grr_response_proto import dummy_pb2


def ToProtoDummyRequest(rdf: rdf_dummy.DummyRequest) -> dummy_pb2.DummyRequest:
  return rdf.AsPrimitiveProto()


def ToRDFDummyRequest(proto: dummy_pb2.DummyRequest) -> rdf_dummy.DummyRequest:
  return rdf_dummy.DummyRequest.FromSerializedBytes(proto.SerializeToString())


def ToProtoDummyResult(rdf: rdf_dummy.DummyResult) -> dummy_pb2.DummyResult:
  return rdf.AsPrimitiveProto()


def ToRDFDummyResult(proto: dummy_pb2.DummyResult) -> rdf_dummy.DummyResult:
  return rdf_dummy.DummyResult.FromSerializedBytes(proto.SerializeToString())
