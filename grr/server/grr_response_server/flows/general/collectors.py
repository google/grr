#!/usr/bin/env python
"""Flows for handling the collection for artifacts."""

import logging
from typing import Optional, Sequence, Text

from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.parsers import windows_persistence
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import compatibility
from grr_response_proto import flows_pb2
from grr_response_server import action_registry
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.flows.general import artifact_fallbacks
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import transfer

# For file collection artifacts. pylint: disable=unused-import
# pylint: enable=unused-import
_MAX_DEBUG_RESPONSES_STRING_LENGTH = 100000


def _ReadClientKnowledgeBase(client_id, allow_uninitialized=False):
  client = data_store.REL_DB.ReadClientSnapshot(client_id)
  return artifact.GetKnowledgeBase(
      client, allow_uninitialized=allow_uninitialized)


def _GetPathType(args: rdf_artifacts.ArtifactCollectorFlowArgs,
                 client_os: str) -> rdf_paths.PathSpec.PathType:
  if args.use_tsk or args.use_raw_filesystem_access:
    if client_os == "Windows":
      return config.CONFIG["Server.raw_filesystem_access_pathtype"]
    else:
      return rdf_paths.PathSpec.PathType.TSK
  else:
    return rdf_paths.PathSpec.PathType.OS


def _GetImplementationType(
    args: rdf_artifacts.ArtifactCollectorFlowArgs
) -> rdf_paths.PathSpec.ImplementationType:
  if args.HasField("implementation_type"):
    return args.implementation_type
  return None


