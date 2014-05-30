#!/usr/bin/env python
"""Flows for handling the collection for artifacts."""

import re

import logging

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class BootStrapKnowledgeBaseFlow(flow.GRRFlow):
  """Flow that finds core bootstrap artifacts.

  To use artifacts we need to be able to interpolate paths that the artifacts
  use. These are stored in the knowledgebase. However most of the things in the
  knowledge base come from artifacts, which in turn rely on facts in the
  knowledge base. To resolve the dependency loop we rely on a couple of core
  knowledge base values that we call Bootstrap values.

  This flow collects or guesses those Bootstrap values.
  """

  @flow.StateHandler(next_state="ProcessRegStat")
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.Register("bootstrap_initialized", False)

    system = self.client.Get(self.client.Schema.SYSTEM)
    if system != "Windows":
      # We don't need bootstrapping for non-windows clients at the moment.
      self.state.bootstrap_initialized = True
      self.CallState(next_state="End")
      return

    # First try querying the registry, this should work fine for live clients
    # but won't support offline clients.
    system_root_reg = (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT"
                       r"\CurrentVersion\SystemRoot")
    pathspec = rdfvalue.PathSpec(path=system_root_reg,
                                 pathtype=rdfvalue.PathSpec.PathType.REGISTRY)
    self.CallClient("StatFile", pathspec=pathspec,
                    request_data={"bootstrap_var": "system_root"},
                    next_state="ProcessRegStat")

  @flow.StateHandler(next_state="ProcessFileStats")
  def ProcessRegStat(self, responses):
    """Check SystemRoot registry value."""
    if responses.success:
      systemroot = responses.First().registry_data.GetValue()
      if systemroot:
        systemdrive = systemroot[0:2]
        if re.match(r"^[A-Za-z]:$", systemdrive):
          self.SendReply(rdfvalue.Dict({"environ_systemroot": systemroot,
                                        "environ_systemdrive": systemdrive}))
          self.state.bootstrap_initialized = True
          return

    # If registry querying didn't work, we try to guess common paths instead.
    system_drive_opts = ["C:", "D:"]
    for drive in system_drive_opts:
      pathspec = rdfvalue.PathSpec(path=drive,
                                   pathtype=rdfvalue.PathSpec.PathType.OS)
      self.CallClient("ListDirectory", pathspec=pathspec,
                      request_data={"bootstrap_var": "system_root"},
                      next_state="ProcessFileStats")

  @flow.StateHandler(next_state="End")
  def ProcessFileStats(self, responses):
    """Extract DataBlob from Stat response."""
    if not responses.success:
      return
    system_root_paths = ["Windows", "WinNT", "WINNT35", "WTSRV"]

    for response in responses:
      if response.pathspec.path[4:] in system_root_paths:
        systemdrive = response.pathspec.path[1:3]
        systemroot = "%s\\%s" % (systemdrive, response.pathspec.path[4:])
        self.SendReply(rdfvalue.Dict({"environ_systemroot": systemroot,
                                      "environ_systemdrive": systemdrive}))
        self.state.bootstrap_initialized = True
        break

  @flow.StateHandler()
  def End(self):
    """Finalize and test if we succeeded. No notification required."""
    if not self.state.bootstrap_initialized:
      raise flow.FlowError("Could not bootstrap systemroot.")


class ArtifactCollectorFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactCollectorFlowArgs

  def Validate(self):
    if not self.artifact_list:
      raise ValueError("No artifacts to collect.")


