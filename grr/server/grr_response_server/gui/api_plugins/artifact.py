#!/usr/bin/env python
"""API handlers for accessing artifacts."""

from grr.lib import parser

from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import artifact_pb2
from grr.server.grr_response_server import artifact
from grr.server.grr_response_server import artifact_registry

from grr.server.grr_response_server.gui import api_call_handler_base


class ApiListArtifactsArgs(rdf_structs.RDFProtoStruct):
  protobuf = artifact_pb2.ApiListArtifactsArgs


class ApiListArtifactsResult(rdf_structs.RDFProtoStruct):
  protobuf = artifact_pb2.ApiListArtifactsResult
  rdf_deps = [
      artifact_registry.ArtifactDescriptor,
  ]


class ApiListArtifactsHandler(api_call_handler_base.ApiCallHandler):
  """Renders available artifacts definitions."""

  args_type = ApiListArtifactsArgs
  result_type = ApiListArtifactsResult

  def BuildArtifactDescriptors(self, artifacts):
    result = []
    for artifact_val in artifacts:
      descriptor = artifact_registry.ArtifactDescriptor(
          artifact=artifact_val,
          dependencies=sorted(artifact_val.GetArtifactDependencies()),
          path_dependencies=sorted(artifact_val.GetArtifactPathDependencies()),
          error_message=artifact_val.error_message,
          is_custom=artifact_val.loaded_from.startswith("datastore:"))

      for processor in parser.Parser.GetClassesByArtifact(artifact_val.name):
        descriptor.processors.append(
            artifact_registry.ArtifactProcessorDescriptor(
                name=processor.__name__,
                output_types=processor.output_types,
                description=processor.GetDescription()))

      result.append(descriptor)

    return result

  def Handle(self, args, token=None):
    """Get available artifact information for rendering."""

    # Get all artifacts that aren't Bootstrap and aren't the base class.
    artifacts = sorted(
        artifact_registry.REGISTRY.GetArtifacts(
            reload_datastore_artifacts=True),
        key=lambda art: art.name)

    total_count = len(artifacts)

    if args.count:
      artifacts = artifacts[args.offset:args.offset + args.count]
    else:
      artifacts = artifacts[args.offset:]

    descriptors = self.BuildArtifactDescriptors(artifacts)
    return ApiListArtifactsResult(items=descriptors, total_count=total_count)


class ApiUploadArtifactArgs(rdf_structs.RDFProtoStruct):
  protobuf = artifact_pb2.ApiUploadArtifactArgs


class ApiUploadArtifactHandler(api_call_handler_base.ApiCallHandler):
  """Handles artifact upload."""

  args_type = ApiUploadArtifactArgs

  def Handle(self, args, token=None):
    artifact.UploadArtifactYamlFile(
        args.artifact, overwrite=True, overwrite_system_artifacts=False)


class ApiDeleteArtifactsArgs(rdf_structs.RDFProtoStruct):
  protobuf = artifact_pb2.ApiDeleteArtifactsArgs


class ApiDeleteArtifactsHandler(api_call_handler_base.ApiCallHandler):
  """Handles artifact deletion."""

  args_type = ApiDeleteArtifactsArgs

  def Handle(self, args, token=None):
    artifact_registry.DeleteArtifactsFromDatastore(set(args.names))
