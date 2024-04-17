#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import output_plugin_pb2
from grr_response_server.output_plugins import elasticsearch_plugin


def ToProtoElasticsearchOutputPluginArgs(
    rdf: elasticsearch_plugin.ElasticsearchOutputPluginArgs,
) -> output_plugin_pb2.ElasticsearchOutputPluginArgs:
  return rdf.AsPrimitiveProto()


def ToRDFElasticsearchOutputPluginArgs(
    proto: output_plugin_pb2.ElasticsearchOutputPluginArgs,
) -> elasticsearch_plugin.ElasticsearchOutputPluginArgs:
  return elasticsearch_plugin.ElasticsearchOutputPluginArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
