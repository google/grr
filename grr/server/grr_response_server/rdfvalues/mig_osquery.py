#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import osquery_pb2
from grr_response_server.rdfvalues import osquery as rdf_osquery


def ToProtoOsqueryCollectedFile(
    rdf: rdf_osquery.OsqueryCollectedFile,
) -> osquery_pb2.OsqueryCollectedFile:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryCollectedFile(
    proto: osquery_pb2.OsqueryCollectedFile,
) -> rdf_osquery.OsqueryCollectedFile:
  return rdf_osquery.OsqueryCollectedFile.FromSerializedBytes(
      proto.SerializeToString()
  )
