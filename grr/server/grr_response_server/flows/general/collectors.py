#!/usr/bin/env python
"""Flows for handling the collection for artifacts."""

import logging
from grr import config

from grr.lib import parser
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr.lib.rdfvalues import structs as rdf_structs
# For file collection artifacts. pylint: disable=unused-import
from grr_response_proto import flows_pb2
# pylint: enable=unused-import
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import artifact
# For various parsers use by artifacts. pylint: disable=unused-import
from grr.server.grr_response_server import artifact_registry
# pylint: enable=unused-import
from grr.server.grr_response_server import artifact_utils
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import sequential_collection
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.flows.general import file_finder
from grr.server.grr_response_server.flows.general import filesystem
from grr.server.grr_response_server.flows.general import memory
from grr.server.grr_response_server.flows.general import transfer
# For file collection artifacts. pylint: disable=unused-import
from grr.server.grr_response_server.parsers import registry_init
# pylint: enable=unused-import
from grr.server.grr_response_server.parsers import windows_persistence


class ArtifactCollectorFlow(flow.GRRFlow):
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
  args_type = artifact_utils.ArtifactCollectorFlowArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def GetPathType(self):
    if self.args.use_tsk:
      return paths.PathSpec.PathType.TSK
    return paths.PathSpec.PathType.OS

  @flow.StateHandler()
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.state.artifacts_failed = []
    self.state.artifacts_skipped_due_to_condition = []
    self.state.called_fallbacks = set()
    self.state.failed_count = 0
    self.state.knowledge_base = self.args.knowledge_base
    self.state.response_count = 0

    if (self.args.dependencies ==
        artifact_utils.ArtifactCollectorFlowArgs.Dependency.FETCH_NOW):
      # String due to dependency loop with discover.py.
      self.CallFlow("Interrogate", next_state="StartCollection")
      return

    elif (self.args.dependencies == artifact_utils.ArtifactCollectorFlowArgs.
          Dependency.USE_CACHED) and (not self.state.knowledge_base):
      # If not provided, get a knowledge base from the client.
      try:
        self.state.knowledge_base = artifact.GetArtifactKnowledgeBase(
            self.client)
      except artifact_utils.KnowledgeBaseUninitializedError:
        # If no-one has ever initialized the knowledge base, we should do so
        # now.
        if not self._AreArtifactsKnowledgeBaseArtifacts():
          # String due to dependency loop with discover.py.
          self.CallFlow("Interrogate", next_state="StartCollection")
          return

    # In all other cases start the collection state.
    self.CallState(next_state="StartCollection")

  @flow.StateHandler()
  def StartCollection(self, responses):
    """Start collecting."""
    if not responses.success:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "Attempt to initialize Knowledge Base failed.")

    if not self.state.knowledge_base:
      self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
      # If we are processing the knowledge base, it still won't exist yet.
      self.state.knowledge_base = artifact.GetArtifactKnowledgeBase(
          self.client, allow_uninitialized=True)

    for artifact_name in self.args.artifact_list:
      artifact_obj = self._GetArtifactFromName(artifact_name)

      # Ensure artifact has been written sanely. Note that this could be
      # removed if it turns out to be expensive. Artifact tests should catch
      # these.
      artifact_obj.Validate()

      self.Collect(artifact_obj)

  def ConvertSupportedOSToConditions(self, src_object, filter_list):
    """Turn supported_os into a condition."""
    if src_object.supported_os:
      filter_str = " OR ".join(
          "os == '%s'" % o for o in src_object.supported_os)
      return filter_list.append(filter_str)

  def Collect(self, artifact_obj):
    """Collect the raw data from the client for this artifact."""
    artifact_name = artifact_obj.name

    test_conditions = list(artifact_obj.conditions)
    self.ConvertSupportedOSToConditions(artifact_obj, test_conditions)

    # Check each of the conditions match our target.
    for condition in test_conditions:
      if not artifact_utils.CheckCondition(condition,
                                           self.state.knowledge_base):
        logging.debug("Artifact %s condition %s failed on %s", artifact_name,
                      condition, self.client_id)
        self.state.artifacts_skipped_due_to_condition.append((artifact_name,
                                                              condition))
        return

    # Call the source defined action for each source.
    for source in artifact_obj.sources:
      # Check conditions on the source.
      source_conditions_met = True
      self.ConvertSupportedOSToConditions(source, source.conditions)
      if source.conditions:
        for condition in source.conditions:
          if not artifact_utils.CheckCondition(condition,
                                               self.state.knowledge_base):
            source_conditions_met = False

      if source_conditions_met:
        type_name = source.type
        source_type = artifact_registry.ArtifactSource.SourceType
        self.current_artifact_name = artifact_name
        if type_name == source_type.COMMAND:
          self.RunCommand(source)
        elif (type_name == source_type.DIRECTORY or
              type_name == source_type.LIST_FILES):
          # TODO(user): LIST_FILES will be replaced in favor of
          # DIRECTORY as used by the public artifacts repo.
          self.Glob(source, self.GetPathType())
        elif type_name == source_type.FILE:
          self.GetFiles(source, self.GetPathType(), self.args.max_file_size)
        elif type_name == source_type.GREP:
          self.Grep(source, self.GetPathType())
        elif type_name == source_type.PATH:
          # TODO(user): GRR currently ignores PATH types, they are currently
          # only useful to plaso during bootstrapping when the registry is
          # unavailable. The intention is to remove this type in favor of a
          # default fallback mechanism.
          pass
        elif type_name == source_type.REGISTRY_KEY:
          self.GetRegistryKey(source)
        elif type_name == source_type.REGISTRY_VALUE:
          self.GetRegistryValue(source)
        elif type_name == source_type.WMI:
          self.WMIQuery(source)
        elif type_name == source_type.REKALL_PLUGIN:
          self.RekallPlugin(source)
        # ARTIFACT is the legacy name for ARTIFACT_GROUP
        # per: https://github.com/ForensicArtifacts/artifacts/pull/143
        # TODO(user): remove legacy support after migration.
        elif type_name in (source_type.ARTIFACT, source_type.ARTIFACT_GROUP):
          self.CollectArtifacts(source)
        elif type_name == source_type.ARTIFACT_FILES:
          self.CollectArtifactFiles(source)
        elif type_name == source_type.GRR_CLIENT_ACTION:
          self.RunGrrClientAction(source)
        else:
          raise RuntimeError(
              "Invalid type %s in %s" % (type_name, artifact_name))

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

  def GetFiles(self, source, path_type, max_size):
    """Get a set of files."""
    new_path_list = []
    for path in source.attributes["paths"]:
      # Interpolate any attributes from the knowledgebase.
      new_path_list.extend(
          artifact_utils.InterpolateKbAttributes(
              path,
              self.state.knowledge_base,
              ignore_errors=self.args.ignore_interpolation_errors))

    action = rdf_file_finder.FileFinderAction.Download(max_size=max_size)

    self.CallFlow(
        file_finder.FileFinder.__name__,
        paths=new_path_list,
        pathtype=path_type,
        action=action,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state="ProcessFileFinderResults")

  @flow.StateHandler()
  def ProcessFileFinderResults(self, responses):
    if not responses.success:
      self.Log(
          "Failed to fetch files %s" % responses.request_data["artifact_name"])
    else:
      self.CallStateInline(
          next_state="ProcessCollected",
          request_data=responses.request_data,
          messages=[r.stat_entry for r in responses])

  def Glob(self, source, pathtype):
    """Glob paths, return StatEntry objects."""
    self.CallFlow(
        filesystem.Glob.__name__,
        paths=self.InterpolateList(source.attributes.get("paths", [])),
        pathtype=pathtype,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state="ProcessCollected")

  def _CombineRegex(self, regex_list):
    if len(regex_list) == 1:
      return regex_list[0]

    regex_combined = ""
    for regex in regex_list:
      if regex_combined:
        regex_combined = "%s|(%s)" % (regex_combined, regex)
      else:
        regex_combined = "(%s)" % regex
    return regex_combined

  def Grep(self, source, pathtype):
    """Grep files in paths for any matches to content_regex_list.

    Args:
      source: artifact source
      pathtype: pathspec path type

    When multiple regexes are supplied, combine them into a single regex as an
    OR match so that we check all regexes at once.
    """
    path_list = self.InterpolateList(source.attributes.get("paths", []))
    content_regex_list = self.InterpolateList(
        source.attributes.get("content_regex_list", []))

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
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state="ProcessCollected")

  def GetRegistryKey(self, source):
    self.CallFlow(
        filesystem.Glob.__name__,
        paths=self.InterpolateList(source.attributes.get("keys", [])),
        pathtype=paths.PathSpec.PathType.REGISTRY,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state="ProcessCollected")

  def GetRegistryValue(self, source):
    """Retrieve directly specified registry values, returning Stat objects."""
    new_paths = set()
    has_glob = False
    for kvdict in source.attributes["key_value_pairs"]:
      if "*" in kvdict["key"] or paths.GROUPING_PATTERN.search(kvdict["key"]):
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

      expanded_paths = artifact_utils.InterpolateKbAttributes(
          path,
          self.state.knowledge_base,
          ignore_errors=self.args.ignore_interpolation_errors)
      new_paths.update(expanded_paths)

    if has_glob:
      self.CallFlow(
          filesystem.Glob.__name__,
          paths=new_paths,
          pathtype=paths.PathSpec.PathType.REGISTRY,
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict()
          },
          next_state="ProcessCollected")
    else:
      # We call statfile directly for keys that don't include globs because it
      # is faster and some artifacts rely on getting an IOError to trigger
      # fallback processing.
      for new_path in new_paths:
        pathspec = paths.PathSpec(
            path=new_path, pathtype=paths.PathSpec.PathType.REGISTRY)

        # TODO(hanuszczak): Support for old clients ends on 2021-01-01.
        # This conditional should be removed after that date.
        if self.client_version >= 3221:
          stub = server_stubs.GetFileStat
          request = rdf_client.GetFileStatRequest(pathspec=pathspec)
        else:
          stub = server_stubs.StatFile
          request = rdf_client.ListDirRequest(pathspec=pathspec)

        self.CallClient(
            stub,
            request,
            request_data={
                "artifact_name": self.current_artifact_name,
                "source": source.ToPrimitiveDict()
            },
            next_state="ProcessCollectedRegistryStatEntry")

  def _StartSubArtifactCollector(self, artifact_list, source, next_state):
    self.CallFlow(
        ArtifactCollectorFlow.__name__,
        artifact_list=artifact_list,
        use_tsk=self.args.use_tsk,
        apply_parsers=self.args.apply_parsers,
        max_file_size=self.args.max_file_size,
        ignore_interpolation_errors=self.args.ignore_interpolation_errors,
        dependencies=self.args.dependencies,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state=next_state)

  def CollectArtifacts(self, source):
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["names"],
        source=source,
        next_state="ProcessCollected")

  def CollectArtifactFiles(self, source):
    """Collect files from artifact pathspecs."""
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["artifact_list"],
        source=source,
        next_state="ProcessCollectedArtifactFiles")

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
        next_state="ProcessCollected")

  def WMIQuery(self, source):
    """Run a Windows WMI Query."""
    query = source.attributes["query"]
    queries = artifact_utils.InterpolateKbAttributes(
        query,
        self.state.knowledge_base,
        ignore_errors=self.args.ignore_interpolation_errors)
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
          next_state="ProcessCollected")

  def RekallPlugin(self, source):
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdf_rekall_types.PluginRequest(
            plugin=source.attributes["plugin"],
            args=source.attributes.get("args", {}))
    ]

    self.CallFlow(
        memory.AnalyzeClientMemory.__name__,
        request=request,
        request_data={
            "artifact_name": self.current_artifact_name,
            "rekall_plugin": source.attributes["plugin"],
            "source": source.ToPrimitiveDict()
        },
        next_state="ProcessCollected")

  def _GetSingleExpansion(self, value):
    results = list(
        artifact_utils.InterpolateKbAttributes(
            value,
            self.state.knowledge_base,
            ignore_errors=self.args.ignore_interpolation_errors))
    if len(results) > 1:
      raise ValueError(
          "Interpolation generated multiple results, use a"
          " list for multi-value expansions. %s yielded: %s" % (value, results))
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
      if isinstance(value, basestring):
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
      if isinstance(value, basestring):
        results = list(
            artifact_utils.InterpolateKbAttributes(
                value,
                self.state.knowledge_base,
                ignore_errors=self.args.ignore_interpolation_errors))
        new_args.extend(results)
      else:
        new_args.extend(value)
    return new_args

  def RunGrrClientAction(self, source):
    """Call a GRR Client Action."""

    # Retrieve the correct rdfvalue to use for this client action.
    action_name = source.attributes["client_action"]
    try:
      action_stub = server_stubs.ClientActionStub.classes[action_name]
    except KeyError:
      raise RuntimeError("Client action %s not found." % action_name)

    self.CallClient(
        action_stub,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict()
        },
        next_state="ProcessCollected",
        **self.InterpolateDict(source.attributes.get("action_args", {})))

  def CallFallback(self, artifact_name, request_data):
    classes = artifact.ArtifactFallbackCollector.classes.items()
    for clsname, fallback_class in classes:

      if not aff4.issubclass(fallback_class,
                             artifact.ArtifactFallbackCollector):
        continue

      if artifact_name in fallback_class.artifacts:
        if artifact_name in self.state.called_fallbacks:
          self.Log("Already called fallback class %s for artifact: %s", clsname,
                   artifact_name)
        else:
          self.Log("Calling fallback class %s for artifact: %s", clsname,
                   artifact_name)

          self.CallFlow(
              clsname,
              request_data=request_data.ToDict(),
              artifact_name=artifact_name,
              next_state="ProcessCollected")

          # Make sure we only try this once
          self.state.called_fallbacks.add(artifact_name)
          return True
    return False

  @flow.StateHandler()
  def ProcessCollected(self, responses):
    """Each individual collector will call back into here.

    Args:
      responses: Responses from the collection.

    Raises:
      artifact_utils.ArtifactDefinitionError: On bad definition.
      artifact_utils.ArtifactProcessingError: On failure to process.
    """
    flow_name = self.__class__.__name__
    artifact_name = responses.request_data["artifact_name"]
    source = responses.request_data.GetItem("source", None)

    if responses.success:
      self.Log(
          "Artifact data collection %s completed successfully in flow %s "
          "with %d responses", artifact_name, flow_name, len(responses))
    else:
      self.Log("Artifact %s data collection failed. Status: %s.", artifact_name,
               responses.status)
      if not self.CallFallback(artifact_name, responses.request_data):
        self.state.failed_count += 1
        self.state.artifacts_failed.append(artifact_name)
      return

    output_collection_map = {}

    # Now process the responses.
    processors = parser.Parser.GetClassesByArtifact(artifact_name)
    saved_responses = {}
    for response in responses:
      if processors and self.args.apply_parsers:
        for processor in processors:
          processor_obj = processor()
          if processor_obj.process_together:
            # Store the response until we have them all.
            saved_responses.setdefault(processor.__name__, []).append(response)
          else:
            # Process the response immediately
            self._ParseResponses(processor_obj, response, responses,
                                 artifact_name, source, output_collection_map)
      else:
        # We don't have any defined processors for this artifact.
        self._ParseResponses(None, response, responses, artifact_name, source,
                             output_collection_map)

    # If we were saving responses, process them now:
    for processor_name, responses_list in saved_responses.items():
      processor_obj = parser.Parser.classes[processor_name]()
      self._ParseResponses(processor_obj, responses_list, responses,
                           artifact_name, source, output_collection_map)

    # Flush the results to the objects.
    if self.args.split_output_by_artifact:
      self._FinalizeSplitCollection(output_collection_map)

  @flow.StateHandler()
  def ProcessCollectedRegistryStatEntry(self, responses):
    """Create AFF4 objects for registry statentries.

    We need to do this explicitly because we call StatFile client action
    directly for performance reasons rather than using one of the flows that do
    this step automatically.

    Args:
      responses: Response objects from the artifact source.
    """
    if not responses.success:
      self.CallStateInline(next_state="ProcessCollected", responses=responses)
      return

    with data_store.DB.GetMutationPool() as pool:
      stat_entries = map(rdf_client.StatEntry, responses)
      filesystem.WriteStatEntries(
          stat_entries,
          client_id=self.client_id,
          mutation_pool=pool,
          token=self.token)

    self.CallStateInline(
        next_state="ProcessCollected",
        request_data=responses.request_data,
        messages=stat_entries)

  @flow.StateHandler()
  def ProcessCollectedArtifactFiles(self, responses):
    """Schedule files for download based on pathspec attribute.

    Args:
      responses: Response objects from the artifact source.
    Raises:
      RuntimeError: if pathspec value is not a PathSpec instance and not
                    a basestring.
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
      if not isinstance(pathspec, paths.PathSpec):
        try:
          pathspec = response.pathspec
        except AttributeError:
          pass

      if isinstance(pathspec, basestring):
        pathspec = paths.PathSpec(path=pathspec)
        if self.args.use_tsk:
          pathspec.pathtype = paths.PathSpec.PathType.TSK
        else:
          pathspec.pathtype = paths.PathSpec.PathType.OS

      if isinstance(pathspec, paths.PathSpec):
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
          next_state="ProcessCollected")
    else:
      self.Log("No files to download")

  def _GetArtifactReturnTypes(self, source):
    """Get a list of types we expect to handle from our responses."""
    if source:
      return source["returned_types"]

  def _ParseResponses(self, processor_obj, responses, responses_obj,
                      artifact_name, source, output_collection_map):
    """Create a result parser sending different arguments for diff parsers.

    Args:
      processor_obj: A Processor object that inherits from Parser.
      responses: A list of, or single response depending on the processors
         process_together setting.
      responses_obj: The responses object itself.
      artifact_name: Name of the artifact that generated the responses.
      source: The source responsible for producing the responses.
      output_collection_map: dict of collections when splitting by artifact

    Raises:
      RuntimeError: On bad parser.
    """
    _ = responses_obj
    result_iterator = artifact.ApplyParserToResponses(processor_obj, responses,
                                                      source, self, self.token)

    artifact_return_types = self._GetArtifactReturnTypes(source)

    if result_iterator:
      with data_store.DB.GetMutationPool() as pool:
        # If we have a parser, do something with the results it produces.
        for result in result_iterator:
          result_type = result.__class__.__name__
          if result_type == "Anomaly":
            self.SendReply(result)
          elif (not artifact_return_types or
                result_type in artifact_return_types):
            self.state.response_count += 1
            self.SendReply(result)
            self._WriteResultToSplitCollection(result, artifact_name,
                                               output_collection_map, pool)

  @classmethod
  def ResultCollectionForArtifact(cls, session_id, artifact_name, token=None):
    urn = rdfvalue.RDFURN("_".join((str(session_id.Add(flow.RESULTS_SUFFIX)),
                                    utils.SmartStr(artifact_name))))
    return sequential_collection.GeneralIndexedCollection(urn)

  def _WriteResultToSplitCollection(self, result, artifact_name,
                                    output_collection_map, mutation_pool):
    """Write any results to the collection if we are splitting by artifact.

    If not splitting, SendReply will handle writing to the collection.

    Args:
      result: result to write
      artifact_name: artifact name string
      output_collection_map: dict of collections when splitting by artifact
      mutation_pool: A MutationPool object to write to.
    """
    if self.args.split_output_by_artifact and self.runner.IsWritingResults():
      if artifact_name not in output_collection_map:
        # TODO(amoser): Make this work in the UI...
        # Create the new collections in the same directory but not as children,
        # so they are visible in the GUI
        collection = self.ResultCollectionForArtifact(self.urn, artifact_name)
        output_collection_map[artifact_name] = collection
      output_collection_map[artifact_name].Add(
          result, mutation_pool=mutation_pool)

  def _FinalizeSplitCollection(self, output_collection_map):
    """Flush all of the collections that were split by artifact."""
    total = 0
    for artifact_name, collection in output_collection_map.iteritems():
      l = len(collection)
      total += l
      self.Log("Wrote results from Artifact %s to %s. Collection size %d.",
               artifact_name, collection.collection_id, l)

    self.Log("Total collection size: %d", total)

  def _GetArtifactFromName(self, name):
    """Get an artifact class from the cache in the flow."""
    try:
      art_obj = artifact_registry.REGISTRY.GetArtifact(name)
    except artifact_registry.ArtifactNotRegisteredError:
      # If we don't have an artifact, things shouldn't have passed validation
      # so we assume its a new one in the datastore.
      artifact_registry.REGISTRY.ReloadDatastoreArtifacts()
      art_obj = artifact_registry.REGISTRY.GetArtifact(name)
    return art_obj

  @flow.StateHandler()
  def End(self):
    # If we got no responses, and user asked for it, we error out.
    if self.args.on_no_results_error and self.state.response_count == 0:
      raise artifact_utils.ArtifactProcessingError(
          "Artifact collector returned 0 responses.")


class ArtifactFilesDownloaderFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFilesDownloaderFlowArgs
  rdf_deps = [
      artifact_registry.ArtifactName,
      rdfvalue.ByteSize,
  ]


class ArtifactFilesDownloaderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFilesDownloaderResult
  rdf_deps = [
      paths.PathSpec,
      rdf_client.StatEntry,
  ]

  def GetOriginalResultType(self):
    if self.HasField("original_result_type"):
      return rdfvalue.RDFValue.classes.get(self.original_result_type)


class ArtifactFilesDownloaderFlow(transfer.MultiGetFileMixin, flow.GRRFlow):
  """Flow that downloads files referenced by collected artifacts."""

  category = "/Collectors/"
  args_type = ArtifactFilesDownloaderFlowArgs

  def FindMatchingPathspecs(self, response):
    # If we're dealing with plain file StatEntry, just
    # return it's pathspec - there's nothing to parse
    # and guess.
    if (isinstance(response, rdf_client.StatEntry) and
        response.pathspec.pathtype in [
            paths.PathSpec.PathType.TSK, paths.PathSpec.PathType.OS
        ]):
      return [response.pathspec]

    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    knowledge_base = artifact.GetArtifactKnowledgeBase(client)

    if self.args.use_tsk:
      path_type = paths.PathSpec.PathType.TSK
    else:
      path_type = paths.PathSpec.PathType.OS

    p = windows_persistence.WindowsPersistenceMechanismsParser()
    parsed_items = p.Parse(response, knowledge_base, path_type)

    return [item.pathspec for item in parsed_items]

  @flow.StateHandler()
  def Start(self):
    super(ArtifactFilesDownloaderFlow, self).Start()

    self.state.file_size = self.args.max_file_size
    self.state.results_to_download = []

    self.CallFlow(
        ArtifactCollectorFlow.__name__,
        next_state="DownloadFiles",
        artifact_list=self.args.artifact_list,
        use_tsk=self.args.use_tsk,
        max_file_size=self.args.max_file_size)

  @flow.StateHandler()
  def DownloadFiles(self, responses):
    if not responses.success:
      self.Log("Failed to run ArtifactCollectorFlow: %s", responses.status)
      return

    results_with_pathspecs = []
    results_without_pathspecs = []
    for response in responses:
      pathspecs = self.FindMatchingPathspecs(response)
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

    grouped_results = utils.GroupBy(results_with_pathspecs,
                                    lambda x: x.found_pathspec)
    for pathspec, group in grouped_results.items():
      self.StartFileFetch(pathspec, request_data=dict(results=group))

    for result in results_without_pathspecs:
      self.SendReply(result)

  def ReceiveFetchedFile(self, stat_entry, file_hash, request_data=None):
    if not request_data:
      raise RuntimeError("Expected non-empty request_data")

    for result in request_data["results"]:
      result.downloaded_file = stat_entry
      self.SendReply(result)

  def FileFetchFailed(self, pathspec, request_type, request_data=None):
    if not request_data:
      raise RuntimeError("Expected non-empty request_data")

    # If file doesn't exist, FileFetchFailed will be called twice:
    # once for StatFile client action, and then for HashFile client action (as
    # they're scheduled in parallel). We do a request_type check here to
    # avoid reporting same result twice.
    if request_type == "StatFile":
      for result in request_data["results"]:
        self.SendReply(result)