class ArtifactCollectorFlow(flow_base.FlowBase):
  """Flow that takes a list of artifacts and collects them.

  This flow is the core of the Artifact implementation for GRR. Artifacts are
  defined using a standardized data format that includes what to collect and
  how to process the things collected. This flow takes that data driven format
  and makes it useful.

  The core functionality of Artifacts is split into ArtifactSources and
  Processors.

  An Artifact defines a set of ArtifactSources that are used to retrieve data
  from the client. These can specify collection of files, registry keys, command
  output and others. The first part of this flow "Collect" handles running those
  collections by issuing GRR flows and client actions.

  The results of those are then collected and GRR searches for Processors that
  know how to process the output of the ArtifactSources. The Processors all
  inherit from the Parser class, and each Parser specifies which Artifacts it
  knows how to process.

  So this flow hands off the collected rdfvalue results to the Processors which
  then return modified or different rdfvalues. These final results are then
  either:
  1. Sent to the calling flow.
  2. Written to a collection.
  """

  category = "/Collectors/"
  args_type = rdf_artifacts.ArtifactCollectorFlowArgs
  progress_type = rdf_artifacts.ArtifactCollectorFlowProgress
  result_types = (
      rdf_anomaly.Anomaly,
      rdf_client_action.ExecuteResponse,
      # ArtifactCollectorFlow has many more result types. For now, only result
      # types required for UI type generation are captured here, add other
      # types when needed.
      rdfvalue.RDFValue,
  )
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.state.artifacts_failed = []
    self.state.artifacts_skipped_due_to_condition = []
    self.state.called_fallbacks = set()
    self.state.failed_count = 0
    self.state.knowledge_base = self.args.knowledge_base
    self.state.response_count = 0
    self.state.progress = rdf_artifacts.ArtifactCollectorFlowProgress()

    if self.args.use_tsk and self.args.use_raw_filesystem_access:
      raise ValueError(
          "Only one of use_tsk and use_raw_filesystem_access can be set.")

    if (self.args.dependencies ==
        rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.FETCH_NOW):
      # String due to dependency loop with discover.py.
      self.CallFlow(
          "Interrogate", next_state=compatibility.GetName(self.StartCollection))
      return

    elif (self.args.dependencies
          == rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.USE_CACHED
         ) and (not self.state.knowledge_base):
      # If not provided, get a knowledge base from the client.
      try:
        self.state.knowledge_base = _ReadClientKnowledgeBase(self.client_id)
      except artifact_utils.KnowledgeBaseUninitializedError:
        # If no-one has ever initialized the knowledge base, we should do so
        # now.
        if not self._AreArtifactsKnowledgeBaseArtifacts():
          # String due to dependency loop with discover.py.
          self.CallFlow(
              "Interrogate",
              next_state=compatibility.GetName(self.StartCollection))
          return

    # In all other cases start the collection state.
    self.CallState(next_state=compatibility.GetName(self.StartCollection))

  def _GetArtifactFromName(self, name):
    """Gets an artifact from the registry, refreshing the registry if needed."""
    try:
      return artifact_registry.REGISTRY.GetArtifact(name)
    except rdf_artifacts.ArtifactNotRegisteredError:
      # If we don't have an artifact, things shouldn't have passed validation
      # so we assume it's a new one in the datastore.
      artifact_registry.REGISTRY.ReloadDatastoreArtifacts()
      return artifact_registry.REGISTRY.GetArtifact(name)

  def StartCollection(self, responses):
    """Start collecting."""
    if not responses.success:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "Attempt to initialize Knowledge Base failed.")

    if not self.state.knowledge_base:
      self.state.knowledge_base = _ReadClientKnowledgeBase(
          self.client_id, allow_uninitialized=True)

    for artifact_name in self.args.artifact_list:
      artifact_obj = self._GetArtifactFromName(artifact_name)

      # Ensure artifact has been written sanely. Note that this could be
      # removed if it turns out to be expensive. Artifact tests should catch
      # these.
      artifact_registry.Validate(artifact_obj)

      self.Collect(artifact_obj)

  def Collect(self, artifact_obj):
    """Collect the raw data from the client for this artifact."""
    artifact_name = artifact_obj.name

    # Ensure attempted artifacts are shown in progress, even with 0 results.
    self._GetOrInsertArtifactProgress(artifact_name)

    test_conditions = list(artifact_obj.conditions)
    os_conditions = ConvertSupportedOSToConditions(artifact_obj)
    if os_conditions:
      test_conditions.append(os_conditions)

    # Check each of the conditions match our target.
    for condition in test_conditions:
      if not artifact_utils.CheckCondition(condition,
                                           self.state.knowledge_base):
        logging.debug("Artifact %s condition %s failed on %s", artifact_name,
                      condition, self.client_id)
        self.state.artifacts_skipped_due_to_condition.append(
            (artifact_name, condition))
        return

    # Call the source defined action for each source.
    for source in artifact_obj.sources:
      # Check conditions on the source.
      source_conditions_met = True
      test_conditions = list(source.conditions)
      os_conditions = ConvertSupportedOSToConditions(source)
      if os_conditions:
        test_conditions.append(os_conditions)

      for condition in test_conditions:
        if not artifact_utils.CheckCondition(condition,
                                             self.state.knowledge_base):
          source_conditions_met = False

      if source_conditions_met:
        type_name = source.type
        source_type = rdf_artifacts.ArtifactSource.SourceType
        self.current_artifact_name = artifact_name
        if type_name == source_type.COMMAND:
          self.RunCommand(source)
        # TODO(hanuszczak): `DIRECTORY` is deprecated [1], it should be removed.
        #
        # [1]: https://github.com/ForensicArtifacts/artifacts/pull/475
        elif (type_name == source_type.DIRECTORY or
              type_name == source_type.PATH):
          self.Glob(source, _GetPathType(self.args, self.client_os),
                    _GetImplementationType(self.args))
        elif type_name == source_type.FILE:
          self.GetFiles(source, _GetPathType(self.args, self.client_os),
                        _GetImplementationType(self.args),
                        self.args.max_file_size)
        elif type_name == source_type.GREP:
          self.Grep(source, _GetPathType(self.args, self.client_os),
                    _GetImplementationType(self.args))
        elif type_name == source_type.REGISTRY_KEY:
          self.GetRegistryKey(source)
        elif type_name == source_type.REGISTRY_VALUE:
          self.GetRegistryValue(source)
        elif type_name == source_type.WMI:
          self.WMIQuery(source)
        elif type_name == source_type.REKALL_PLUGIN:
          raise NotImplementedError(
              "Running Rekall artifacts is not supported anymore.")
        elif type_name == source_type.ARTIFACT_GROUP:
          self.CollectArtifacts(source)
        elif type_name == source_type.ARTIFACT_FILES:
          self.CollectArtifactFiles(source)
        elif type_name == source_type.GRR_CLIENT_ACTION:
          self.RunGrrClientAction(source)
        else:
          raise RuntimeError("Invalid type %s in %s" %
                             (type_name, artifact_name))

      else:
        logging.debug(
            "Artifact %s no sources run due to all sources "
            "having failing conditions on %s", artifact_name, self.client_id)

  def _AreArtifactsKnowledgeBaseArtifacts(self):
    knowledgebase_list = config.CONFIG["Artifacts.knowledge_base"]
    for artifact_name in self.args.artifact_list:
      if artifact_name not in knowledgebase_list:
        return False
    return True

  def GetFiles(self, source, path_type, implementation_type, max_size):
    """Get a set of files."""
    new_path_list = []
    for path in source.attributes["paths"]:
      try:
        interpolated = artifact_utils.InterpolateKbAttributes(
            path, self.state.knowledge_base)
      except artifact_utils.KbInterpolationMissingAttributesError as error:
        logging.error(str(error))
        if not self.args.ignore_interpolation_errors:
          raise
        else:
          interpolated = []

      new_path_list.extend(interpolated)

    action = rdf_file_finder.FileFinderAction.Download(max_size=max_size)

    self.CallFlow(
        file_finder.FileFinder.__name__,
        paths=new_path_list,
        pathtype=path_type,
        implementation_type=implementation_type,
        action=action,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=compatibility.GetName(self.ProcessFileFinderResults))

  def ProcessFileFinderResults(self, responses):
    if not responses.success:
      self.Log("Failed to fetch files %s" %
               responses.request_data["artifact_name"])
    else:
      self.CallStateInline(
          next_state=compatibility.GetName(self.ProcessCollected),
          request_data=responses.request_data,
          messages=[r.stat_entry for r in responses])

  def Glob(self, source, pathtype, implementation_type):
    """Glob paths, return StatEntry objects."""
    self.CallFlow(
        filesystem.Glob.__name__,
        paths=self.InterpolateList(source.attributes.get("paths", [])),
        pathtype=pathtype,
        implementation_type=implementation_type,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=compatibility.GetName(self.ProcessCollected))

  def _CombineRegex(self, regex_list):
    if len(regex_list) == 1:
      return regex_list[0]

    regex_combined = b""
    for regex in regex_list:
      if regex_combined:
        regex_combined = b"%s|(%s)" % (regex_combined, regex)
      else:
        regex_combined = b"(%s)" % regex
    return regex_combined

  def Grep(self, source, pathtype, implementation_type):
    """Grep files in paths for any matches to content_regex_list.

    When multiple regexes are supplied, combine
    them into a single regex as an OR match so that we check all regexes at
    once.

    Args:
      source: artifact source
      pathtype: pathspec path typed
      implementation_type: Pathspec implementation type to use.
    """
    path_list = self.InterpolateList(source.attributes.get("paths", []))

    # `content_regex_list` elements should be binary strings, but forcing
    # artifact creators to use verbose YAML syntax for binary literals would
    # be cruel. Therefore, we allow both kind of strings and we convert to bytes
    # if required.
    content_regex_list = []
    for content_regex in source.attributes.get("content_regex_list", []):
      if isinstance(content_regex, Text):
        content_regex = content_regex.encode("utf-8")
      content_regex_list.append(content_regex)

    content_regex_list = self.InterpolateList(content_regex_list)

    regex_condition = rdf_file_finder.FileFinderContentsRegexMatchCondition(
        regex=self._CombineRegex(content_regex_list),
        bytes_before=0,
        bytes_after=0,
        mode="ALL_HITS")

    file_finder_condition = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=regex_condition)

    self.CallFlow(
        file_finder.FileFinder.__name__,
        paths=path_list,
        conditions=[file_finder_condition],
        action=rdf_file_finder.FileFinderAction(),
        pathtype=pathtype,
        implementation_type=implementation_type,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=compatibility.GetName(self.ProcessCollected))

  def GetRegistryKey(self, source):
    self.CallFlow(
        filesystem.Glob.__name__,
        paths=self.InterpolateList(source.attributes.get("keys", [])),
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=compatibility.GetName(self.ProcessCollected))

  def GetRegistryValue(self, source):
    """Retrieve directly specified registry values, returning Stat objects."""
    new_paths = set()
    has_glob = False
    for kvdict in source.attributes["key_value_pairs"]:
      if "*" in kvdict["key"] or rdf_paths.GROUPING_PATTERN.search(
          kvdict["key"]):
        has_glob = True

      if kvdict["value"]:
        # This currently only supports key value pairs specified using forward
        # slash.
        path = "\\".join((kvdict["key"], kvdict["value"]))
      else:
        # If value is not set, we want to get the default value. In
        # GRR this is done by specifying the key only, so this is what
        # we do here.
        path = kvdict["key"]

      try:
        expanded_paths = artifact_utils.InterpolateKbAttributes(
            path, self.state.knowledge_base)
      except artifact_utils.KbInterpolationMissingAttributesError as error:
        logging.error(str(error))
        if not self.args.ignore_interpolation_errors:
          raise
        else:
          expanded_paths = []
      new_paths.update(expanded_paths)

    if has_glob:
      self.CallFlow(
          filesystem.Glob.__name__,
          paths=new_paths,
          pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict()
          },
          next_state=compatibility.GetName(self.ProcessCollected))
    else:
      # We call statfile directly for keys that don't include globs because it
      # is faster and some artifacts rely on getting an IOError to trigger
      # fallback processing.
      for new_path in new_paths:
        pathspec = rdf_paths.PathSpec(
            path=new_path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

        # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
        # This conditional should be removed after that date.
        if not self.client_version or self.client_version >= 3221:
          stub = server_stubs.GetFileStat
          request = rdf_client_action.GetFileStatRequest(pathspec=pathspec)
        else:
          stub = server_stubs.StatFile
          request = rdf_client_action.ListDirRequest(pathspec=pathspec)

        self.CallClient(
            stub,
            request,
            request_data={
                "artifact_name": self.current_artifact_name,
                "source": source.ToPrimitiveDict()
            },
            next_state=compatibility.GetName(
                self.ProcessCollectedRegistryStatEntry))

  def _StartSubArtifactCollector(self, artifact_list, source, next_state):
    self.CallFlow(
        ArtifactCollectorFlow.__name__,
        artifact_list=artifact_list,
        use_raw_filesystem_access=(self.args.use_raw_filesystem_access or
                                   self.args.use_tsk),
        apply_parsers=self.args.apply_parsers,
        max_file_size=self.args.max_file_size,
        ignore_interpolation_errors=self.args.ignore_interpolation_errors,
        dependencies=self.args.dependencies,
        knowledge_base=self.args.knowledge_base,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=next_state)

  def CollectArtifacts(self, source):
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["names"],
        source=source,
        next_state=compatibility.GetName(self.ProcessCollected))

  def CollectArtifactFiles(self, source):
    """Collect files from artifact pathspecs."""
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["artifact_list"],
        source=source,
        next_state=compatibility.GetName(self.ProcessCollectedArtifactFiles))

  def RunCommand(self, source):
    """Run a command."""
    self.CallClient(
        server_stubs.ExecuteCommand,
        cmd=source.attributes["cmd"],
        args=source.attributes.get("args", []),
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=compatibility.GetName(self.ProcessCollected))

  def WMIQuery(self, source):
    """Run a Windows WMI Query."""
    query = source.attributes["query"]
    queries = self._Interpolate(query)
    base_object = source.attributes.get("base_object")
    for query in queries:
      self.CallClient(
          server_stubs.WmiQuery,
          query=query,
          base_object=base_object,
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict()
          },
          next_state=compatibility.GetName(self.ProcessCollected))

  def _GetSingleExpansion(self, value):
    results = list(self._Interpolate(value))
    if len(results) > 1:
      raise ValueError("Interpolation generated multiple results, use a"
                       " list for multi-value expansions. %s yielded: %s" %
                       (value, results))
    return results[0]

  def InterpolateDict(self, input_dict):
    """Interpolate all items from a dict.

    Args:
      input_dict: dict to interpolate

    Returns:
      original dict with all string values interpolated
    """
    new_args = {}
    for key, value in input_dict.items():
      if isinstance(value, Text) or isinstance(value, bytes):
        new_args[key] = self._GetSingleExpansion(value)
      elif isinstance(value, list):
        new_args[key] = self.InterpolateList(value)
      else:
        new_args[key] = value
    return new_args

  def InterpolateList(self, input_list):
    """Interpolate all items from a given source array.

    Args:
      input_list: list of values to interpolate

    Returns:
      original list of values extended with strings interpolated
    """
    new_args = []
    for value in input_list:
      if isinstance(value, Text) or isinstance(value, bytes):
        results = self._Interpolate(value)

        if not results and self.args.old_client_snapshot_fallback:
          client_id = self.client_id
          snapshots = data_store.REL_DB.ReadClientSnapshotHistory(client_id)

          for snapshot in snapshots:
            results = self._Interpolate(value, snapshot.knowledge_base)
            if results:
              break

        new_args.extend(results)
      else:
        new_args.extend(value)
    return new_args

  def _Interpolate(self,
                   pattern: Text,
                   knowledgebase: Optional[rdf_client.KnowledgeBase] = None)\
  -> Sequence[Text]:
    """Performs a knowledgebase interpolation.

    Args:
      pattern: A pattern to interpolate.
      knowledgebase: Knowledgebase to use for interpolation. If no knowledgebase
        is provided, the one provided as a flow argument is used.

    Returns:
      A list of possible interpolation results.
    """
    if knowledgebase is None:
      knowledgebase = self.state.knowledge_base

    try:
      return artifact_utils.InterpolateKbAttributes(pattern, knowledgebase)
    except artifact_utils.KbInterpolationMissingAttributesError as error:
      if self.args.old_client_snapshot_fallback:
        return []
      if self.args.ignore_interpolation_errors:
        logging.error(str(error))
        return []
      raise

  def RunGrrClientAction(self, source):
    """Call a GRR Client Action."""

    # Retrieve the correct rdfvalue to use for this client action.
    action_name = source.attributes["client_action"]
    try:
      action_stub = action_registry.ACTION_STUB_BY_ID[action_name]
    except KeyError:
      raise RuntimeError("Client action %s not found." % action_name)

    self.CallClient(
        action_stub,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=compatibility.GetName(self.ProcessCollected),
        **self.InterpolateDict(source.attributes.get("action_args", {})))

  def CallFallback(self, artifact_name, request_data):

    if artifact_name not in artifact_fallbacks.FALLBACK_REGISTRY:
      return False

    fallback_flow = artifact_fallbacks.FALLBACK_REGISTRY[artifact_name]

    if artifact_name in self.state.called_fallbacks:
      self.Log("Already called fallback class %s for artifact: %s",
               fallback_flow, artifact_name)
      return False

    self.Log("Calling fallback class %s for artifact: %s", fallback_flow,
             artifact_name)

    self.CallFlow(
        fallback_flow,
        request_data=request_data.ToDict(),
        artifact_name=artifact_name,
        next_state=compatibility.GetName(self.ProcessCollected))

    # Make sure we only try this once
    self.state.called_fallbacks.add(artifact_name)
    return True

  def ProcessCollected(self, responses):
    """Each individual collector will call back into here.

    Args:
      responses: Responses from the collection.

    Raises:
      artifact_utils.ArtifactDefinitionError: On bad definition.
      artifact_utils.ArtifactProcessingError: On failure to process.
    """
    flow_name = self.__class__.__name__
    artifact_name = str(responses.request_data["artifact_name"])
    source = responses.request_data.GetItem("source", None)

    if responses.success:
      self.Log(
          "Artifact data collection %s completed successfully in flow %s "
          "with %d responses", artifact_name, flow_name, len(responses))
    else:
      self.Log("Artifact %s data collection failed. Status: %s.", artifact_name,
               responses.status)

      # If the ArtifactDescriptor specifies a fallback for the failed Artifact,
      # call the fallback without processing any responses of the failed
      # artifact. If there is no fallback, process any responses that have been
      # received before the child ArtifactCollector failed.
      if self.CallFallback(artifact_name, responses.request_data):
        return

      self.state.failed_count += 1
      self.state.artifacts_failed.append(artifact_name)

    self._ParseResponses(list(responses), artifact_name, source)

  def ProcessCollectedRegistryStatEntry(self, responses):
    """Create AFF4 objects for registry statentries.

    We need to do this explicitly because we call StatFile client action
    directly for performance reasons rather than using one of the flows that do
    this step automatically.

    Args:
      responses: Response objects from the artifact source.
    """
    if not responses.success:
      self.CallStateInline(
          next_state=compatibility.GetName(self.ProcessCollected),
          responses=responses)
      return

    stat_entries = list(map(rdf_client_fs.StatEntry, responses))
    filesystem.WriteStatEntries(stat_entries, client_id=self.client_id)

    self.CallStateInline(
        next_state=compatibility.GetName(self.ProcessCollected),
        request_data=responses.request_data,
        messages=stat_entries)

  def ProcessCollectedArtifactFiles(self, responses):
    """Schedule files for download based on pathspec attribute.

    Args:
      responses: Response objects from the artifact source.

    Raises:
      RuntimeError: if pathspec value is not a PathSpec instance and not
                    a str.
    """
    self.download_list = []
    source = responses.request_data.GetItem("source")
    pathspec_attribute = source["attributes"].get("pathspec_attribute", None)

    for response in responses:
      if pathspec_attribute:
        if response.HasField(pathspec_attribute):
          pathspec = response.Get(pathspec_attribute)
        else:
          self.Log("Missing pathspec field %s: %s", pathspec_attribute,
                   response)
          continue
      else:
        pathspec = response

      # Check the default .pathspec attribute.
      if not isinstance(pathspec, rdf_paths.PathSpec):
        try:
          pathspec = response.pathspec
        except AttributeError:
          pass

      if isinstance(pathspec, Text):
        pathspec = rdf_paths.PathSpec(path=pathspec)
        if self.args.use_raw_filesystem_access or self.args.use_tsk:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.TSK
        else:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

      if isinstance(pathspec, rdf_paths.PathSpec):
        if not pathspec.path:
          self.Log("Skipping empty pathspec.")
          continue

        self.download_list.append(pathspec)

      else:
        raise RuntimeError(
            "Response must be a string path, a pathspec, or have "
            "pathspec_attribute set. Got: %s" % pathspec)

    if self.download_list:
      request_data = responses.request_data.ToDict()
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=self.download_list,
          request_data=request_data,
          next_state=compatibility.GetName(self.ProcessCollected))
    else:
      self.Log("No files to download")

  def _GetArtifactReturnTypes(self, source):
    """Get a list of types we expect to handle from our responses."""
    if source:
      return source["returned_types"]

  def _ParseResponses(self, responses, artifact_name, source):
    """Create a result parser sending different arguments for diff parsers.

    Args:
      responses: A list of responses.
      artifact_name: Name of the artifact that generated the responses.
      source: The source responsible for producing the responses.
    """
    artifact_return_types = self._GetArtifactReturnTypes(source)

    if self.args.apply_parsers:
      parser_factory = parsers.ArtifactParserFactory(artifact_name)
      results = artifact.ApplyParsersToResponses(parser_factory, responses,
                                                 self)
    else:
      results = responses

    # Increment artifact result count in flow progress.
    progress = self._GetOrInsertArtifactProgress(artifact_name)
    progress.num_results += len(results)

    for result in results:
      result_type = result.__class__.__name__
      if result_type == "Anomaly":
        self.SendReply(result)
      elif (not artifact_return_types or result_type in artifact_return_types):
        self.state.response_count += 1
        self.SendReply(result, tag="artifact:%s" % artifact_name)

  def GetProgress(self) -> rdf_artifacts.ArtifactCollectorFlowProgress:
    return self.state.progress

  def _GetOrInsertArtifactProgress(self,
                                   name: str) -> rdf_artifacts.ArtifactProgress:
    try:
      return next(a for a in self.state.progress.artifacts if a.name == name)
    except StopIteration:
      progress = rdf_artifacts.ArtifactProgress(name=name)
      self.state.progress.artifacts.append(progress)
      return progress

  def End(self, responses):
    del responses
    # If we got no responses, and user asked for it, we error out.
    if self.args.error_on_no_results and self.state.response_count == 0:
      raise artifact_utils.ArtifactProcessingError(
          "Artifact collector returned 0 responses.")


class ArtifactFilesDownloaderFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFilesDownloaderFlowArgs
  rdf_deps = [
      rdf_artifacts.ArtifactName,
      rdfvalue.ByteSize,
  ]


class ArtifactFilesDownloaderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFilesDownloaderResult
  rdf_deps = [
      rdf_paths.PathSpec,
      rdf_client_fs.StatEntry,
  ]

  def GetOriginalResultType(self):
    if self.HasField("original_result_type"):
      return rdfvalue.RDFValue.classes.get(self.original_result_type)


class ArtifactFilesDownloaderFlow(transfer.MultiGetFileLogic,
                                  flow_base.FlowBase):
  """Flow that downloads files referenced by collected artifacts."""

  category = "/Collectors/"
  args_type = ArtifactFilesDownloaderFlowArgs
  result_types = (ArtifactFilesDownloaderResult,)

  def _FindMatchingPathspecs(self, response):
    # If we're dealing with plain file StatEntry, just
    # return it's pathspec - there's nothing to parse
    # and guess.
    if (isinstance(response, rdf_client_fs.StatEntry) and
        response.pathspec.pathtype in [
            rdf_paths.PathSpec.PathType.TSK,
            rdf_paths.PathSpec.PathType.OS,
            rdf_paths.PathSpec.PathType.NTFS,
        ]):
      return [response.pathspec]

    knowledge_base = _ReadClientKnowledgeBase(self.client_id)

    if self.args.use_raw_filesystem_access or self.args.use_tsk:
      path_type = rdf_paths.PathSpec.PathType.TSK
    else:
      path_type = rdf_paths.PathSpec.PathType.OS

    p = windows_persistence.WindowsPersistenceMechanismsParser()
    parsed_items = p.ParseResponse(knowledge_base, response)
    parsed_pathspecs = [item.pathspec for item in parsed_items]

    for pathspec in parsed_pathspecs:
      pathspec.pathtype = path_type

    return parsed_pathspecs

  def Start(self):
    super().Start()

    if self.args.use_tsk and self.args.use_raw_filesystem_access:
      raise ValueError(
          "Only one of use_tsk and use_raw_filesystem_access can be set.")

    self.state.file_size = self.args.max_file_size
    self.state.results_to_download = []

    if self.args.HasField("implementation_type"):
      implementation_type = self.args.implementation_type
    else:
      implementation_type = None

    self.CallFlow(
        ArtifactCollectorFlow.__name__,
        next_state=compatibility.GetName(self._DownloadFiles),
        artifact_list=self.args.artifact_list,
        use_raw_filesystem_access=(self.args.use_tsk or
                                   self.args.use_raw_filesystem_access),
        implementation_type=implementation_type,
        max_file_size=self.args.max_file_size)

  def _DownloadFiles(self, responses):
    if not responses.success:
      self.Log("Failed to run ArtifactCollectorFlow: %s", responses.status)
      return

    results_with_pathspecs = []
    results_without_pathspecs = []
    for response in responses:
      pathspecs = self._FindMatchingPathspecs(response)
      if pathspecs:
        for pathspec in pathspecs:
          result = ArtifactFilesDownloaderResult(
              original_result_type=response.__class__.__name__,
              original_result=response,
              found_pathspec=pathspec)
          results_with_pathspecs.append(result)
      else:
        result = ArtifactFilesDownloaderResult(
            original_result_type=response.__class__.__name__,
            original_result=response)
        results_without_pathspecs.append(result)

    grouped_results = collection.Group(
        results_with_pathspecs, lambda x: x.found_pathspec.CollapsePath())
    for _, group in grouped_results.items():
      self.StartFileFetch(
          group[0].found_pathspec, request_data=dict(results=group))

    for result in results_without_pathspecs:
      self.SendReply(result)

  def ReceiveFetchedFile(self,
                         stat_entry,
                         file_hash,
                         request_data=None,
                         is_duplicate=False):
    """See MultiGetFileLogic."""
    del is_duplicate  # Unused.

    if not request_data:
      raise RuntimeError("Expected non-empty request_data")

    for result in request_data["results"]:
      result.downloaded_file = stat_entry
      self.SendReply(result)

  def FileFetchFailed(self, pathspec, request_data=None, status=None):
    """See MultiGetFileLogic."""
    if not request_data:
      raise RuntimeError("Expected non-empty request_data")

    for result in request_data["results"]:
      self.SendReply(result)


