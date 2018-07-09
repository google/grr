#!/usr/bin/env python
"""The client artifact collector."""

from grr_response_client import actions
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import standard
from grr.core.grr_response_core.lib import artifact_utils
from grr.core.grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr.core.grr_response_core.lib.rdfvalues import client as rdf_client
from grr.core.grr_response_core.lib.rdfvalues import paths as rdf_paths


class ArtifactCollector(actions.ActionPlugin):
  """The client side artifact collector implementation."""

  in_rdfvalue = rdf_artifacts.ClientArtifactCollectorArgs
  out_rdfvalues = [rdf_artifacts.ClientArtifactCollectorResult]

  def Run(self, args):
    result = rdf_artifacts.ClientArtifactCollectorResult()
    self.knowledge_base = args.knowledge_base
    self.ignore_interpolation_errors = args.ignore_interpolation_errors
    for artifact in args.artifacts:
      self.Progress()
      artifact_result = rdf_artifacts.CollectedArtifact(name=artifact.name)
      for source in artifact.sources:
        action_response = rdf_artifacts.ClientActionResponse()
        for action, request, response_field in self._ProcessSource(source):
          for res in action.Start(request):
            getattr(action_response, response_field).append(res)
        artifact_result.action_responses.append(action_response)

      result.collected_artifacts.append(artifact_result)
    # TODO(user): Limit the number of bytes and send multiple responses.
    self.SendReply(result)

  def _ProcessSource(self, args):
    source_type = args.base_source.type
    if source_type == rdf_artifacts.ArtifactSource.SourceType.GRR_CLIENT_ACTION:
      yield self._ProcessClientActionSource()
    elif source_type == rdf_artifacts.ArtifactSource.SourceType.COMMAND:
      yield self._ProcessCommandSource(args)
    elif source_type == rdf_artifacts.ArtifactSource.SourceType.REGISTRY_VALUE:
      for res in self._ProcessRegistryValueSource(args):
        yield res
    else:
      raise ValueError("Incorrect source type: %s" % source_type)

  def _ProcessClientActionSource(self):
    action = admin.GetHostname
    response_field = "hostname"
    return action, {}, response_field

  def _ProcessCommandSource(self, args):
    action = standard.ExecuteCommand
    request = rdf_client.ExecuteRequest(
        cmd=args.base_source.attributes["cmd"],
        args=args.base_source.attributes["args"],
    )
    response_field = "execute_response"
    return action, request, response_field

  def _ProcessRegistryValueSource(self, args):
    new_paths = set()
    has_glob = False
    for kvdict in args.base_source.attributes["key_value_pairs"]:
      if "*" in kvdict["key"] or rdf_paths.GROUPING_PATTERN.search(
          kvdict["key"]):
        has_glob = True
      if kvdict["value"]:
        path = "\\".join((kvdict["key"], kvdict["value"]))
      else:
        path = kvdict["key"]
      expanded_paths = artifact_utils.InterpolateKbAttributes(
          path,
          self.knowledge_base,
          ignore_errors=self.ignore_interpolation_errors)
      new_paths.update(expanded_paths)
    if has_glob:
      # TODO(user): If a path has a wildcard we need to glob the filesystem
      # for patterns to collect matching files. The corresponding flow is
      # filesystem.Glob.
      pass
    else:
      action = standard.GetFileStat
      response_field = "file_stat"
      for new_path in new_paths:
        pathspec = rdf_paths.PathSpec(
            path=new_path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
        request = rdf_client.GetFileStatRequest(pathspec=pathspec)
        yield action, request, response_field
