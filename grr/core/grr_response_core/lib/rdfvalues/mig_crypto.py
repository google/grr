#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_proto import jobs_pb2


def ToProtoCertificate(rdf: rdf_crypto.Certificate) -> jobs_pb2.Certificate:
  return rdf.AsPrimitiveProto()


def ToRDFCertificate(proto: jobs_pb2.Certificate) -> rdf_crypto.Certificate:
  return rdf_crypto.Certificate.FromSerializedBytes(proto.SerializeToString())


def ToProtoHash(rdf: rdf_crypto.Hash) -> jobs_pb2.Hash:
  return rdf.AsPrimitiveProto()


def ToRDFHash(proto: jobs_pb2.Hash) -> rdf_crypto.Hash:
  return rdf_crypto.Hash.FromSerializedBytes(proto.SerializeToString())


def ToProtoSignedBlob(rdf: rdf_crypto.SignedBlob) -> jobs_pb2.SignedBlob:
  return rdf.AsPrimitiveProto()


def ToRDFSignedBlob(proto: jobs_pb2.SignedBlob) -> rdf_crypto.SignedBlob:
  return rdf_crypto.SignedBlob.FromSerializedBytes(proto.SerializeToString())


def ToProtoSymmetricCipher(
    rdf: rdf_crypto.SymmetricCipher,
) -> jobs_pb2.SymmetricCipher:
  return rdf.AsPrimitiveProto()


def ToRDFSymmetricCipher(
    proto: jobs_pb2.SymmetricCipher,
) -> rdf_crypto.SymmetricCipher:
  return rdf_crypto.SymmetricCipher.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPassword(rdf: rdf_crypto.Password) -> jobs_pb2.Password:
  return rdf.AsPrimitiveProto()


def ToRDFPassword(proto: jobs_pb2.Password) -> rdf_crypto.Password:
  return rdf_crypto.Password.FromSerializedBytes(proto.SerializeToString())