class ClientArtifactCollector(flow_base.FlowBase):
  """A client side artifact collector."""

  category = "/Collectors/"
  args_type = rdf_artifacts.ArtifactCollectorFlowArgs
  behaviours = flow_base.BEHAVIOUR_DEBUG

  def Start(self):
    """Issue the artifact collection request."""
    super().Start()

    self.state.knowledge_base = self.args.knowledge_base
    self.state.response_count = 0

    if not self.args.recollect_knowledge_base:
      dependency = rdf_artifacts.ArtifactCollectorFlowArgs.Dependency
      if self.args.dependencies == dependency.FETCH_NOW:
        # String due to dependency loop with discover.py.
        self.CallFlow(
            "Interrogate",
            next_state=compatibility.GetName(self.StartCollection))
        return

      if (self.args.dependencies == dependency.USE_CACHED and
          not self.state.knowledge_base):
        # If not provided, get a knowledge base from the client.
        try:
          self.state.knowledge_base = _ReadClientKnowledgeBase(self.client_id)
        except artifact_utils.KnowledgeBaseUninitializedError:
          # If no-one has ever initialized the knowledge base, we should do so
          # now.
          if not self._AreArtifactsKnowledgeBaseArtifacts():
            # String due to dependency loop with discover.py
            self.CallFlow(
                "Interrogate",
                next_state=compatibility.GetName(self.StartCollection))
            return

    # In all other cases start the collection state.
    self.CallStateInline(next_state=compatibility.GetName(self.StartCollection))

  def StartCollection(self, responses):
    """Start collecting."""
    if not responses.success:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "Attempt to initialize Knowledge Base failed.")

    # TODO(hanuszczak): Flow arguments also appear to have some knowledgebase.
    # Do we use it in any way?
    if not self.state.knowledge_base:
      self.state.knowledge_base = _ReadClientKnowledgeBase(
          self.client_id, allow_uninitialized=True)

    request = GetArtifactCollectorArgs(self.args, self.state.knowledge_base)
    self.CollectArtifacts(request)

  def _AreArtifactsKnowledgeBaseArtifacts(self):
    knowledgebase_list = config.CONFIG["Artifacts.knowledge_base"]
    for artifact_name in self.args.artifact_list:
      if artifact_name not in knowledgebase_list:
        return False
    return True

  def CollectArtifacts(self, client_artifact_collector_args):
    """Start the client side artifact collection."""
    self.CallClient(
        server_stubs.ArtifactCollector,
        request=client_artifact_collector_args,
        next_state=compatibility.GetName(self.ProcessCollected))

  def ProcessCollected(self, responses):
    flow_name = self.__class__.__name__
    if responses.success:
      self.Log(
          "Artifact data collection completed successfully in flow %s "
          "with %d responses", flow_name, len(responses))
    else:
      self.Log("Artifact data collection failed. Status: %s.", responses.status)
      return

    for response in responses:
      # The ClientArtifactCollector returns a `ClientArtifactCollectorResult`
      # (an rdf object that contains a knowledge base and the list of collected
      # artifacts, each collected artifact has a name and a list of responses).
      # In order to conform to the normal Artifact Collector we just iterate
      # through and return the responses.
      for collected_artifact in response.collected_artifacts:
        for res in collected_artifact.action_results:
          self.SendReply(res.value)
      self.state.response_count += 1

  def End(self, responses):
    super().End(responses)

    # If we got no responses, and user asked for it, we error out.
    if self.args.error_on_no_results and self.state.response_count == 0:
      raise artifact_utils.ArtifactProcessingError(
          "Artifact collector returned 0 responses.")