class ArtifactCollectorFlow(flow.GRRFlow):
  """Flow that takes a list of artifacts and collects them.

  This flow is the core of the Artifact implementation for GRR. Artifacts are
  defined using a standardized data format that includes what to collect and
  how to process the things collected. This flow takes that data driven format
  and makes it useful.

  The core functionality of Artifacts is split into Collectors and Processors.

  An Artifact defines a set of Collectors that are used to retrieve data from
  the client. These can specify collection of files, registry keys, command
  output and others. The first part of this flow "Collect" handles running those
  collections by issuing GRR flows and client actions.

  The results of those are then collected and GRR searches for Processors that
  know how to process the output of the Collectors. The Processors all inherit
  from the Parser class, and each Parser specifies which Artifacts it knows how
  to process.

  So this flow hands off the collected rdfvalue results to the Processors which
  then return modified or different rdfvalues. These final results are then
  either:
  1. Sent to the calling flow.
  2. Written to a collection.
  3. Stored in AFF4 based on a special mapping called the GRRArtifactMappings.
  4. A combination of the above.
  This is controlled by the flow parameters.
  """

  category = "/Collectors/"
  args_type = ArtifactCollectorFlowArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["StartCollection"])
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.state.Register("artifacts_skipped_due_to_condition", [])
    self.state.Register("failed_count", 0)
    self.state.Register("artifacts_failed", [])
    self.state.Register("bootstrap_complete", False)
    self.state.Register("knowledge_base", self.args.knowledge_base)
    self.state.Register("client_anomaly_store", None)

    if self.args.use_tsk:
      self.state.Register("path_type", rdfvalue.PathSpec.PathType.TSK)
    else:
      self.state.Register("path_type", rdfvalue.PathSpec.PathType.OS)

    if not self.state.knowledge_base:
      # If not provided, get a knowledge base from the client.
      try:
        self.state.knowledge_base = artifact.GetArtifactKnowledgeBase(
            self.client)
      except artifact_lib.KnowledgeBaseUninitializedError:
        # If no-one has ever initialized the knowledge base, we should do so
        # now.
        if not self._AreArtifactsKnowledgeBaseArtifacts():
          self.CallFlow("KnowledgeBaseInitializationFlow",
                        next_state="StartCollection")
          return

    # In all other cases start the collection state.
    self.CallState(next_state="StartCollection")

  @flow.StateHandler(next_state=["ProcessCollected",
                                 "ProcessCollectedArtifactFiles",
                                 "ProcessFileFinderResults",
                                 "ProcessRegistryValue", "ProcessBootstrap"])
  def StartCollection(self, responses):
    """Start collecting."""
    if not responses.success:
      raise artifact_lib.KnowledgeBaseUninitializedError(
          "Attempt to initialize Knowledge Base failed.")
    else:
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
      filter_str = " OR ".join("os == '%s'" % o for o in
                               src_object.supported_os)
      return filter_list.append(filter_str)

  def Collect(self, artifact_obj):
    """Collect the raw data from the client for this artifact."""
    artifact_name = artifact_obj.name

    test_conditions = list(artifact_obj.conditions)
    self.ConvertSupportedOSToConditions(artifact_obj, test_conditions)

    # Check each of the conditions match our target.
    for condition in test_conditions:
      if not artifact_lib.CheckCondition(condition, self.state.knowledge_base):
        logging.debug("Artifact %s condition %s failed on %s",
                      artifact_name, condition, self.client_id)
        self.state.artifacts_skipped_due_to_condition.append(
            (artifact_name, condition))
        return

    # Call the collector defined action for each collector.
    for collector in artifact_obj.collectors:

      # Check conditions on the collector.
      collector_conditions_met = True
      self.ConvertSupportedOSToConditions(collector, collector.conditions)
      if collector.conditions:
        for condition in collector.conditions:
          if not artifact_lib.CheckCondition(condition,
                                             self.state.knowledge_base):
            collector_conditions_met = False

      if collector_conditions_met:
        action_name = collector.action
        self.current_artifact_name = artifact_name
        if action_name == "Bootstrap":
          # Can't do anything with a bootstrap action.
          pass
        elif action_name == "RunCommand":
          self.RunCommand(collector)
        elif action_name == "GetFiles":
          self.GetFiles(collector, self.state.path_type,
                        self.args.max_file_size)
        elif action_name == "Grep":
          self.Grep(collector, self.state.path_type)
        elif action_name == "ListFiles":
          self.Glob(collector, self.state.path_type)
        elif action_name == "GetRegistryKeys":
          self.Glob(collector, rdfvalue.PathSpec.PathType.REGISTRY)
        elif action_name == "GetRegistryValue":
          self.GetRegistryValue(collector)
        elif action_name == "GetRegistryValues":
          self.GetRegistryValue(collector)
        elif action_name == "WMIQuery":
          self.WMIQuery(collector)
        elif action_name == "VolatilityPlugin":
          self.VolatilityPlugin(collector)
        elif action_name == "CollectArtifacts":
          self.CollectArtifacts(collector)
        elif action_name == "CollectArtifactFiles":
          self.CollectArtifactFiles(collector)
        elif action_name == "RunGrrClientAction":
          self.RunGrrClientAction(collector)
        else:
          raise RuntimeError("Invalid action %s in %s" % (action_name,
                                                          artifact_name))

      else:
        logging.debug("Artifact %s no collectors run due to all collectors "
                      "having failing conditons on %s", artifact_name,
                      self.client_id)

  def _AreArtifactsKnowledgeBaseArtifacts(self):
    knowledgebase_list = config_lib.CONFIG["Artifacts.knowledge_base"]
    for artifact_name in self.args.artifact_list:
      if artifact_name not in knowledgebase_list:
        return False
    return True

  def GetFiles(self, collector, path_type, max_size):
    """Get a set of files."""
    new_path_list = []
    for path in collector.args["path_list"]:
      # Interpolate any attributes from the knowledgebase.
      new_path_list.extend(artifact_lib.InterpolateKbAttributes(
          path, self.state.knowledge_base))

    action = rdfvalue.FileFinderAction(
        action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD,
        download=rdfvalue.FileFinderDownloadActionOptions(max_size=max_size))

    self.CallFlow(
        "FileFinder", paths=new_path_list, pathtype=path_type, action=action,
        request_data={"artifact_name": self.current_artifact_name,
                      "collector": collector.ToPrimitiveDict()},
        next_state="ProcessFileFinderResults")

  @flow.StateHandler(next_state=["ProcessCollected"])
  def ProcessFileFinderResults(self, responses):
    if not responses.success:
      self.Log("Failed to fetch files %s" %
               responses.request_data["artifact_name"])
    else:
      self.CallStateInline(next_state="ProcessCollected",
                           request_data=responses.request_data,
                           messages=[r.stat_entry for r in responses])

  def Glob(self, collector, pathtype):
    """Glob paths, return StatEntry objects."""
    self.CallFlow(
        "Glob", paths=self.InterpolateList(collector.args.get("path_list", [])),
        pathtype=pathtype,
        request_data={"artifact_name": self.current_artifact_name,
                      "collector": collector.ToPrimitiveDict()},
        next_state="ProcessCollected"
        )

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

  def Grep(self, collector, pathtype):
    """Grep files in path_list for any matches to content_regex_list.

    Args:
      collector: artifact collector
      pathtype: pathspec path type

    When multiple regexes are supplied, combine them into a single regex as an
    OR match so that we check all regexes at once.
    """
    path_list = self.InterpolateList(collector.args.get("path_list", []))
    content_regex_list = self.InterpolateList(
        collector.args.get("content_regex_list", []))

    regex_condition = rdfvalue.FileFinderContentsRegexMatchCondition(
        regex=self._CombineRegex(content_regex_list), bytes_before=0,
        bytes_after=0)

    file_finder_condition = rdfvalue.FileFinderCondition(
        condition_type=rdfvalue.FileFinderCondition.Type.CONTENTS_REGEX_MATCH,
        contents_regex_match=regex_condition)

    self.CallFlow("FileFinder", paths=path_list,
                  conditions=[file_finder_condition],
                  action=rdfvalue.FileFinderAction(), pathtype=pathtype,
                  request_data={"artifact_name": self.current_artifact_name,
                                "collector": collector.ToPrimitiveDict()},
                  next_state="ProcessCollected")

  def GetRegistryValue(self, collector):
    """Retrieve directly specified registry values, returning Stat objects."""
    if collector.action == "GetRegistryValue":
      path_list = [collector.args["path"]]
    elif collector.action == "GetRegistryValues":
      path_list = collector.args["path_list"]

    new_paths = set()
    for path in path_list:
      expanded_paths = artifact_lib.InterpolateKbAttributes(
          path, self.state.knowledge_base)
      new_paths.update(expanded_paths)

    for new_path in new_paths:
      pathspec = rdfvalue.PathSpec(path=new_path,
                                   pathtype=rdfvalue.PathSpec.PathType.REGISTRY)
      self.CallClient(
          "StatFile", pathspec=pathspec,
          request_data={"artifact_name": self.current_artifact_name,
                        "collector": collector.ToPrimitiveDict()},
          next_state="ProcessRegistryValue"
          )

  def CollectArtifacts(self, collector):
    self.CallFlow(
        "ArtifactCollectorFlow", artifact_list=collector.args["artifact_list"],
        use_tsk=self.args.use_tsk,
        store_results_in_aff4=False,
        request_data={"artifact_name": self.current_artifact_name,
                      "collector": collector.ToPrimitiveDict()},
        next_state="ProcessCollected"
        )

  def CollectArtifactFiles(self, collector):
    """Collect files from artifact pathspecs."""
    self.CallFlow(
        "ArtifactCollectorFlow", artifact_list=collector.args["artifact_list"],
        use_tsk=self.args.use_tsk,
        store_results_in_aff4=False,
        request_data={"artifact_name": self.current_artifact_name,
                      "collector": collector.ToPrimitiveDict()},
        next_state="ProcessCollectedArtifactFiles"
        )

  def RunCommand(self, collector):
    """Run a command."""
    self.CallClient("ExecuteCommand", cmd=collector.args["cmd"],
                    args=collector.args.get("args", {}),
                    request_data={"artifact_name": self.current_artifact_name,
                                  "collector": collector.ToPrimitiveDict()},
                    next_state="ProcessCollected")

  def WMIQuery(self, collector):
    """Run a Windows WMI Query."""
    query = collector.args["query"]
    queries = artifact_lib.InterpolateKbAttributes(query,
                                                   self.state.knowledge_base)
    for query in queries:
      self.CallClient(
          "WmiQuery", query=query,
          request_data={"artifact_name": self.current_artifact_name,
                        "collector": collector.ToPrimitiveDict()},
          next_state="ProcessCollected"
          )

  def VolatilityPlugin(self, collector):
    """Run a Volatility Plugin."""
    request = rdfvalue.VolatilityRequest()
    request.args[collector.args["plugin"]] = self.InterpolateDict(
        collector.args.get("args", {}))

    self.CallFlow(
        "AnalyzeClientMemoryVolatility", request=request,
        request_data={"artifact_name": self.current_artifact_name,
                      "vol_plugin": collector.args["plugin"],
                      "collector": collector.ToPrimitiveDict()},
        next_state="ProcessCollected"
        )

  def _GetSingleExpansion(self, value):
    results = list(artifact_lib.InterpolateKbAttributes(
        value, self.state.knowledge_base))
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
      if isinstance(value, basestring):
        new_args[key] = self._GetSingleExpansion(value)
      elif isinstance(value, list):
        new_args[key] = self.InterpolateList(value)
      else:
        new_args[key] = value
    return new_args

  def InterpolateList(self, input_list):
    """Interpolate all items from a given collector array.

    Args:
      input_list: list of values to interpolate
    Returns:
      original list of values extended with strings interpolated
    """
    new_args = []
    for value in input_list:
      if isinstance(value, basestring):
        results = list(artifact_lib.InterpolateKbAttributes(
            value, self.state.knowledge_base))
        new_args.extend(results)
      else:
        new_args.extend(value)
    return new_args

  def RunGrrClientAction(self, collector):
    """Call a GRR Client Action."""
    self.CallClient(
        collector.args["client_action"],
        request_data={"artifact_name": self.current_artifact_name,
                      "collector": collector.ToPrimitiveDict()},
        next_state="ProcessCollected",
        **self.InterpolateDict(collector.args.get("action_args", {})))

  @flow.StateHandler(next_state="ProcessCollected")
  def ProcessRegistryValue(self, responses):
    """Extract DataBlob from Stat response."""
    # TODO(user): This currently does no transformation.
    message = responses.First()
    if not responses.success or not message.registry_data:
      self.Log("Failed to get registry value %s" %
               responses.request_data["artifact_name"])
    else:
      self.CallState(next_state="ProcessCollected",
                     request_data=responses.request_data.ToDict(),
                     messages=[message])

  @flow.StateHandler()
  def ProcessCollected(self, responses):
    """Each individual collector will call back into here.

    Args:
      responses: Responses from the collection.

    Raises:
      artifact_lib.ArtifactDefinitionError: On bad definition.
      artifact_lib.ArtifactProcessingError: On failure to process.
    """
    flow_name = self.__class__.__name__
    artifact_name = responses.request_data["artifact_name"]
    collector = responses.request_data.GetItem("collector", None)

    if responses.success:
      self.Log("Artifact data collection %s completed successfully in flow %s "
               "with %d responses", artifact_name, flow_name,
               len(responses))
    else:
      self.Log("Artifact %s data collection failed. Status: %s.",
               artifact_name, responses.status)
      self.state.failed_count += 1
      self.state.artifacts_failed.append(artifact_name)
      return

    # Initialize some local non-state saved variables for processing.
    if self.runner.output is not None:
      if self.args.split_output_by_artifact:
        self.output_collection_map = {}

    if self.args.store_results_in_aff4:
      self.aff4_output_map = {}

    # Now process the responses.
    processors = parsers.Parser.GetClassesByArtifact(artifact_name)
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
                                 artifact_name, collector)
      else:
        # We don't have any defined processors for this artifact.
        self._ParseResponses(None, response, responses, artifact_name,
                             collector)

    # If we were saving responses, process them now:
    for processor_name, responses_list in saved_responses.items():
      processor_obj = parsers.Parser.classes[processor_name]()
      self._ParseResponses(processor_obj, responses_list, responses,
                           artifact_name, collector)

    # Flush the results to the objects.
    if self.runner.output is not None:
      self._FinalizeCollection(artifact_name)
    if self.args.store_results_in_aff4:
      self._FinalizeMappedAFF4Locations(artifact_name)
    if self.state.client_anomaly_store:
      self.state.client_anomaly_store.Flush()

  @flow.StateHandler(next_state="ProcessCollected")
  def ProcessCollectedArtifactFiles(self, responses):
    """Schedule files for download based on pathspec attribute.

    Args:
      responses: Response objects from the artifact collector.
    Raises:
      RuntimeError: if pathspec value is not a PathSpec instance and not
                    a basestring.
    """
    self.download_list = []
    collector = responses.request_data.GetItem("collector")
    pathspec_attribute = collector["args"].get("pathspec_attribute", None)

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
      if not isinstance(pathspec, rdfvalue.PathSpec):
        try:
          pathspec = response.pathspec
        except AttributeError:
          pass

      if isinstance(pathspec, basestring):
        pathspec = rdfvalue.PathSpec(path=pathspec)
        if self.args.use_tsk:
          pathspec.pathtype = rdfvalue.PathSpec.PathType.TSK
        else:
          pathspec.pathtype = rdfvalue.PathSpec.PathType.OS
        self.download_list.append(pathspec)

      elif isinstance(pathspec, rdfvalue.PathSpec):
        self.download_list.append(pathspec)

      else:
        raise RuntimeError(
            "Response must be a string path, a pathspec, or have "
            "pathspec_attribute set. Got: %s" % pathspec)

    if self.download_list:
      request_data = responses.request_data.ToDict()
      self.CallFlow("MultiGetFile", pathspecs=self.download_list,
                    request_data=request_data,
                    next_state="ProcessCollected")
    else:
      self.Log("No files to download")

  def _GetArtifactReturnTypes(self, collector):
    """Get a list of types we expect to handle from our responses."""
    if collector:
      return collector["returned_types"]

  def _ProcessAnomaly(self, anomaly_value):
    """Write anomalies to the client in the data store."""
    if not self.state.client_anomaly_store:
      self.state.client_anomaly_store = aff4.FACTORY.Create(
          self.client_id.Add("anomalies"), "RDFValueCollection",
          token=self.token, mode="rw")
    self.state.client_anomaly_store.Add(anomaly_value)

  def _ParseResponses(self, processor_obj, responses, responses_obj,
                      artifact_name, collector):
    """Create a result parser sending different arguments for diff parsers.

    Args:
      processor_obj: A Processor object that inherits from Parser.
      responses: A list of, or single response depending on the processors
         process_together setting.
      responses_obj: The responses object itself.
      artifact_name: Name of the artifact that generated the responses.
      collector: The collector responsible for producing the responses.

    Raises:
      RuntimeError: On bad parser.
    """
    _ = responses_obj
    if not processor_obj:
      # We don't do any parsing, the results are raw as they came back.
      result_iterator = responses

    else:
      # We have some processors to run.
      if processor_obj.process_together:
        # We are processing things in a group which requires specialized
        # handling by the parser. This is used when multiple responses need to
        # be combined to parse successfully. E.g parsing passwd and shadow files
        # together.
        parse_method = processor_obj.ParseMultiple
      else:
        parse_method = processor_obj.Parse

      if isinstance(processor_obj, parsers.CommandParser):
        # Command processor only supports one response at a time.
        response = responses
        result_iterator = parse_method(
            cmd=response.request.cmd,
            args=response.request.args,
            stdout=response.stdout,
            stderr=response.stderr,
            return_val=response.exit_status,
            time_taken=response.time_used,
            knowledge_base=self.state.knowledge_base)

      elif isinstance(processor_obj, parsers.WMIQueryParser):
        query = collector["args"]["query"]
        result_iterator = parse_method(query, responses,
                                       self.state.knowledge_base)

      elif isinstance(processor_obj, parsers.FileParser):
        if processor_obj.process_together:
          file_objects = [aff4.FACTORY.Open(r.aff4path, token=self.token)
                          for r in responses]
          result_iterator = parse_method(responses, file_objects,
                                         self.state.knowledge_base)
        else:
          fd = aff4.FACTORY.Open(responses.aff4path,
                                 token=self.token)
          result_iterator = parse_method(responses, fd,
                                         self.state.knowledge_base)

      elif isinstance(processor_obj, (parsers.RegistryParser,
                                      parsers.VolatilityPluginParser,
                                      parsers.RegistryValueParser,
                                      parsers.GenericResponseParser,
                                      parsers.GrepParser)):
        result_iterator = parse_method(responses, self.state.knowledge_base)

      elif isinstance(processor_obj, (parsers.ArtifactFilesParser)):
        result_iterator = parse_method(responses, self.state.knowledge_base,
                                       self.state.path_type)

      else:
        raise RuntimeError("Unsupported parser detected %s" % processor_obj)

    artifact_return_types = self._GetArtifactReturnTypes(collector)

    if result_iterator:
      # If we have a parser, do something with the results it produces.
      for result in result_iterator:
        result_type = result.__class__.__name__
        if result_type == "Anomaly":
          # Anomalies are special results and get handled separately.
          self._ProcessAnomaly(result)
        elif not artifact_return_types or result_type in artifact_return_types:
          self.SendReply(result)    # Send to parent.
          if self.runner.output is not None:
            # Output is set, we need to write to a collection.
            self._WriteResultToCollection(result, artifact_name)
          if self.args.store_results_in_aff4:
            # Write our result back to a mapped location in AFF4 space.
            self._WriteResultToMappedAFF4Location(result)

  def _WriteResultToCollection(self, result, artifact_name):
    """Write any results to the collection."""
    if self.args.split_output_by_artifact:
      if (self.runner.output is not None and
          artifact_name not in self.output_collection_map):
        urn = self.runner.output.urn.Add(artifact_name)
        collection = aff4.FACTORY.Create(urn, "RDFValueCollection", mode="rw",
                                         token=self.token)
        # Cache the opened object.
        self.output_collection_map[artifact_name] = collection
      self.output_collection_map[artifact_name].Add(result)
    else:
      # If not split the SendReply handling will take care of collection adding.
      pass

  def _FinalizeCollection(self, artifact_name):
    """Finalize writes to the Collection."""
    total = 0
    if self.args.split_output_by_artifact:
      for collection in self.output_collection_map.values():
        total += len(collection)
        collection.Flush()
    else:
      if self.runner.output is not None:
        self.runner.output.Flush()
        total += len(self.runner.output)

    if self.runner.output is not None:
      self.Log("Wrote results from Artifact %s to %s. Collection size %d.",
               artifact_name, self.runner.output.urn, total)

  def _WriteResultToMappedAFF4Location(self, result):
    """If we have a mapping for this result type, write it there."""
    result_type = result.__class__.__name__
    if result_type not in self.aff4_output_map:
      aff4_obj, aff4_attr, operator = (
          self.GetAFF4PathForArtifactResponses(result_type))
      # Cache the opened object.
      self.aff4_output_map[result_type] = (aff4_obj, aff4_attr, operator)
    else:
      aff4_obj, aff4_attr, operator = self.aff4_output_map[result_type]

    if operator == "Append":
      aff4_attr.Append(result)
    elif operator == "Overwrite":
      # We set for each new value, overwriting older ones.
      aff4_obj.Set(aff4_attr)

  def _FinalizeMappedAFF4Locations(self, artifact_name):
    for aff4_obj, aff4_attr, operator in self.aff4_output_map.values():
      if operator == "Append":
        # For any objects we appended to, we need to do the set now as the new
        # attributes aren't assigned to the AFF4 object yet.
        aff4_obj.Set(aff4_attr)
      aff4_obj.Flush()
      self.Log("Wrote Artifact %s results to %s on %s", artifact_name,
               aff4_obj.urn, aff4_attr.__class__.__name__)

  def GetAFF4PathForArtifactResponses(self, output_type):
    """Use the RDFValue type to find where in AFF4 space to write results.

    Args:
      output_type: The name of a SemanticValue type.

    Returns:
      A tuple of (aff4 object, attribute, operator)

    Raises:
      ArtifactProcessingError: If there is no defined mapping.
    """

    rdf_type = artifact.GRRArtifactMappings.rdf_map.get(output_type)
    if rdf_type is None:
      raise artifact_lib.ArtifactProcessingError(
          "No defined RDF type for %s.  See the description for "
          " the store_results_in_aff4 option, you probably want it set to "
          "false. Supported types are: %s" %
          (output_type, artifact.GRRArtifactMappings.rdf_map.keys()))

    # "info/software", "InstalledSoftwarePackages", "INSTALLED_PACKAGES",
    # "Append"
    relative_path, aff4_type, aff4_attribute, operator = rdf_type

    urn = self.client_id.Add(relative_path)
    try:
      result_object = aff4.FACTORY.Open(urn, aff4_type=aff4_type, mode="w",
                                        token=self.token)
    except IOError as e:
      raise artifact_lib.ArtifactProcessingError(
          "Failed to open result object for type %s. %s" % (output_type, e))

    result_attr = getattr(result_object.Schema, aff4_attribute)()
    if not isinstance(result_attr, rdfvalue.RDFValue):
      raise artifact_lib.ArtifactProcessingError(
          "Failed to get attribute %s for output type %s" %
          (aff4_attribute, output_type))

    return result_object, result_attr, operator

  def _GetArtifactFromName(self, name):
    """Get an artifact class from the cache in the flow."""
    if name in artifact_lib.ArtifactRegistry.artifacts:
      return artifact_lib.ArtifactRegistry.artifacts[name]
    else:
      # If we don't have an artifact, things shouldn't have passed validation
      # so we assume its a new one in the datastore.
      artifact.LoadArtifactsFromDatastore(token=self.token)
      if name not in artifact_lib.ArtifactRegistry.artifacts:
        raise RuntimeError("ArtifactCollectorFlow failed due to unknown "
                           "Artifact %s" % name)
      else:
        return artifact_lib.ArtifactRegistry.artifacts[name]

  @flow.StateHandler()
  def End(self):
    # If we got no responses, and user asked for it, we error out.
    collect_count = self.runner.args.request_state.response_count
    if self.args.no_results_errors and collect_count == 0:
      raise artifact_lib.ArtifactProcessingError("Artifact collector returned "
                                                 "0 responses.")
    if self.runner.output is not None:
      urn = self.runner.output.urn
    else:
      urn = self.client_id

    self.Notify("ViewObject", urn,
                "Completed artifact collection of %s. Collected %d. Errors %d."
                % (self.args.artifact_list, collect_count,
                   self.state.failed_count))
