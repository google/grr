#!/usr/bin/env python
"""API renderers for accessing artifacts."""

from grr.gui import api_call_renderer_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_registry
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


class ApiArtifactsRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiArtifactsRendererArgs


class ApiArtifactsRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders available artifacts definitions."""

  args_type = ApiArtifactsRendererArgs

  def RenderArtifacts(self, artifacts, custom_artifacts=None):
    if custom_artifacts is None:
      custom_artifacts = set()

    result = []
    for artifact_val in artifacts:
      descriptor = artifact_registry.ArtifactDescriptor(
          artifact=artifact_val,
          artifact_source=artifact_val.ToPrettyJson(extended=True),
          dependencies=sorted(artifact_val.GetArtifactDependencies()),
          path_dependencies=sorted(artifact_val.GetArtifactPathDependencies()),
          is_custom=artifact_val.name in custom_artifacts)

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

    # get custom artifacts from data store
    artifact_urn = rdfvalue.RDFURN("aff4:/artifact_store")
    try:
      collection = aff4.FACTORY.Open(artifact_urn,
                                     aff4_type="RDFValueCollection",
                                     token=token)
    except IOError:
      collection = {}

    custom_artifacts = set()
    for artifact_val in collection:
      custom_artifacts.add(artifact_val.name)

    # Get all artifacts that aren't Bootstrap and aren't the base class.
    artifacts = sorted(artifact_registry.REGISTRY.GetArtifacts(
        reload_datastore_artifacts=True))
    total_count = len(artifacts)

    if args.count:
      artifacts = artifacts[args.offset:args.offset + args.count]
    else:
      artifacts = artifacts[args.offset:]

    rendered_artifacts = self.RenderArtifacts(artifacts,
                                              custom_artifacts=custom_artifacts)

    return dict(total_count=total_count,
                offset=args.offset,
                count=len(rendered_artifacts),
                items=rendered_artifacts)


class ApiArtifactsUploadRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiArtifactsUploadRendererArgs


class ApiArtifactsUploadRenderer(api_call_renderer_base.ApiCallRenderer):
  """Handles artifact upload."""

  args_type = ApiArtifactsUploadRendererArgs

  def Render(self, args, token=None):
    urn = artifact.UploadArtifactYamlFile(args.artifact, token=token)
    return dict(status="OK", urn=utils.SmartStr(urn))


class ApiArtifactsDeleteRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiArtifactsDeleteRendererArgs


class ApiArtifactsDeleteRenderer(api_call_renderer_base.ApiCallRenderer):
  """Handles artifact deletion."""

  args_type = ApiArtifactsDeleteRendererArgs

  def Render(self, args, token=None):
    with aff4.FACTORY.Create("aff4:/artifact_store", mode="r",
                             aff4_type="RDFValueCollection",
                             token=token) as store:
      filtered_artifacts = [artifact_value for artifact_value in store
                            if artifact_value.name not in args.names]

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

    return dict(status="OK")