def ConvertSupportedOSToConditions(src_object):
  """Turn supported_os into a condition."""
  if src_object.supported_os:
    conditions = " OR ".join("os == '%s'" % o for o in src_object.supported_os)
    return conditions


def GetArtifactCollectorArgs(flow_args, knowledge_base):
  """Prepare bundle of artifacts and their dependencies for the client.

  Args:
    flow_args: An `ArtifactCollectorFlowArgs` instance.
    knowledge_base: contains information about the client

  Returns:
    rdf value object containing a list of extended artifacts and the
    knowledge base
  """
  args = rdf_artifacts.ClientArtifactCollectorArgs()
  args.knowledge_base = knowledge_base

  args.apply_parsers = flow_args.apply_parsers
  args.ignore_interpolation_errors = flow_args.ignore_interpolation_errors
  args.max_file_size = flow_args.max_file_size

  if not flow_args.recollect_knowledge_base:
    artifact_names = flow_args.artifact_list
  else:
    artifact_names = GetArtifactsForCollection(knowledge_base.os,
                                               flow_args.artifact_list)

  expander = ArtifactExpander(knowledge_base,
                              _GetPathType(flow_args, knowledge_base.os),
                              flow_args.max_file_size)
  for artifact_name in artifact_names:
    rdf_artifact = artifact_registry.REGISTRY.GetArtifact(artifact_name)
    if not MeetsConditions(knowledge_base, rdf_artifact):
      continue
    if artifact_name in expander.processed_artifacts:
      continue
    requested_by_user = artifact_name in flow_args.artifact_list
    for expanded_artifact in expander.Expand(rdf_artifact, requested_by_user):
      args.artifacts.append(expanded_artifact)
  return args


