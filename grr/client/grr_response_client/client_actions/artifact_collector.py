#!/usr/bin/env python
"""The client artifact collector."""
from __future__ import absolute_import
from __future__ import division
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
from grr_response_core.lib import parsers
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
from grr_response_core.lib.util import precondition


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

    if apply_parsers:
      parser_factory = parsers.ArtifactParserFactory(unicode(artifact.name))
    else:
      parser_factory = None

    for source_result_list in self._ProcessSources(artifact.sources,
                                                   parser_factory):
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

  def _ProcessSources(self, sources, parser_factory):
    """Iterates through sources yielding action responses."""
    for source in sources:
      for action, request in self._ParseSourceType(source):
        yield self._RunClientAction(action, request, parser_factory,
                                    source.path_type)

  def _RunClientAction(self, action, request, parser_factory, path_type):
    """Runs the client action  with the request and parses the result."""
    responses = list(action(request))

    if parser_factory is None:
      return responses

    # parse the responses
    parsed_responses = []

    for response in responses:
      for parser in parser_factory.SingleResponseParsers():
        parsed_responses.extend(
            parser.ParseResponse(self.knowledge_base, response, path_type))

      for parser in parser_factory.SingleFileParsers():
        precondition.AssertType(response, rdf_client_fs.StatEntry)
        pathspec = response.pathspec
        with vfs.VFSOpen(pathspec) as filedesc:
          parsed_responses.extend(
              parser.ParseFile(self.knowledge_base, pathspec, filedesc))

    for parser in parser_factory.MultiResponseParsers():
      parsed_responses.extend(
          parser.ParseResponses(self.knowledge_base, responses))

    for parser in parser_factory.MultiFileParsers():
      precondition.AssertIterableType(responses, rdf_client_fs.StatEntry)
      pathspecs = [response.pathspec for response in responses]
      with vfs.VFSMultiOpen(pathspecs) as filedescs:
        parsed_responses.extend(
            parser.ParseFiles(self.knowledge_base, pathspecs, filedescs))

    return parsed_responses

  def _ParseSourceType(self, source):
    """Calls the correct processing function for the given source."""
    type_name = rdf_artifacts.ArtifactSource.SourceType
    switch = {
        type_name.COMMAND: self._ProcessCommandSource,
        type_name.DIRECTORY: self._ProcessFileSource,
        type_name.FILE: self._ProcessFileSource,
        type_name.GREP: self._ProcessGrepSource,
        type_name.REGISTRY_KEY: self._ProcessRegistryKeySource,
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

  def _ProcessRegistryKeySource(self, source):
    """Glob for paths in the registry."""
    keys = source.base_source.attributes.get("keys", [])
    if not keys:
      return

    interpolated_paths = artifact_utils.InterpolateListKbAttributes(
        input_list=keys,
        knowledge_base=self.knowledge_base,
        ignore_errors=self.ignore_interpolation_errors)

    glob_expressions = map(rdf_paths.GlobExpression, interpolated_paths)

    patterns = []
    for pattern in glob_expressions:
      patterns.extend(pattern.Interpolate(knowledge_base=self.knowledge_base))
    patterns.sort(key=len, reverse=True)

    file_finder_action = rdf_file_finder.FileFinderAction.Stat()
    request = rdf_file_finder.FileFinderArgs(
        paths=patterns,
        action=file_finder_action,
        follow_links=True,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY)
    action = file_finder.RegistryKeyFromClient

    yield action, request

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
        source.artifact_sources, parser_factory=None):
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
