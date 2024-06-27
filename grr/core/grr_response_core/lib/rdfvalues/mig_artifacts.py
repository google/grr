#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_proto import artifact_pb2
from grr_response_proto import flows_pb2


def ToProtoArtifactSource(
    rdf: rdf_artifacts.ArtifactSource,
) -> artifact_pb2.ArtifactSource:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactSource(
    proto: artifact_pb2.ArtifactSource,
) -> rdf_artifacts.ArtifactSource:
  return rdf_artifacts.ArtifactSource.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoArtifact(rdf: rdf_artifacts.Artifact) -> artifact_pb2.Artifact:
  return rdf.AsPrimitiveProto()


def ToRDFArtifact(proto: artifact_pb2.Artifact) -> rdf_artifacts.Artifact:
  return rdf_artifacts.Artifact.FromSerializedBytes(proto.SerializeToString())


def ToProtoArtifactDescriptor(
    rdf: rdf_artifacts.ArtifactDescriptor,
) -> artifact_pb2.ArtifactDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactDescriptor(
    proto: artifact_pb2.ArtifactDescriptor,
) -> rdf_artifacts.ArtifactDescriptor:
  return rdf_artifacts.ArtifactDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoArtifactCollectorFlowArgs(
    rdf: rdf_artifacts.ArtifactCollectorFlowArgs,
) -> flows_pb2.ArtifactCollectorFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactCollectorFlowArgs(
    proto: flows_pb2.ArtifactCollectorFlowArgs,
) -> rdf_artifacts.ArtifactCollectorFlowArgs:
  return rdf_artifacts.ArtifactCollectorFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoArtifactProgress(
    rdf: rdf_artifacts.ArtifactProgress,
) -> flows_pb2.ArtifactProgress:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactProgress(
    proto: flows_pb2.ArtifactProgress,
) -> rdf_artifacts.ArtifactProgress:
  return rdf_artifacts.ArtifactProgress.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoArtifactCollectorFlowProgress(
    rdf: rdf_artifacts.ArtifactCollectorFlowProgress,
) -> flows_pb2.ArtifactCollectorFlowProgress:
  return rdf.AsPrimitiveProto()


def ToRDFArtifactCollectorFlowProgress(
    proto: flows_pb2.ArtifactCollectorFlowProgress,
) -> rdf_artifacts.ArtifactCollectorFlowProgress:
  return rdf_artifacts.ArtifactCollectorFlowProgress.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientActionResult(
    rdf: rdf_artifacts.ClientActionResult,
) -> artifact_pb2.ClientActionResult:
  return rdf.AsPrimitiveProto()


def ToRDFClientActionResult(
    proto: artifact_pb2.ClientActionResult,
) -> rdf_artifacts.ClientActionResult:
  return rdf_artifacts.ClientActionResult.FromSerializedBytes(
      proto.SerializeToString()
  )