def MeetsConditions(knowledge_base, source):
  """Check conditions on the source."""
  source_conditions_met = True
  os_conditions = ConvertSupportedOSToConditions(source)
  if os_conditions:
    source.conditions.append(os_conditions)
  for condition in source.conditions:
    source_conditions_met &= artifact_utils.CheckCondition(
        condition, knowledge_base)

  return source_conditions_met


class ArtifactExpander(object):
  """Expands a given artifact and keeps track of processed artifacts."""

  def __init__(self, knowledge_base, path_type, max_file_size):
    self._knowledge_base = knowledge_base
    self._path_type = path_type
    self._max_file_size = max_file_size
    self.processed_artifacts = set()

  def Expand(self, rdf_artifact, requested):
    """Expand artifact by extending its sources.

    This method takes as input an rdf artifact object and returns a rdf expanded
    artifact. It iterates through the list of sources processing them by type.
    Each source of the original artifact can lead to one or more (in case of
    artifact groups and files where the sub artifacts are expanded recursively)
    sources in the expanded artifact. The list of sources of the expanded
    artifact is extended at the end of each iteration.

    The parameter `requested` is passed down at the recursive calls. So, if an
    artifact group is requested by the user, every artifact/source belonging to
    this group will be treated as requested by the user. The same applies to
    artifact files.

    Args:
      rdf_artifact: artifact object to expand (obtained from the registry)
      requested: Whether the artifact is requested by the user or scheduled for
        collection as a KnowledgeBase dependency.

    Yields:
      rdf value representation of expanded artifact containing the name of the
      artifact and the expanded sources
    """

    source_type = rdf_artifacts.ArtifactSource.SourceType

    expanded_artifact = rdf_artifacts.ExpandedArtifact(
        name=rdf_artifact.name,
        provides=rdf_artifact.provides,
        requested_by_user=requested)

    for source in rdf_artifact.sources:
      if MeetsConditions(self._knowledge_base, source):
        type_name = source.type

        if type_name == source_type.ARTIFACT_GROUP:
          for subartifact in self._ExpandArtifactGroupSource(source, requested):
            yield subartifact
          continue

        elif type_name == source_type.ARTIFACT_FILES:
          expanded_sources = self._ExpandArtifactFilesSource(source, requested)

        else:
          expanded_sources = self._ExpandBasicSource(source)

        expanded_artifact.sources.Extend(expanded_sources)
    self.processed_artifacts.add(rdf_artifact.name)
    if expanded_artifact.sources:
      yield expanded_artifact

  def _ExpandBasicSource(self, source):
    expanded_source = rdf_artifacts.ExpandedSource(
        base_source=source,
        path_type=self._path_type,
        max_bytesize=self._max_file_size)
    return [expanded_source]

  def _ExpandArtifactGroupSource(self, source, requested):
    """Recursively expands an artifact group source."""
    artifact_list = []
    if "names" in source.attributes:
      artifact_list = source.attributes["names"]
    for artifact_name in artifact_list:
      if artifact_name in self.processed_artifacts:
        continue
      artifact_obj = artifact_registry.REGISTRY.GetArtifact(artifact_name)
      for expanded_artifact in self.Expand(artifact_obj, requested):
        yield expanded_artifact

  def _ExpandArtifactFilesSource(self, source, requested):
    """Recursively expands an artifact files source."""
    expanded_source = rdf_artifacts.ExpandedSource(base_source=source)
    sub_sources = []
    artifact_list = []
    if "artifact_list" in source.attributes:
      artifact_list = source.attributes["artifact_list"]
    for artifact_name in artifact_list:
      if artifact_name in self.processed_artifacts:
        continue
      artifact_obj = artifact_registry.REGISTRY.GetArtifact(artifact_name)
      for expanded_artifact in self.Expand(artifact_obj, requested):
        sub_sources.extend(expanded_artifact.sources)
    expanded_source.artifact_sources = sub_sources
    expanded_source.path_type = self._path_type
    return [expanded_source]


