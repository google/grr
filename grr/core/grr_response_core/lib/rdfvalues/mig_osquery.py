#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_proto import osquery_pb2


def ToProtoOsqueryArgs(rdf: rdf_osquery.OsqueryArgs) -> osquery_pb2.OsqueryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryArgs(proto: osquery_pb2.OsqueryArgs) -> rdf_osquery.OsqueryArgs:
  return rdf_osquery.OsqueryArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoOsqueryColumn(
    rdf: rdf_osquery.OsqueryColumn,
) -> osquery_pb2.OsqueryColumn:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryColumn(
    proto: osquery_pb2.OsqueryColumn,
) -> rdf_osquery.OsqueryColumn:
  return rdf_osquery.OsqueryColumn.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoOsqueryHeader(
    rdf: rdf_osquery.OsqueryHeader,
) -> osquery_pb2.OsqueryHeader:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryHeader(
    proto: osquery_pb2.OsqueryHeader,
) -> rdf_osquery.OsqueryHeader:
  return rdf_osquery.OsqueryHeader.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoOsqueryRow(rdf: rdf_osquery.OsqueryRow) -> osquery_pb2.OsqueryRow:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryRow(proto: osquery_pb2.OsqueryRow) -> rdf_osquery.OsqueryRow:
  return rdf_osquery.OsqueryRow.FromSerializedBytes(proto.SerializeToString())


def ToProtoOsqueryTable(
    rdf: rdf_osquery.OsqueryTable,
) -> osquery_pb2.OsqueryTable:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryTable(
    proto: osquery_pb2.OsqueryTable,
) -> rdf_osquery.OsqueryTable:
  return rdf_osquery.OsqueryTable.FromSerializedBytes(proto.SerializeToString())


def ToProtoOsqueryResult(
    rdf: rdf_osquery.OsqueryResult,
) -> osquery_pb2.OsqueryResult:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryResult(
    proto: osquery_pb2.OsqueryResult,
) -> rdf_osquery.OsqueryResult:
  return rdf_osquery.OsqueryResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoOsqueryProgress(
    rdf: rdf_osquery.OsqueryProgress,
) -> osquery_pb2.OsqueryProgress:
  return rdf.AsPrimitiveProto()


def ToRDFOsqueryProgress(
    proto: osquery_pb2.OsqueryProgress,
) -> rdf_osquery.OsqueryProgress:
  return rdf_osquery.OsqueryProgress.FromSerializedBytes(
      proto.SerializeToString()
  )
