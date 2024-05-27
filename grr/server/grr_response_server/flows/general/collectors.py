#!/usr/bin/env python
"""Flows for handling the collection for artifacts."""

import logging
from typing import Optional, Sequence, Text

from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_core.path_detection import windows as path_detection_windows
from grr_response_proto import flows_pb2
from grr_response_server import action_registry
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import mig_objects

# For file collection artifacts. pylint: disable=unused-import
# pylint: enable=unused-import
_MAX_DEBUG_RESPONSES_STRING_LENGTH = 100000


def _ReadClientKnowledgeBase(client_id, allow_uninitialized=False):
  client = data_store.REL_DB.ReadClientSnapshot(client_id)
  if client is not None:
    client = mig_objects.ToRDFClientSnapshot(client)
  return artifact.GetKnowledgeBase(
      client, allow_uninitialized=allow_uninitialized
  )


def _GetPathType(
    args: rdf_artifacts.ArtifactCollectorFlowArgs, client_os: str
) -> rdf_paths.PathSpec.PathType:
  if args.use_raw_filesystem_access:
    if client_os == "Windows":
      return config.CONFIG["Server.raw_filesystem_access_pathtype"]
    else:
      return rdf_paths.PathSpec.PathType.TSK
  else:
    return rdf_paths.PathSpec.PathType.OS


