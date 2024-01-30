#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_server.flows.general import artifact_fallbacks


def ToProtoArtifactFallbackCollectorArgs(
    rdf: artifact_fallbacks.ArtifactFallbackCollectorArgs,
) -> flows_pb2.ArtifactFallbackCollectorArgs:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactFallbackCollectorArgs(
    proto: flows_pb2.ArtifactFallbackCollectorArgs,
) -> artifact_fallbacks.ArtifactFallbackCollectorArgs:
  return artifact_fallbacks.ArtifactFallbackCollectorArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
