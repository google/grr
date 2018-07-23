#!/usr/bin/env python
"""The client artifact collector."""


from grr_response_client import actions
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import standard
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import parser
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths


def _NotImplemented(args):
  # TODO(user): Not implemented yet. This method can be deleted once the
  # missing source types are supported.
  del args  # Unused
  raise NotImplementedError()


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
      collected_artifact = self._CollectArtifact(
          artifact, apply_parsers=args.apply_parsers)
      result.collected_artifacts.append(collected_artifact)

    # TODO(user): Limit the number of bytes and send multiple responses.
    # e.g. grr_rekall.py RESPONSE_CHUNK_SIZE
    self.SendReply(result)

  def _CollectArtifact(self, artifact, apply_parsers):
    artifact_result = rdf_artifacts.CollectedArtifact(name=artifact.name)

    processors = []
    if apply_parsers:
      processors = parser.Parser.GetClassesByArtifact(artifact.name)

    for source in artifact.sources:
      for action, request in self._ParseSourceType(source):
        responses = self._RunClientAction(action, request, processors)
        for response in responses:
          action_result = rdf_artifacts.ClientActionResult()
          action_result.type = response.__class__.__name__
          action_result.value = response
          artifact_result.action_results.append(action_result)
    return artifact_result

  def _RunClientAction(self, action, request, processors):
    saved_responses = []
    for response in action.Start(request):

      if processors:
        for processor in processors:
          processor_obj = processor()
          if processor_obj.process_together:
            raise NotImplementedError()
          for res in ParseResponse(processor_obj, response,
                                   self.knowledge_base):
            saved_responses.append(res)
      else:
        saved_responses.append(response)
    return saved_responses

  def _ParseSourceType(self, args):
    type_name = rdf_artifacts.ArtifactSource.SourceType
    switch = {
        type_name.COMMAND: self._ProcessCommandSource,
        type_name.DIRECTORY: _NotImplemented,
        type_name.FILE: self._ProcessFileSource,
        type_name.GREP: _NotImplemented,
        type_name.REGISTRY_KEY: _NotImplemented,
        type_name.REGISTRY_VALUE: self._ProcessRegistryValueSource,
        type_name.WMI: self._ProcessWmiSource,
        type_name.ARTIFACT_GROUP: _NotImplemented,
        type_name.ARTIFACT_FILES: _NotImplemented,
        type_name.GRR_CLIENT_ACTION: self._ProcessClientActionSource
    }
    source_type = args.base_source.type

    try:
      source_type_action = switch[source_type]
    except KeyError:
      raise ValueError("Incorrect source type: %s" % args.base_source.type)

    for res in source_type_action(args):
      yield res

  def _ProcessFileSource(self, args):
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
    for action_name in args.base_source.attributes["client_action"]:
      if action_name == "GetHostname":
        action = admin.GetHostname
        yield action, {}
      else:
        raise ValueError("Action %s not implemented yet." % action_name)

  def _ProcessCommandSource(self, args):
    action = standard.ExecuteCommand
    request = rdf_client.ExecuteRequest(
        cmd=args.base_source.attributes["cmd"],
        args=args.base_source.attributes["args"],
    )
    yield action, request

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


# TODO(user): Think about a different way to call the Parse method of each
# supported parser. If the method signature is declared in the parser subtype
# classes then isinstance has to be used. And if it was declared in Parser then
# every Parser would have to be changed.
def ParseResponse(processor_obj, response, knowledge_base):
  """Call the parser for the response and yield rdf values.

  Args:
    processor_obj: An instance of the parser.
    response: An rdf value response from a client action.
    knowledge_base: containing information about the client.
  Returns:
    An iterable of rdf value responses.
  Raises:
    ValueError: If the requested parser is not supported.
  """
  if processor_obj.process_together:
    parse_method = processor_obj.ParseMultiple
  else:
    parse_method = processor_obj.Parse

  if isinstance(processor_obj, parser.CommandParser):
    result_iterator = parse_method(
        cmd=response.request.cmd,
        args=response.request.args,
        stdout=response.stdout,
        stderr=response.stderr,
        return_val=response.exit_status,
        time_taken=response.time_used,
        knowledge_base=knowledge_base)
  elif isinstance(processor_obj, parser.WMIQueryParser):
    # At the moment no WMIQueryParser actually uses the passed arguments query
    # and knowledge_base.
    result_iterator = parse_method(None, response, None)
  elif isinstance(processor_obj, parser.FileParser):
    raise NotImplementedError()
  elif isinstance(processor_obj,
                  (parser.RegistryParser, parser.RekallPluginParser,
                   parser.RegistryValueParser, parser.GenericResponseParser,
                   parser.GrepParser)):
    result_iterator = parse_method(response, knowledge_base)
  elif isinstance(processor_obj, parser.ArtifactFilesParser):
    raise NotImplementedError()
  else:
    raise ValueError("Unsupported parser: %s" % processor_obj)
  return result_iterator