def _GetImplementationType(
    args: rdf_artifacts.ArtifactCollectorFlowArgs,
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
    self.state.failed_count = 0
    self.state.knowledge_base = self.args.knowledge_base
    self.state.response_count = 0
    self.state.progress = rdf_artifacts.ArtifactCollectorFlowProgress()

    if (
        self.args.dependencies
        == rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.FETCH_NOW
    ):
      # String due to dependency loop with discover.py.
      self.CallFlow("Interrogate", next_state=self.StartCollection.__name__)
      return

    elif (
        self.args.dependencies
        == rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.USE_CACHED
    ) and (not self.state.knowledge_base):
      # If not provided, get a knowledge base from the client.
      try:
        self.state.knowledge_base = _ReadClientKnowledgeBase(self.client_id)
      except artifact_utils.KnowledgeBaseUninitializedError:
        # If no-one has ever initialized the knowledge base, we should do so
        # now.
        # String due to dependency loop with discover.py.
        self.CallFlow("Interrogate", next_state=self.StartCollection.__name__)
        return

    # In all other cases start the collection state.
    self.CallState(next_state=self.StartCollection.__name__)

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
          "Attempt to initialize Knowledge Base failed."
      )

    if not self.state.knowledge_base:
      self.state.knowledge_base = _ReadClientKnowledgeBase(
          self.client_id, allow_uninitialized=True
      )

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

    if not MeetsOSConditions(self.state.knowledge_base, artifact_obj):
      logging.debug(
          "%s: Artifact %s not supported on os %s (options %s)",
          self.client_id,
          artifact_name,
          self.state.knowledge_base.os,
          artifact_obj.supported_os,
      )
      self.state.artifacts_skipped_due_to_condition.append(
          (artifact_name, "OS")
      )
      return

    sources_ran = 0
    # Call the source defined action for each source.
    for source in artifact_obj.sources:
      if not MeetsOSConditions(self.state.knowledge_base, source):
        continue

      sources_ran += 1

      type_name = source.type
      source_type = rdf_artifacts.ArtifactSource.SourceType
      self.current_artifact_name = artifact_name
      if type_name == source_type.COMMAND:
        self.RunCommand(source)
      elif type_name == source_type.PATH:
        self.GetPaths(
            source,
            _GetPathType(self.args, self.client_os),
            _GetImplementationType(self.args),
            rdf_file_finder.FileFinderAction.Stat(),
        )
      elif type_name == source_type.FILE:
        self.GetPaths(
            source,
            _GetPathType(self.args, self.client_os),
            _GetImplementationType(self.args),
            rdf_file_finder.FileFinderAction.Download(
                max_size=self.args.max_file_size
            ),
        )
      elif type_name == source_type.GREP:
        self.Grep(
            source,
            _GetPathType(self.args, self.client_os),
            _GetImplementationType(self.args),
        )
      elif type_name == source_type.REGISTRY_KEY:
        self.GetRegistryKey(source)
      elif type_name == source_type.REGISTRY_VALUE:
        self.GetRegistryValue(source)
      elif type_name == source_type.WMI:
        self.WMIQuery(source)
      elif type_name == source_type.REKALL_PLUGIN:
        raise NotImplementedError(
            "Running Rekall artifacts is not supported anymore."
        )
      elif type_name == source_type.ARTIFACT_GROUP:
        self.CollectArtifacts(source)
      elif type_name == source_type.ARTIFACT_FILES:
        self.CollectArtifactFiles(source)
      elif type_name == source_type.GRR_CLIENT_ACTION:
        self.RunGrrClientAction(source)
      else:
        raise RuntimeError("Invalid type %s in %s" % (type_name, artifact_name))

    if sources_ran == 0:
      logging.debug(
          "Artifact %s no sources run due to all sources "
          "having failing conditions on %s",
          artifact_name,
          self.client_id,
      )

  def GetPaths(self, source, path_type, implementation_type, action):
    """Get a set of files."""
    file_finder_cls = file_finder.ClientFileFinder
    if config.CONFIG["Server.internal_artifactcollector_use_legacy_filefinder"]:
      file_finder_cls = file_finder.FileFinder
    self.CallFlow(
        file_finder_cls.__name__,
        paths=self.InterpolateList(source.attributes.get("paths", [])),
        pathtype=path_type,
        implementation_type=implementation_type,
        action=action,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessFileFinderResults.__name__,
    )

  def ProcessFileFinderResults(self, responses):
    if not responses.success:
      self.Log(
          "Failed to fetch files %s" % responses.request_data["artifact_name"]
      )
    else:
      self.CallStateInline(
          next_state=self.ProcessCollected.__name__,
          request_data=responses.request_data,
          messages=[r.stat_entry for r in responses],
      )

  def Glob(self, source, pathtype, implementation_type):
    """Glob paths, return StatEntry objects."""
    self.CallFlow(
        filesystem.Glob.__name__,
        paths=self.InterpolateList(source.attributes.get("paths", [])),
        pathtype=pathtype,
        implementation_type=implementation_type,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessCollected.__name__,
    )

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
        mode="ALL_HITS",
    )

    file_finder_condition = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
        ),
        contents_regex_match=regex_condition,
    )

    self.CallFlow(
        file_finder.FileFinder.__name__,
        paths=path_list,
        conditions=[file_finder_condition],
        action=rdf_file_finder.FileFinderAction(),
        pathtype=pathtype,
        implementation_type=implementation_type,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessCollected.__name__,
    )

  def GetRegistryKey(self, source):
    self.CallFlow(
        filesystem.Glob.__name__,
        paths=self.InterpolateList(source.attributes.get("keys", [])),
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessCollected.__name__,
    )

  def GetRegistryValue(self, source):
    """Retrieve directly specified registry values, returning Stat objects."""
    new_paths = set()
    has_glob = False
    for kvdict in source.attributes["key_value_pairs"]:
      if "*" in kvdict["key"] or rdf_paths.GROUPING_PATTERN.search(
          kvdict["key"]
      ):
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

      expanded_paths = []
      try:
        expanded_paths = artifact_utils.InterpolateKbAttributes(
            path, mig_client.ToProtoKnowledgeBase(self.state.knowledge_base)
        )
      except artifact_utils.KbInterpolationMissingAttributesError as error:
        logging.error(str(error))
        if not self.args.ignore_interpolation_errors:
          raise

      new_paths.update(expanded_paths)

    if has_glob:
      self.CallFlow(
          filesystem.Glob.__name__,
          paths=new_paths,
          pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict(),
          },
          next_state=self.ProcessCollected.__name__,
      )
    else:
      # We call statfile directly for keys that don't include globs because it
      # is faster and some artifacts rely on getting an IOError to trigger
      # fallback processing.
      for new_path in new_paths:
        pathspec = rdf_paths.PathSpec(
            path=new_path, pathtype=rdf_paths.PathSpec.PathType.REGISTRY
        )

        self.CallClient(
            server_stubs.GetFileStat,
            rdf_client_action.GetFileStatRequest(pathspec=pathspec),
            request_data={
                "artifact_name": self.current_artifact_name,
                "source": source.ToPrimitiveDict(),
            },
            next_state=self.ProcessCollectedRegistryStatEntry.__name__,
        )

  def _StartSubArtifactCollector(self, artifact_list, source, next_state):
    self.CallFlow(
        ArtifactCollectorFlow.__name__,
        artifact_list=artifact_list,
        use_raw_filesystem_access=self.args.use_raw_filesystem_access,
        apply_parsers=self.args.apply_parsers,
        implementation_type=self.args.implementation_type,
        max_file_size=self.args.max_file_size,
        ignore_interpolation_errors=self.args.ignore_interpolation_errors,
        dependencies=self.args.dependencies,
        knowledge_base=self.args.knowledge_base,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=next_state,
    )

  def CollectArtifacts(self, source):
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["names"],
        source=source,
        next_state=self.ProcessCollected.__name__,
    )

  def CollectArtifactFiles(self, source):
    """Collect files from artifact pathspecs."""
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["artifact_list"],
        source=source,
        next_state=self.ProcessCollectedArtifactFiles.__name__,
    )

  def RunCommand(self, source):
    """Run a command."""
    self.CallClient(
        server_stubs.ExecuteCommand,
        cmd=source.attributes["cmd"],
        args=source.attributes.get("args", []),
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessCollected.__name__,
    )

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
              "source": source.ToPrimitiveDict(),
          },
          next_state=self.ProcessCollected.__name__,
      )

  def _GetSingleExpansion(self, value):
    results = list(self._Interpolate(value))
    if len(results) > 1:
      raise ValueError(
          "Interpolation generated multiple results, use a"
          " list for multi-value expansions. %s yielded: %s" % (value, results)
      )
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
            results = self._Interpolate(
                value, mig_client.ToRDFKnowledgeBase(snapshot.knowledge_base)
            )
            if results:
              break

        new_args.extend(results)
      else:
        new_args.extend(value)
    return new_args

  def _Interpolate(
      self,
      pattern: Text,
      knowledgebase: Optional[rdf_client.KnowledgeBase] = None,
  ) -> Sequence[Text]:
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
      return artifact_utils.InterpolateKbAttributes(
          pattern, mig_client.ToProtoKnowledgeBase(knowledgebase)
      )
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
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessCollected.__name__,
        **self.InterpolateDict(source.attributes.get("action_args", {})),
    )

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
          "with %d responses",
          artifact_name,
          flow_name,
          len(responses),
      )
    else:
      self.Log(
          "Artifact %s data collection failed. Status: %s.",
          artifact_name,
          responses.status,
      )

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
          next_state=self.ProcessCollected.__name__, responses=responses
      )
      return

    stat_entries = list(map(rdf_client_fs.StatEntry, responses))
    filesystem.WriteStatEntries(stat_entries, client_id=self.client_id)

    self.CallStateInline(
        next_state=self.ProcessCollected.__name__,
        request_data=responses.request_data,
        messages=stat_entries,
    )

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
          self.Log(
              "Missing pathspec field %s: %s", pathspec_attribute, response
          )
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

      if isinstance(pathspec, rdf_paths.PathSpec):
        if not pathspec.path:
          self.Log("Skipping empty pathspec.")
          continue
        if self.args.use_raw_filesystem_access:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.TSK
        else:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

        self.download_list.append(pathspec)

      else:
        raise RuntimeError(
            "Response must be a string path, a pathspec, or have "
            "pathspec_attribute set. Got: %s" % pathspec
        )

    if self.download_list:
      request_data = responses.request_data.ToDict()
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=self.download_list,
          request_data=request_data,
          next_state=self.ProcessCollected.__name__,
      )
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
      results = artifact.ApplyParsersToResponses(
          parser_factory, responses, self
      )
    else:
      results = responses

    # Increment artifact result count in flow progress.
    progress = self._GetOrInsertArtifactProgress(artifact_name)
    progress.num_results += len(results)

    for result in results:
      result_type = result.__class__.__name__
      if result_type == "Anomaly":
        self.SendReply(result)
      elif not artifact_return_types or result_type in artifact_return_types:
        self.state.response_count += 1
        self.SendReply(result, tag="artifact:%s" % artifact_name)

  def GetProgress(self) -> rdf_artifacts.ArtifactCollectorFlowProgress:
    if hasattr(self.state, "progress"):
      return self.state.progress
    return rdf_artifacts.ArtifactCollectorFlowProgress()

  def _GetOrInsertArtifactProgress(
      self, name: str
  ) -> rdf_artifacts.ArtifactProgress:
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
          "Artifact collector returned 0 responses."
      )


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


