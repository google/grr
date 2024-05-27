#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import output_plugin_pb2
from grr_response_proto.api import reflection_pb2
from grr_response_server.gui.api_plugins import output_plugin


def ToProtoApiOutputPlugin(
    rdf: output_plugin.ApiOutputPlugin,
) -> output_plugin_pb2.ApiOutputPlugin:
  return rdf.AsPrimitiveProto()


def ToRDFApiOutputPlugin(
    proto: output_plugin_pb2.ApiOutputPlugin,
) -> output_plugin.ApiOutputPlugin:
  return output_plugin.ApiOutputPlugin.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiOutputPluginDescriptor(
    rdf: output_plugin.ApiOutputPluginDescriptor,
) -> reflection_pb2.ApiOutputPluginDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFApiOutputPluginDescriptor(
    proto: reflection_pb2.ApiOutputPluginDescriptor,
) -> output_plugin.ApiOutputPluginDescriptor:
  return output_plugin.ApiOutputPluginDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListOutputPluginDescriptorsResult(
    rdf: output_plugin.ApiListOutputPluginDescriptorsResult,
) -> reflection_pb2.ApiListOutputPluginDescriptorsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListOutputPluginDescriptorsResult(
    proto: reflection_pb2.ApiListOutputPluginDescriptorsResult,
) -> output_plugin.ApiListOutputPluginDescriptorsResult:
  return output_plugin.ApiListOutputPluginDescriptorsResult.FromSerializedBytes(
      proto.SerializeToString()
  )