def GetArtifactsForCollection(os_name, artifact_list):
  """Wrapper for the ArtifactArranger.

  Extend the artifact list by dependencies and sort the artifacts to resolve the
  dependencies.

  Args:
    os_name: String specifying the OS name.
    artifact_list: List of requested artifact names.

  Returns:
    A list of artifacts such that if they are collected in the given order
      their dependencies are resolved.
  """
  artifact_arranger = ArtifactArranger(os_name, artifact_list)
  artifact_names = artifact_arranger.GetArtifactsInProperOrder()
  return artifact_names


class ArtifactArranger(object):
  """Resolves dependencies and gives an ordered list of artifacts to collect."""

  def __init__(self, os_name, artifacts_name_list):
    self.reachable_nodes = set()
    self.graph = {}
    self._InitializeGraph(os_name, artifacts_name_list)

  class Node(object):

    def __init__(self, is_artifact):
      self.is_artifact = is_artifact
      self.is_provided = False
      self.outgoing = []
      self.incoming = []

  def _InitializeGraph(self, os_name, artifact_list):
    """Creates the nodes and directed edges of the dependency graph.

    Args:
      os_name: String specifying the OS name.
      artifact_list: List of requested artifact names.
    """
    dependencies = artifact_registry.REGISTRY.SearchDependencies(
        os_name, artifact_list)
    artifact_names, attribute_names = dependencies

    self._AddAttributeNodes(attribute_names)
    self._AddArtifactNodesAndEdges(artifact_names)

  def _AddAttributeNodes(self, attribute_names):
    """Add the attribute nodes to the graph.

    For every attribute that is required for the collection of requested
    artifacts, add a node to the dependency graph. An attribute node will have
    incoming edges from the artifacts that provide this attribute and outgoing
    edges to the artifacts that depend on it.

    An attribute is reachable as soon as one artifact that provides it is
    reachable. Initially, no attribute node is reachable.

    Args:
      attribute_names: List of required attribute names.
    """
    for attribute_name in attribute_names:
      self.graph[attribute_name] = self.Node(is_artifact=False)

  def _AddArtifactNodesAndEdges(self, artifact_names):
    """Add the artifact nodes to the graph.

    For every artifact that has to be collected, add a node to the dependency
    graph.

    The edges represent the dependencies. An artifact has outgoing edges to the
    attributes it provides and incoming edges from attributes it depends on.
    Initially, only artifacts without incoming edges are reachable. An artifact
    becomes reachable if all of its dependencies are reachable.

    Args:
      artifact_names: List of names of the artifacts to collect.
    """
    for artifact_name in artifact_names:
      self.graph[artifact_name] = self.Node(is_artifact=True)
      rdf_artifact = artifact_registry.REGISTRY.GetArtifact(artifact_name)
      self._AddDependencyEdges(rdf_artifact)
      self._AddProvidesEdges(rdf_artifact)

  def _AddDependencyEdges(self, rdf_artifact):
    """Add an edge for every dependency of the given artifact.

    This method gets the attribute names for a given artifact and for every
    attribute it adds a directed edge from the attribute node to the artifact
    node. If an artifact does not have any dependencies it is added to the set
    of reachable nodes.

    Args:
      rdf_artifact: The artifact object.
    """
    artifact_dependencies = artifact_registry.GetArtifactPathDependencies(
        rdf_artifact)
    if artifact_dependencies:
      for attribute in artifact_dependencies:
        self._AddEdge(attribute, rdf_artifact.name)
    else:
      self.reachable_nodes.add(rdf_artifact.name)
      self.graph[rdf_artifact.name].is_provided = True

  def _AddProvidesEdges(self, rdf_artifact):
    """Add an edge for every attribute the given artifact provides.

    This method adds a directed edge from the artifact node to every attribute
    this artifact provides.

    Args:
      rdf_artifact: The artifact object.
    """
    for attribute in rdf_artifact.provides:
      self._AddEdge(rdf_artifact.name, attribute)

  def _AddEdge(self, start_node, end_node):
    """Add a directed edge to the graph.

    Add the end to the list of outgoing nodes of the start and the start to the
    list of incoming nodes of the end node.

    Args:
      start_node: name of the start node
      end_node: name of the end node
    """

    self.graph[start_node].outgoing.append(end_node)

    # This check is necessary because an artifact can provide attributes that
    # are not covered by the graph because they are not relevant for the
    # requested artifacts.
    if end_node in self.graph:
      self.graph[end_node].incoming.append(start_node)

  def GetArtifactsInProperOrder(self):
    """Bring the artifacts in a linear order that resolves dependencies.

    This method obtains a linear ordering of the nodes and then returns the list
    of artifact names.

    Returns:
      A list of `ArtifactName` instances such that if they are collected in the
      given order their dependencies are resolved.
    """
    artifact_list = []
    while self.reachable_nodes:
      node_name = self.reachable_nodes.pop()
      node = self.graph[node_name]
      if node.is_artifact:
        artifact_list.append(node_name)
      for next_node_name in node.outgoing:
        if next_node_name not in self.graph:
          continue
        next_node = self.graph[next_node_name]
        if next_node.is_provided:
          continue
        next_node.incoming.remove(node_name)
        if not (next_node.is_artifact and next_node.incoming):
          next_node.is_provided = True
          self.reachable_nodes.add(next_node_name)
    return artifact_list
