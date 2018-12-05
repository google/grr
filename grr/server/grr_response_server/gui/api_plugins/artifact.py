#!/usr/bin/env python
"""API handlers for accessing artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import parser

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import artifact_pb2
from grr_response_server import artifact
from grr_response_server import artifact_registry

from grr_response_server.gui import api_call_handler_base


class ApiListArtifactsArgs(rdf_structs.RDFProtoStruct):
  protobuf = artifact_pb2.ApiListArtifactsArgs


class ApiListArtifactsResult(rdf_structs.RDFProtoStruct):
  protobuf = artifact_pb2.ApiListArtifactsResult
  rdf_deps = [
      rdf_artifacts.ArtifactDescriptor,
  ]


class ApiListArtifactsHandler(api_call_handler_base.ApiCallHandler):
  """Renders available artifacts definitions."""

  args_type = ApiListArtifactsArgs
  result_type = ApiListArtifactsResult

  def BuildArtifactDescriptors(self, artifacts_list):
    result = []
    for artifact_val in artifacts_list:
      descriptor = rdf_artifacts.ArtifactDescriptor(
          artifact=artifact_val,
          dependencies=sorted(
              artifact_registry.GetArtifactDependencies(artifact_val)),
          path_dependencies=sorted(
              artifact_registry.GetArtifactPathDependencies(artifact_val)),
          error_message=artifact_val.error_message,
          is_custom=artifact_val.loaded_from.startswith("datastore:"))

      for processor in parser.Parser.GetClassesByArtifact(artifact_val.name):
        descriptor.processors.append(
            rdf_artifacts.ArtifactProcessorDescriptor(
                name=processor.__name__,
                output_types=processor.output_types,
                description=processor.GetDescription()))

      result.append(descriptor)

    return result

  def Handle(self, args, token=None):
    """Get available artifact information for rendering."""

    # Get all artifacts that aren't Bootstrap and aren't the base class.
    artifacts_list = sorted(
        artifact_registry.REGISTRY.GetArtifacts(
            reload_datastore_artifacts=True),
        key=lambda art: art.name)

    total_count = len(artifacts_list)

    if args.count:
      artifacts_list = artifacts_list[args.offset:args.offset + args.count]
    else:
      artifacts_list = artifacts_list[args.offset:]

    descriptors = self.BuildArtifactDescriptors(artifacts_list)
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
