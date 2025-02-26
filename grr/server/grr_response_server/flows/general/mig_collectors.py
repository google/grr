#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import flows_pb2
from grr_response_server.flows.general import collectors


def ToProtoArtifactFilesDownloaderFlowArgs(
    rdf: collectors.ArtifactFilesDownloaderFlowArgs,
) -> flows_pb2.ArtifactFilesDownloaderFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactFilesDownloaderFlowArgs(
    proto: flows_pb2.ArtifactFilesDownloaderFlowArgs,
) -> collectors.ArtifactFilesDownloaderFlowArgs:
  return collectors.ArtifactFilesDownloaderFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoArtifactFilesDownloaderResult(
    rdf: collectors.ArtifactFilesDownloaderResult,
) -> flows_pb2.ArtifactFilesDownloaderResult:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactFilesDownloaderResult(
    proto: flows_pb2.ArtifactFilesDownloaderResult,
) -> collectors.ArtifactFilesDownloaderResult:
  return collectors.ArtifactFilesDownloaderResult.FromSerializedBytes(
      proto.SerializeToString()
  )
