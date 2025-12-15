#!/usr/bin/env python
"""API handlers for accessing artifacts."""

from typing import Optional

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import mig_artifacts
from grr_response_proto import artifact_pb2
from grr_response_proto.api import artifact_pb2 as api_artifact_pb2
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base


class ApiListArtifactsHandler(api_call_handler_base.ApiCallHandler):
  """Renders available artifacts definitions."""

  proto_args_type = api_artifact_pb2.ApiListArtifactsArgs
  proto_result_type = api_artifact_pb2.ApiListArtifactsResult

  def BuildArtifactDescriptors(
      self,
      artifacts_list: list[rdf_artifacts.Artifact],
  ) -> list[artifact_pb2.ArtifactDescriptor]:
    result = []
    for rdf_artifact in artifacts_list:
      proto_artifact = mig_artifacts.ToProtoArtifact(rdf_artifact)
      descriptor = artifact_pb2.ArtifactDescriptor(
          artifact=proto_artifact,
          dependencies=sorted(
              artifact_registry.GetArtifactDependencies(rdf_artifact)
          ),
          path_dependencies=sorted(
              artifact_registry.GetArtifactPathDependencies(rdf_artifact)
          ),
          error_message=proto_artifact.error_message,
          is_custom=artifact_registry.REGISTRY.IsLoadedFrom(
              proto_artifact.name, "datastore:"
          ),
      )

      result.append(descriptor)

    return result

  def Handle(
      self,
      args: api_artifact_pb2.ApiListArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_artifact_pb2.ApiListArtifactsResult:
    """Get available artifact information for rendering."""

    # Get all artifacts that aren't Bootstrap and aren't the base class.
    artifacts_list = sorted(
        artifact_registry.REGISTRY.GetArtifacts(
            reload_datastore_artifacts=True
        ),
        key=lambda art: art.name,
    )

    total_count = len(artifacts_list)

    if args.count:
      artifacts_list = artifacts_list[args.offset : args.offset + args.count]
    else:
      artifacts_list = artifacts_list[args.offset :]

    descriptors = self.BuildArtifactDescriptors(artifacts_list)
    return api_artifact_pb2.ApiListArtifactsResult(
        items=descriptors, total_count=total_count
    )


class ApiUploadArtifactHandler(api_call_handler_base.ApiCallHandler):
  """Handles artifact upload."""

  proto_args_type = api_artifact_pb2.ApiUploadArtifactArgs

  def Handle(
      self,
      args: api_artifact_pb2.ApiUploadArtifactArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    artifact.UploadArtifactYamlFile(
        args.artifact, overwrite=True, overwrite_system_artifacts=False
    )


class ApiDeleteArtifactsHandler(api_call_handler_base.ApiCallHandler):
  """Handles artifact deletion."""

  proto_args_type = api_artifact_pb2.ApiDeleteArtifactsArgs

  def Handle(
      self,
      args: api_artifact_pb2.ApiDeleteArtifactsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    artifact_registry.DeleteArtifactsFromDatastore(set(args.names))
