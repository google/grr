#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import output_plugin_pb2
from grr_response_server.output_plugins import bigquery_plugin


def ToProtoBigQueryOutputPluginArgs(
    rdf: bigquery_plugin.BigQueryOutputPluginArgs,
) -> output_plugin_pb2.BigQueryOutputPluginArgs:
  return rdf.AsPrimitiveProto()


def ToRDFBigQueryOutputPluginArgs(
    proto: output_plugin_pb2.BigQueryOutputPluginArgs,
) -> bigquery_plugin.BigQueryOutputPluginArgs:
  return bigquery_plugin.BigQueryOutputPluginArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
