#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2


def ToProtoAuthenticodeSignedData(
    rdf: rdf_standard.AuthenticodeSignedData,
) -> jobs_pb2.AuthenticodeSignedData:
  return rdf.AsPrimitiveProto()


def ToRDFAuthenticodeSignedData(
    proto: jobs_pb2.AuthenticodeSignedData,
) -> rdf_standard.AuthenticodeSignedData:
  return rdf_standard.AuthenticodeSignedData.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPersistenceFile(
    rdf: rdf_standard.PersistenceFile,
) -> jobs_pb2.PersistenceFile:
  return rdf.AsPrimitiveProto()


def ToRDFPersistenceFile(
    proto: jobs_pb2.PersistenceFile,
) -> rdf_standard.PersistenceFile:
  return rdf_standard.PersistenceFile.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoURI(rdf: rdf_standard.URI) -> sysinfo_pb2.URI:
  return rdf.AsPrimitiveProto()


def ToRDFURI(proto: sysinfo_pb2.URI) -> rdf_standard.URI:
  return rdf_standard.URI.FromSerializedBytes(proto.SerializeToString())
