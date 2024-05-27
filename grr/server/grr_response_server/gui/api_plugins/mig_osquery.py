#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import osquery_pb2
from grr_response_server.gui.api_plugins import osquery


def ToProtoApiGetOsqueryResultsArgs(
    rdf: osquery.ApiGetOsqueryResultsArgs,
) -> osquery_pb2.ApiGetOsqueryResultsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetOsqueryResultsArgs(
    proto: osquery_pb2.ApiGetOsqueryResultsArgs,
) -> osquery.ApiGetOsqueryResultsArgs:
  return osquery.ApiGetOsqueryResultsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
