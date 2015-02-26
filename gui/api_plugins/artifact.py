#!/usr/bin/env python
"""API renderers for accessing artifacts."""

from grr.gui import api_call_renderers

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import registry


class ApiArtifactRenderer(api_call_renderers.ApiCallRenderer):
  """Renders available artifacts definitions."""

  def RenderArtifacts(self, artifacts, custom_artifacts=None):
    if custom_artifacts is None:
      custom_artifacts = set()

    # Convert artifacts into a dict usable from javascript.
    artifact_dict = {}
    for artifact_name, artifact_val in artifacts.items():
      processors = []
      for processor in parsers.Parser.GetClassesByArtifact(artifact_name):
        processors.append({"name": processor.__name__,
                           "output_types": processor.output_types,
                           "doc": processor.GetDescription()})
      is_custom = artifact_name in custom_artifacts
      artifact_dict[artifact_name] = {"artifact": artifact_val.ToExtendedDict(),
                                      "processors": processors,
                                      "custom": is_custom}

    return artifact_dict

  def Render(self, unused_args, token=None):
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
    for value in collection:
      custom_artifacts.add(value.name)

    # Get all artifacts that aren't Bootstrap and aren't the base class.
    artifacts = {}
    artifact.LoadArtifactsFromDatastore(token=token)

    for name, artifact_val in artifact_lib.ArtifactRegistry.artifacts.items():
      artifacts[name] = artifact_val

    return self.RenderArtifacts(artifacts, custom_artifacts=custom_artifacts)


class ApiArtifactInitHook(registry.InitHook):

  def RunOnce(self):
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/artifacts", ApiArtifactRenderer)
