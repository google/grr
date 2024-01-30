#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import output_plugin_pb2
from grr_response_server import output_plugin


def ToProtoOutputPluginBatchProcessingStatus(
    rdf: output_plugin.OutputPluginBatchProcessingStatus,
) -> output_plugin_pb2.OutputPluginBatchProcessingStatus:
  return rdf.AsPrimitiveProto()


def ToRDFOutputPluginBatchProcessingStatus(
    proto: output_plugin_pb2.OutputPluginBatchProcessingStatus,
) -> output_plugin.OutputPluginBatchProcessingStatus:
  return output_plugin.OutputPluginBatchProcessingStatus.FromSerializedBytes(
      proto.SerializeToString()
  )
