#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import output_plugin_pb2
from grr_response_server.output_plugins import splunk_plugin


def ToProtoSplunkOutputPluginArgs(
    rdf: splunk_plugin.SplunkOutputPluginArgs,
) -> output_plugin_pb2.SplunkOutputPluginArgs:
  return rdf.AsPrimitiveProto()


def ToRDFSplunkOutputPluginArgs(
    proto: output_plugin_pb2.SplunkOutputPluginArgs,
) -> splunk_plugin.SplunkOutputPluginArgs:
  return splunk_plugin.SplunkOutputPluginArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
