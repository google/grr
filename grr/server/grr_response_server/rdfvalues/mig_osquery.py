#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import osquery_pb2
from grr_response_server.rdfvalues import osquery as rdf_osquery


def ToProtoOsqueryFlowArgs(
    rdf: rdf_osquery.OsqueryFlowArgs,
) -> osquery_pb2.OsqueryFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryFlowArgs(
    proto: osquery_pb2.OsqueryFlowArgs,
) -> rdf_osquery.OsqueryFlowArgs:
  return rdf_osquery.OsqueryFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


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
