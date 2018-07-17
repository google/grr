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
        for action, request in self._ProcessSource(source):
          for res in action.Start(request):
            action_result = rdf_artifacts.ClientActionResult()
            action_result.type = res.__class__.__name__
            action_result.value = res
            artifact_result.action_results.append(action_result)

      result.collected_artifacts.append(artifact_result)
    # TODO(user): Limit the number of bytes and send multiple responses.
    # e.g. grr_rekall.py RESPONSE_CHUNK_SIZE
    self.SendReply(result)

  def _ProcessSource(self, args):
    source_type = args.base_source.type
    type_name = rdf_artifacts.ArtifactSource.SourceType
    if source_type == type_name.COMMAND:
      yield self._ProcessCommandSource(args)
    elif source_type == type_name.DIRECTORY:
      # TODO(user): Not implemented yet.
      raise NotImplementedError()
    elif source_type == type_name.FILE:
      # TODO(user): Not implemented yet.
      # Created action `Download` in file_finder.py with classmethod Start that
      # would take FileFinderArgs as input and return a FileFinderResult object.
      # opts = rdf_file_finder.FileFinderDownloadActionOptions(
      #     max_size=args.max_bytesize
      # )
      # action = rdf_file_finder.FileFinderAction(
      #     action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD,
      #     download=opts
      # )
      # request = rdf_file_finder.FileFinderArgs(
      #     paths=args.paths,
      #     pathtype=args.pathtype,
      #     action=action
      # )

      # action = subactions.DownloadAction

      raise NotImplementedError()
    elif source_type == type_name.GREP:
      # TODO(user): Not implemented yet.
      raise NotImplementedError()
    elif source_type == type_name.REGISTRY_KEY:
      # TODO(user): Not implemented yet.
      raise NotImplementedError()
    elif source_type == type_name.REGISTRY_VALUE:
      for res in self._ProcessRegistryValueSource(args):
        yield res
    elif source_type == type_name.WMI:
      for res in self._ProcessWmiSource(args):
        yield res
    elif source_type == type_name.ARTIFACT_GROUP:
      # TODO(user): Not implemented yet.
      raise NotImplementedError()
    elif source_type == type_name.ARTIFACT_FILES:
      # TODO(user): Not implemented yet.
      raise NotImplementedError()
    elif source_type == type_name.GRR_CLIENT_ACTION:
      yield self._ProcessClientActionSource(args)
    else:
      raise ValueError("Incorrect source type: %s" % source_type)

  def _ProcessWmiSource(self, args):
    # pylint: disable= g-import-not-at-top
    from grr_response_client.client_actions.windows import windows
    # pylint: enable=g-import-not-at-top
    action = windows.WmiQuery
    query = args.base_source.attributes["query"]
    queries = artifact_utils.InterpolateKbAttributes(
        query, self.knowledge_base, self.ignore_interpolation_errors)
    base_object = args.base_source.attributes.get("base_object")
    for query in queries:
      request = rdf_client.WMIRequest(query=query, base_object=base_object)
      yield action, request

  def _ProcessClientActionSource(self, args):
    for action_name in args.base_source.attributes["client_action"].keys():
      if action_name == "GetHostname":
        action = admin.GetHostname
        return action, {}
      else:
        raise ValueError("Action %s not implemented yet." % action_name)

  def _ProcessCommandSource(self, args):
    action = standard.ExecuteCommand
    request = rdf_client.ExecuteRequest(
        cmd=args.base_source.attributes["cmd"],
        args=args.base_source.attributes["args"],
    )
    return action, request

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
      for new_path in new_paths:
        pathspec = rdf_paths.PathSpec(
            path=new_path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
        request = rdf_client.GetFileStatRequest(pathspec=pathspec)
        yield action, request
