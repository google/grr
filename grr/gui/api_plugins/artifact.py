#!/usr/bin/env python
"""API handlers for accessing artifacts."""

from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import parsers
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "Artifacts"


class ApiListArtifactsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListArtifactsArgs


class ApiListArtifactsHandler(api_call_handler_base.ApiCallHandler):
  """Renders available artifacts definitions."""

  category = CATEGORY
  args_type = ApiListArtifactsArgs

  def RenderArtifacts(self, artifacts):
    result = []
    for artifact_val in artifacts:
      descriptor = artifact_registry.ArtifactDescriptor(
          artifact=artifact_val,
          artifact_source=artifact_val.ToPrettyJson(extended=True),
          dependencies=sorted(artifact_val.GetArtifactDependencies()),
          path_dependencies=sorted(artifact_val.GetArtifactPathDependencies()),
          error_message=artifact_val.error_message,
          is_custom=artifact_val.loaded_from.startswith("datastore:"))

      for processor in parsers.Parser.GetClassesByArtifact(artifact_val.name):
        descriptor.processors.append(
            artifact_registry.ArtifactProcessorDescriptor(
                name=processor.__name__,
                output_types=processor.output_types,
                description=processor.GetDescription()))

      result.append(api_value_renderers.RenderValue(descriptor))

    return result

  def Render(self, args, token=None):
    """Get available artifact information for rendering."""

    # Get all artifacts that aren't Bootstrap and aren't the base class.
    artifacts = sorted(artifact_registry.REGISTRY.GetArtifacts(
        reload_datastore_artifacts=True), key=lambda art: art.name)

    total_count = len(artifacts)

    if args.count:
      artifacts = artifacts[args.offset:args.offset + args.count]
    else:
      artifacts = artifacts[args.offset:]

    rendered_artifacts = self.RenderArtifacts(artifacts)

    return dict(total_count=total_count,
                offset=args.offset,
                count=len(rendered_artifacts),
                items=rendered_artifacts)


class ApiUploadArtifactArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiUploadArtifactArgs


class ApiUploadArtifactHandler(api_call_handler_base.ApiCallHandler):
  """Handles artifact upload."""

  category = CATEGORY
  args_type = ApiUploadArtifactArgs

  def Render(self, args, token=None):
    urn = artifact.UploadArtifactYamlFile(args.artifact, token=token)
    return dict(status="OK", urn=utils.SmartStr(urn))


class ApiDeleteArtifactsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiDeleteArtifactsArgs


class ApiDeleteArtifactsHandler(api_call_handler_base.ApiCallHandler):
  """Handles artifact deletion."""

  category = CATEGORY
  args_type = ApiDeleteArtifactsArgs

  def Render(self, args, token=None):
    artifacts = sorted(artifact_registry.REGISTRY.GetArtifacts(
        reload_datastore_artifacts=True))

    deps = set()
    to_delete = set(args.names)
    for artifact_obj in artifacts:
      deps.update(artifact_obj.GetArtifactDependencies() & to_delete)

    if deps:
      raise ValueError(
          "Artifact(s) %s depend(s) on one of the artifacts to delete." % (
              ",".join(list(deps))))

    with aff4.FACTORY.Create("aff4:/artifact_store", mode="r",
                             aff4_type="RDFValueCollection",
                             token=token) as store:
      all_artifacts = list(store)

    filtered_artifacts, found_artifacts = [], []
    for artifact_value in all_artifacts:
      if artifact_value.name in to_delete:
        found_artifacts.append(artifact_value)
      else:
        filtered_artifacts.append(artifact_value)

    if len(found_artifacts) != len(to_delete):
      not_found = to_delete - set(found_artifacts)
      raise ValueError(
          "Artifact(s) to delete (%s) not found." % ",".join(list(not_found)))

    # TODO(user): this is ugly and error- and race-condition- prone.
    # We need to store artifacts not in an RDFValueCollection, which is an
    # append-only object, but in some different way that allows easy
    # deletion. Possible option - just store each artifact in a separate object
    # in the same folder.
    aff4.FACTORY.Delete("aff4:/artifact_store", token=token)

    with aff4.FACTORY.Create("aff4:/artifact_store", mode="w",
                             aff4_type="RDFValueCollection",
                             token=token) as store:
      for artifact_value in filtered_artifacts:
        store.Add(artifact_value)

    for artifact_value in to_delete:
      artifact_registry.REGISTRY.UnregisterArtifact(artifact_value)

    return dict(status="OK")
