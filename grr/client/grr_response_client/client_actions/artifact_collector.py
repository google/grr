#!/usr/bin/env python
"""The client artifact collector."""
from __future__ import unicode_literals


from future.utils import iteritems

from grr_response_client import actions
from grr_response_client import vfs
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import file_finder
from grr_response_client.client_actions import network
from grr_response_client.client_actions import operating_system
from grr_response_client.client_actions import standard
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import parser as parser_lib
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
# The client artifact collector parses the responses on the client. So the
# parsers have to be loaded for the results to be processed.
# pylint: disable=unused-import
from grr_response_core.lib.parsers import registry_init
# pylint: enable=unused-import
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict


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

    # The knowledge base is either (partially) filled or an empty rdf object.
    self.knowledge_base = args.knowledge_base

    self.ignore_interpolation_errors = args.ignore_interpolation_errors
    for artifact in args.artifacts:
      self.Progress()
      collected_artifact = self._CollectArtifact(
          artifact, apply_parsers=args.apply_parsers)
      if artifact.requested_by_user:
        result.collected_artifacts.append(collected_artifact)

    result.knowledge_base = self.knowledge_base

    # TODO(user): Limit the number of bytes and send multiple responses.
    # e.g. grr_rekall.py RESPONSE_CHUNK_SIZE
    self.SendReply(result)

  def _CollectArtifact(self, artifact, apply_parsers):
    """Returns an `CollectedArtifact` rdf object for the requested artifact."""
    artifact_result = rdf_artifacts.CollectedArtifact(name=artifact.name)

    parsers = []
    if apply_parsers:
      parsers = parser_lib.Parser.GetClassesByArtifact(artifact.name)

    for source_result_list in self._ProcessSources(artifact.sources, parsers):
      for response in source_result_list:
        action_result = rdf_artifacts.ClientActionResult()
        action_result.type = response.__class__.__name__
        action_result.value = response
        artifact_result.action_results.append(action_result)
        self.UpdateKnowledgeBase(response, artifact.provides)

    return artifact_result

  def UpdateKnowledgeBase(self, response, provides):
    """Set values in the knowledge base based on responses."""

    if isinstance(response, rdf_anomaly.Anomaly):
      return

    if isinstance(response, rdf_client.User):
      self.knowledge_base.MergeOrAddUser(response)
      return

    if isinstance(response, rdf_protodict.Dict):
      response_dict = response.ToDict()
      for attribute, value in iteritems(response_dict):
        if attribute in provides:
          self.SetKnowledgeBaseValue(attribute, value)
      return

    # If its not a dict we only support a single value.
    if len(provides) == 1:
      self.SetKnowledgeBaseValue(provides[0], response)

  def SetKnowledgeBaseValue(self, attribute, value):
    if isinstance(value, rdfvalue.RDFString):
      value = unicode(value)
    elif isinstance(value, rdf_client_fs.StatEntry):
      value = value.registry_data.GetValue()
    if value:
      self.knowledge_base.Set(attribute, value)

  def _ProcessSources(self, sources, parsers):
    """Iterates through sources yielding action responses."""
    for source in sources:
      for action, request in self._ParseSourceType(source):
        yield self._RunClientAction(action, request, parsers, source.path_type)

  def _RunClientAction(self, action, request, parsers, path_type):
    """Runs the client action  with the request and parses the result."""

    responses = list(action(request))

    if not parsers:
      return responses

    # filter parsers by process_together setting
    multi_parsers = []
    single_parsers = []
    for parser in parsers:
      parser_obj = parser()
      if parser_obj.process_together:
        multi_parsers.append(parser_obj)
      else:
        single_parsers.append(parser_obj)

    # parse the responses
    parsed_responses = []

    for response in responses:
      for parser in single_parsers:
        for res in ParseSingleResponse(parser, response, self.knowledge_base,
                                       path_type):
          parsed_responses.append(res)

    for parser in multi_parsers:
      for res in ParseMultipleResponses(parser, responses, self.knowledge_base,
                                        path_type):
        parsed_responses.append(res)

    return parsed_responses

  def _ParseSourceType(self, source):
    """Calls the correct processing function for the given source."""
    type_name = rdf_artifacts.ArtifactSource.SourceType
    switch = {
        type_name.COMMAND: self._ProcessCommandSource,
        type_name.DIRECTORY: self._ProcessFileSource,
        type_name.FILE: self._ProcessFileSource,
        type_name.GREP: self._ProcessGrepSource,
        type_name.REGISTRY_KEY: _NotImplemented,
        type_name.REGISTRY_VALUE: self._ProcessRegistryValueSource,
        type_name.WMI: self._ProcessWmiSource,
        type_name.ARTIFACT_FILES: self._ProcessArtifactFilesSource,
        type_name.GRR_CLIENT_ACTION: self._ProcessClientActionSource
    }
    source_type = source.base_source.type

    try:
      source_type_action = switch[source_type]
    except KeyError:
      raise ValueError("Incorrect source type: %s" % source_type)

    for res in source_type_action(source):
      yield res

  def _ProcessGrepSource(self, source):
    """Find files fulfilling regex conditions."""
    attributes = source.base_source.attributes
    paths = artifact_utils.InterpolateListKbAttributes(
        attributes["paths"], self.knowledge_base,
        self.ignore_interpolation_errors)
    regex_list = artifact_utils.InterpolateListKbAttributes(
        attributes["content_regex_list"], self.knowledge_base,
        self.ignore_interpolation_errors)
    regex = utils.RegexListDisjunction(regex_list)
    condition = rdf_file_finder.FileFinderCondition.ContentsRegexMatch(
        regex=regex, mode="ALL_HITS")
    file_finder_action = rdf_file_finder.FileFinderAction.Stat()
    request = rdf_file_finder.FileFinderArgs(
        paths=paths,
        action=file_finder_action,
        conditions=[condition],
        follow_links=True)
    action = file_finder.FileFinderOSFromClient

    yield action, request

  def _ProcessArtifactFilesSource(self, source):
    """Get artifact responses, extract paths and send corresponding files."""

    if source.path_type != rdf_paths.PathSpec.PathType.OS:
      raise ValueError("Only supported path type is OS.")

    # TODO(user): Check paths for GlobExpressions.
    # If it contains a * then FileFinder will interpret it as GlobExpression and
    # expand it. FileFinderArgs needs an option to treat paths literally.

    paths = []
    pathspec_attribute = source.base_source.attributes.get("pathspec_attribute")

    for source_result_list in self._ProcessSources(
        source.artifact_sources, parsers=[]):
      for response in source_result_list:
        path = _ExtractPath(response, pathspec_attribute)
        if path is not None:
          paths.append(path)

    file_finder_action = rdf_file_finder.FileFinderAction.Download()
    request = rdf_file_finder.FileFinderArgs(
        paths=paths, pathtype=source.path_type, action=file_finder_action)
    action = file_finder.FileFinderOSFromClient

    yield action, request

  def _ProcessFileSource(self, source):
    """Glob paths and return StatEntry objects."""

    if source.path_type != rdf_paths.PathSpec.PathType.OS:
      raise ValueError("Only supported path type is OS.")

    paths = artifact_utils.InterpolateListKbAttributes(
        source.base_source.attributes["paths"], self.knowledge_base,
        self.ignore_interpolation_errors)

    file_finder_action = rdf_file_finder.FileFinderAction.Stat()
    request = rdf_file_finder.FileFinderArgs(
        paths=paths, pathtype=source.path_type, action=file_finder_action)
    action = file_finder.FileFinderOSFromClient

    yield action, request

  def _ProcessWmiSource(self, source):
    # pylint: disable= g-import-not-at-top
    from grr_response_client.client_actions.windows import windows
    # pylint: enable=g-import-not-at-top
    action = windows.WmiQueryFromClient
    query = source.base_source.attributes["query"]
    queries = artifact_utils.InterpolateKbAttributes(
        query, self.knowledge_base, self.ignore_interpolation_errors)
    base_object = source.base_source.attributes.get("base_object")
    for query in queries:
      request = rdf_client_action.WMIRequest(
          query=query, base_object=base_object)
      yield action, request

  def _ProcessClientActionSource(self, source):

    request = {}
    action_name = source.base_source.attributes["client_action"]

    if action_name == "GetHostname":
      action = admin.GetHostnameFromClient

    elif action_name == "ListProcesses":
      action = standard.ListProcessesFromClient

    elif action_name == "ListNetworkConnections":
      action = network.ListNetworkConnectionsFromClient
      request = rdf_client_action.ListNetworkConnectionsArgs()

    elif action_name == "EnumerateInterfaces":
      action = operating_system.EnumerateInterfacesFromClient

    elif action_name == "EnumerateUsers":
      action = operating_system.EnumerateUsersFromClient

    elif action_name == "EnumerateFilesystems":
      action = operating_system.EnumerateFilesystemsFromClient

    elif action_name == "StatFS":
      action = standard.StatFSFromClient
      paths = []
      if "action_args" in source.base_source.attributes:
        if "path_list" in source.base_source.attributes["action_args"]:
          paths = source.base_source.attributes["action_args"]["path_list"]
      request = rdf_client_action.StatFSRequest(
          path_list=paths, pathtype=source.path_type)

    elif action_name == "OSXEnumerateRunningServices":
      action = operating_system.EnumerateRunningServices

    else:
      raise ValueError("Incorrect action type: %s" % action_name)

    yield action, request

  def _ProcessCommandSource(self, source):
    """Prepare a request for calling the execute command action."""
    action = standard.ExecuteCommandFromClient
    request = rdf_client_action.ExecuteRequest(
        cmd=source.base_source.attributes["cmd"],
        args=source.base_source.attributes["args"],
    )
    yield action, request

  def _ProcessRegistryValueSource(self, source):
    new_paths = set()
    has_glob = False
    for kvdict in source.base_source.attributes["key_value_pairs"]:
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
      action = standard.GetFileStatFromClient
      for new_path in new_paths:
        pathspec = rdf_paths.PathSpec(
            path=new_path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
        request = rdf_client_action.GetFileStatRequest(pathspec=pathspec)
        yield action, request


# TODO(user): Think about a different way to call the Parse method of each
# supported parser. If the method signature is declared in the parser subtype
# classes then isinstance has to be used. And if it was declared in Parser then
# every Parser would have to be changed.
def ParseSingleResponse(parser_obj, response, knowledge_base, path_type):
  """Call the parser for the response and yield rdf values.

  Args:
    parser_obj: An instance of the parser.
    response: An rdf value response from a client action.
    knowledge_base: containing information about the client.
    path_type: Specifying whether OS or TSK paths are used.
  Returns:
    An iterable of rdf value responses.
  Raises:
    ValueError: If the requested parser is not supported.
  """
  parse = parser_obj.Parse

  if isinstance(parser_obj, parser_lib.CommandParser):
    result_iterator = parse(
        cmd=response.request.cmd,
        args=response.request.args,
        stdout=response.stdout,
        stderr=response.stderr,
        return_val=response.exit_status,
        time_taken=response.time_used,
        knowledge_base=knowledge_base)
  elif isinstance(parser_obj, parser_lib.WMIQueryParser):
    # At the moment no WMIQueryParser actually uses the passed arguments query
    # and knowledge_base.
    result_iterator = parse(response)
  elif isinstance(parser_obj, parser_lib.FileParser):
    file_obj = vfs.VFSOpen(response.pathspec)
    stat = rdf_client_fs.StatEntry(pathspec=response.pathspec)
    result_iterator = parse(stat, file_obj, None)
  elif isinstance(parser_obj,
                  (parser_lib.RegistryParser, parser_lib.RekallPluginParser,
                   parser_lib.RegistryValueParser, parser_lib.GrepParser)):
    result_iterator = parse(response, knowledge_base)
  elif isinstance(parser_obj, parser_lib.ArtifactFilesParser):
    result_iterator = parse(response, knowledge_base, path_type)
  else:
    raise ValueError("Unsupported parser: %s" % parser_obj)
  return result_iterator


def ParseMultipleResponses(parser_obj, responses, knowledge_base, path_type):
  """Call the parser for the responses and yield rdf values.

  Args:
    parser_obj: An instance of the parser.
    responses: A list of rdf value responses from a client action.
    knowledge_base: containing information about the client.
    path_type: Specifying whether OS or TSK paths are used.

  Returns:
    An iterable of rdf value responses.
  Raises:
    ValueError: If the requested parser is not supported.
  """
  parse_multiple = parser_obj.ParseMultiple

  if isinstance(parser_obj, parser_lib.FileParser):
    file_objects = []
    stats = []
    for res in responses:
      try:
        file_objects.append(vfs.VFSOpen(res.pathspec))
        stats.append(rdf_client_fs.StatEntry(pathspec=res.pathspec))
      except IOError:
        continue
    result_iterator = parse_multiple(stats, file_objects, knowledge_base)
  elif isinstance(parser_obj,
                  (parser_lib.RegistryParser, parser_lib.RegistryValueParser)):
    result_iterator = parse_multiple(responses, knowledge_base)
  elif isinstance(parser_obj, parser_lib.ArtifactFilesParser):
    result_iterator = parse_multiple(responses, knowledge_base, path_type)
  else:
    raise ValueError("Unsupported parser: %s" % parser_obj)
  return result_iterator


def _ExtractPath(response, pathspec_attribute=None):
  """Returns the path from a client action response as a string.

  Args:
    response: A client action response.
    pathspec_attribute: Specifies the field which stores the pathspec.

  Returns:
    The path as a string or None if no path is found.

  """
  path_specification = response

  if pathspec_attribute is not None:
    if response.HasField(pathspec_attribute):
      path_specification = response.Get(pathspec_attribute)

  if path_specification.HasField("pathspec"):
    path_specification = path_specification.pathspec

  if path_specification.HasField("path"):
    path_specification = path_specification.path

  if isinstance(path_specification, unicode):
    return path_specification
  return None
