#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import output_plugin_pb2
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


def ToProtoOutputPluginDescriptor(
    rdf: rdf_output_plugin.OutputPluginDescriptor,
) -> output_plugin_pb2.OutputPluginDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFOutputPluginDescriptor(
    proto: output_plugin_pb2.OutputPluginDescriptor,
) -> rdf_output_plugin.OutputPluginDescriptor:
  return rdf_output_plugin.OutputPluginDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )
