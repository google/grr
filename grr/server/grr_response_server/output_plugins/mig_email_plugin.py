#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import output_plugin_pb2
from grr_response_server.output_plugins import email_plugin


def ToProtoEmailOutputPluginArgs(
    rdf: email_plugin.EmailOutputPluginArgs,
) -> output_plugin_pb2.EmailOutputPluginArgs:
  return rdf.AsPrimitiveProto()


def ToRDFEmailOutputPluginArgs(
    proto: output_plugin_pb2.EmailOutputPluginArgs,
) -> email_plugin.EmailOutputPluginArgs:
  return email_plugin.EmailOutputPluginArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
