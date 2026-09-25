#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_proto import jobs_pb2


def ToProtoHash(rdf: rdf_crypto.Hash) -> jobs_pb2.Hash:
  return rdf.AsPrimitiveProto()


def ToRDFHash(proto: jobs_pb2.Hash) -> rdf_crypto.Hash:
  return rdf_crypto.Hash.FromSerializedBytes(proto.SerializeToString())


def ToProtoSignedBlob(rdf: rdf_crypto.SignedBlob) -> jobs_pb2.SignedBlob:
  return rdf.AsPrimitiveProto()


def ToRDFSignedBlob(proto: jobs_pb2.SignedBlob) -> rdf_crypto.SignedBlob:
  return rdf_crypto.SignedBlob.FromSerializedBytes(proto.SerializeToString())
