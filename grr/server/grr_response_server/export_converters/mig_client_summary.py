#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import client_summary


def ToProtoExportedClient(
    rdf: client_summary.ExportedClient,
) -> export_pb2.ExportedClient:
  return rdf.AsPrimitiveProto()


def ToRDFExportedClient(
    proto: export_pb2.ExportedClient,
) -> client_summary.ExportedClient:
  return client_summary.ExportedClient.FromSerializedBytes(
      proto.SerializeToString()
  )
