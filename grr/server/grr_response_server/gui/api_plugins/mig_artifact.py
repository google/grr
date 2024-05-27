#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import artifact_pb2
from grr_response_server.gui.api_plugins import artifact


def ToProtoApiListArtifactsArgs(
    rdf: artifact.ApiListArtifactsArgs,
) -> artifact_pb2.ApiListArtifactsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListArtifactsArgs(
    proto: artifact_pb2.ApiListArtifactsArgs,
) -> artifact.ApiListArtifactsArgs:
  return artifact.ApiListArtifactsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListArtifactsResult(
    rdf: artifact.ApiListArtifactsResult,
) -> artifact_pb2.ApiListArtifactsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListArtifactsResult(
    proto: artifact_pb2.ApiListArtifactsResult,
) -> artifact.ApiListArtifactsResult:
  return artifact.ApiListArtifactsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiUploadArtifactArgs(
    rdf: artifact.ApiUploadArtifactArgs,
) -> artifact_pb2.ApiUploadArtifactArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiUploadArtifactArgs(
    proto: artifact_pb2.ApiUploadArtifactArgs,
) -> artifact.ApiUploadArtifactArgs:
  return artifact.ApiUploadArtifactArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiDeleteArtifactsArgs(
    rdf: artifact.ApiDeleteArtifactsArgs,
) -> artifact_pb2.ApiDeleteArtifactsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiDeleteArtifactsArgs(
    proto: artifact_pb2.ApiDeleteArtifactsArgs,
) -> artifact.ApiDeleteArtifactsArgs:
  return artifact.ApiDeleteArtifactsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