class ArtifactFilesDownloaderFlow(
    transfer.MultiGetFileLogic, flow_base.FlowBase
):
  """Flow that downloads files referenced by collected artifacts."""

  category = "/Collectors/"
  args_type = ArtifactFilesDownloaderFlowArgs
  result_types = (ArtifactFilesDownloaderResult,)

  def _FindMatchingPathspecs(self, response):
    # If we're dealing with plain file StatEntry, just
    # return it's pathspec - there's nothing to parse
    # and guess.
    if isinstance(response, rdf_client_fs.StatEntry):
      if response.pathspec.pathtype in [
          rdf_paths.PathSpec.PathType.TSK,
          rdf_paths.PathSpec.PathType.OS,
          rdf_paths.PathSpec.PathType.NTFS,
      ]:
        yield response.pathspec

      if response.pathspec.pathtype in [
          rdf_paths.PathSpec.PathType.REGISTRY,
      ]:
        knowledge_base = _ReadClientKnowledgeBase(self.client_id)

        if self.args.use_raw_filesystem_access:
          path_type = rdf_paths.PathSpec.PathType.TSK
        else:
          path_type = rdf_paths.PathSpec.PathType.OS

        for path in path_detection_windows.DetectExecutablePaths(
            [response.registry_data.string],
            artifact_utils.GetWindowsEnvironmentVariablesMap(knowledge_base),
        ):
          yield rdf_paths.PathSpec(path=path, pathtype=path_type)

  def Start(self):
    super().Start()

    self.state.file_size = self.args.max_file_size
    self.state.results_to_download = []

    if self.args.HasField("implementation_type"):
      implementation_type = self.args.implementation_type
    else:
      implementation_type = None

    self.CallFlow(
        ArtifactCollectorFlow.__name__,
        next_state=self._DownloadFiles.__name__,
        artifact_list=self.args.artifact_list,
        use_raw_filesystem_access=self.args.use_raw_filesystem_access,
        implementation_type=implementation_type,
        max_file_size=self.args.max_file_size,
    )

  def _DownloadFiles(self, responses):
    if not responses.success:
      self.Log("Failed to run ArtifactCollectorFlow: %s", responses.status)
      return

    results_with_pathspecs = []
    results_without_pathspecs = []
    for response in responses:
      pathspecs = list(self._FindMatchingPathspecs(response))
      if pathspecs:
        for pathspec in pathspecs:
          result = ArtifactFilesDownloaderResult(
              original_result_type=response.__class__.__name__,
              original_result=response,
              found_pathspec=pathspec,
          )
          results_with_pathspecs.append(result)
      else:
        result = ArtifactFilesDownloaderResult(
            original_result_type=response.__class__.__name__,
            original_result=response,
        )
        results_without_pathspecs.append(result)

    grouped_results = collection.Group(
        results_with_pathspecs, lambda x: x.found_pathspec.CollapsePath()
    )
    for _, group in grouped_results.items():
      self.StartFileFetch(
          group[0].found_pathspec, request_data=dict(results=group)
      )

    for result in results_without_pathspecs:
      self.SendReply(result)

  def ReceiveFetchedFile(
      self, stat_entry, file_hash, request_data=None, is_duplicate=False
  ):
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


def MeetsOSConditions(knowledge_base, source):
  """Check supported OS on the source."""
  if source.supported_os and knowledge_base.os not in source.supported_os:
    return False

  return True
