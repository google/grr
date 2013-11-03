#!/usr/bin/env python
"""Flows for handling the collection for artifacts."""

import re
import time

import logging

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
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

  @flow.StateHandler(next_state=["ProcessCollected", "ProcessRegistryValue",
                                 "ProcessBootstrap"])
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.state.Register("collected_count", 0)
    self.state.Register("artifacts_skipped_due_to_condition", [])
    self.state.Register("failed_count", 0)
    self.state.Register("artifacts_failed", [])
    self.state.Register("bootstrap_complete", False)
    self.state.Register("knowledge_base", self.args.knowledge_base)

    if self.args.use_tsk:
      self.state.Register("path_type", rdfvalue.PathSpec.PathType.TSK)
    else:
      self.state.Register("path_type", rdfvalue.PathSpec.PathType.OS)

    output = self.args.output.format(t=time.time(), u=self.state.context.user)
    self.state.Register("output_urn", self.client_id.Add(output))

    if not self.state.knowledge_base:
      # If not provided, get a knowledge base from the client.
      self.state.knowledge_base = artifact.GetArtifactKnowledgeBase(self.client)

    if not self.args.artifact_list:
      raise flow.FlowError("No artifacts to collect")

    for cls_name in self.args.artifact_list:
      artifact_cls = self._GetArtifactClassFromName(cls_name)
      artifact_obj = artifact_cls()

      # Ensure artifact has been written sanely. Note that this could be
      # removed if it turns out to be expensive. Artifact tests should catch
      # these.
      artifact_obj.Validate()

      self.Collect(artifact_obj)

  def Collect(self, artifact_obj):
    """Collect the raw data from the client for this artifact."""
    artifact_name = artifact_obj.__class__.__name__

    test_conditions = list(artifact_obj.CONDITIONS)
    # Turn SUPPORTED_OS into a condition.
    if artifact_obj.SUPPORTED_OS:
      os_match = lambda kb: kb.os in artifact_obj.SUPPORTED_OS
      test_conditions.append(os_match)

    # Check each of the conditions match our target.
    for condition in test_conditions:
      if not condition(self.state.knowledge_base):
        logging.debug("Artifact %s condition %s failed on %s",
                      artifact_name, condition.func_name, self.client.client_id)
        self.state.artifacts_skipped_due_to_condition.append(
            (artifact_name, condition.func_name))
        return

    # Call the collector defined action for each collector.
    for collector in artifact_obj.COLLECTORS:
      action_name = collector.action
      self.current_artifact_name = artifact_name
      if action_name == "Bootstrap":
        # Can't do anything with a bootstrap action.
        pass
      elif action_name == "RunCommand":
        self.RunCommand(**collector.args)
      elif action_name == "GetFile":
        self.GetFile(path_type=self.state.path_type, **collector.args)
      elif action_name == "GetFiles":
        self.GetFiles(path_type=self.state.path_type, **collector.args)
      elif action_name == "GetRegistryKeys":
        self.GetRegistry(path_list=collector.args["path_list"])
      elif action_name == "GetRegistryValue":
        self.GetRegistryValue(path=collector.args["path"])
      elif action_name == "GetRegistryValues":
        self.GetRegistryValue(path=collector.args["paths"])
      elif action_name == "WMIQuery":
        self.WMIQuery(**collector.args)
      elif action_name == "RunGrrClientAction":
        self.RunGrrClientAction(collector.args["client_action"],
                                collector.args.get("action_args", {}))
      else:
        raise RuntimeError("Invalid action %s in %s" % (action_name,
                                                        artifact_name))

  def GetFiles(self, path_list, path_type):
    """Get a set of files."""
    new_path_list = []
    for path in path_list:
      # Interpolate any attributes from the knowledgebase.
      new_path_list.extend(artifact_lib.InterpolateKbAttributes(
          path, self.state.knowledge_base))

    self.CallFlow(
        "GlobAndDownload", paths=new_path_list, pathtype=path_type,
        request_data={"artifact_name": self.current_artifact_name},
        next_state="ProcessCollected"
        )

  def GetFile(self, path, path_type):
    """Convenience shortcut to GetFiles to get a single file path."""
    self.GetFiles([path], path_type=path_type)

  def GetRegistry(self, path_list):
    """Retrieve globbed registry values, returning Stat objects."""
    new_path_list = []
    for path in path_list:
      # Interpolate any attributes from the knowledgebase.
      new_path_list.extend(artifact_lib.InterpolateKbAttributes(
          path, self.state.knowledge_base))

    self.CallFlow(
        "Glob", paths=new_path_list,
        pathtype=rdfvalue.PathSpec.PathType.REGISTRY,
        request_data={"artifact_name": self.current_artifact_name},
        next_state="ProcessCollected"
        )

  def GetRegistryValue(self, path):
    """Retrieve directly specified registry values, returning Stat objects."""
    paths = artifact_lib.InterpolateKbAttributes(path,
                                                 self.state.knowledge_base)
    for new_path in paths:
      pathspec = rdfvalue.PathSpec(path=new_path,
                                   pathtype=rdfvalue.PathSpec.PathType.REGISTRY)
      self.CallClient(
          "StatFile", pathspec=pathspec,
          request_data={"artifact_name": self.current_artifact_name},
          next_state="ProcessRegistryValue"
          )

  def RunCommand(self, cmd, args):
    """Run a command."""
    self.CallClient("ExecuteCommand", cmd=cmd, args=args,
                    request_data={"artifact_name": self.current_artifact_name},
                    next_state="ProcessCollected")

  def WMIQuery(self, query):
    """Run a Windows WMI Query."""
    queries = artifact_lib.InterpolateKbAttributes(query,
                                                   self.state.knowledge_base)
    for query in queries:
      self.CallClient(
          "WmiQuery", query=query,
          request_data={"artifact_name": self.current_artifact_name,
                        "query": query},
          next_state="ProcessCollected"
          )

  def RunGrrClientAction(self, client_action, action_args):
    """Call a GRR Client Action."""
    self.CallClient(
        client_action,
        request_data={"artifact_name": self.current_artifact_name},
        next_state="ProcessCollected",
        **action_args
        )

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
    artifact_cls_name = responses.request_data["artifact_name"]
    if responses.success:
      self.Log("Artifact data collection %s completed successfully in flow %s "
               "with %d responses", artifact_cls_name, flow_name,
               len(responses))
      self.state.collected_count += 1
    else:
      self.Log("Artifact %s data collection failed. Status: %s.",
               artifact_cls_name, responses.status)
      self.state.failed_count += 1
      self.state.artifacts_failed.append(artifact_cls_name)
      return

    # Initialize some local non-state saved variables for processing.
    if self.args.output:
      if self.args.split_output_by_artifact:
        self.output_collection_map = {}
      else:
        self.output_collection = None
    if self.args.store_results_in_aff4:
      self.aff4_output_map = {}

    # Now process the responses.
    processors = parsers.Parser.GetClassesByArtifact(artifact_cls_name)
    saved_responses = {}
    for response in responses:
      if processors:
        for processor in processors:
          processor_obj = processor()
          if processor_obj.process_together:
            # Store the response until we have them all.
            saved_responses.setdefault(processor.__name__, []).append(response)
          else:
            # Process the response immediately
            self._ParseResponses(processor_obj, response, responses,
                                 artifact_cls_name)
      else:
        # We don't have any defined processors for this artifact, we treat it
        # like a dumb collection and send results back directly.
        self.SendReply(response)
        if self.args.output:
          self._WriteResultToCollection(response, artifact_cls_name)

    # If we were saving responses, process them now:
    for processor_name, responses_list in saved_responses.items():
      processor_obj = parsers.Parser.classes[processor_name]()
      self._ParseResponses(processor_obj, responses_list, responses,
                           artifact_cls_name)

    # Flush the results to the objects.
    if self.args.output:
      self._FinalizeCollection(artifact_cls_name)
    if self.args.store_results_in_aff4:
      self._FinalizeMappedAFF4Locations(artifact_cls_name)

  def _ParseResponses(self, processor_obj, responses, responses_obj,
                      artifact_name):
    """Create a result parser sending different arguments for diff parsers.

    Args:
      processor_obj: A Processor object that inherits from Parser.
      responses: A list of, or single response depending on the processors
         process_together setting.
      responses_obj: The responses object itself.
      artifact_name: Name of the artifact that generated the responses.
    """
    if not processor_obj.process_together:
      response = responses   # There is a single response.
    if isinstance(processor_obj, parsers.CommandParser):
      result_parser = processor_obj.Parse(
          cmd=response.request.cmd,
          args=response.request.args,
          stdout=response.stdout,
          stderr=response.stderr,
          return_val=response.exit_status,
          time_taken=response.time_used,
          knowledge_base=self.state.knowledge_base)

    elif isinstance(processor_obj, parsers.WMIQueryParser):
      result_parser = processor_obj.Parse(responses_obj.request_data["query"],
                                          responses,
                                          self.state.knowledge_base)

    elif isinstance(processor_obj, parsers.RegistryValueParser):
      result_parser = processor_obj.Parse(response,
                                          self.state.knowledge_base)

    elif isinstance(processor_obj, parsers.RegistryParser):
      if processor_obj.process_together:
        result_parser = processor_obj.ParseMultiple(
            responses, self.state.knowledge_base)
      else:
        result_parser = processor_obj.Parse(
            responses, self.state.knowledge_base)

    if result_parser:
      # If we have a parser, do something with the results it produces.
      for result in result_parser:
        self.SendReply(result)    # Send to parent.
        if self.args.output:
          # Output is set, we need to write to a collection.
          self._WriteResultToCollection(result, artifact_name)
        if self.args.store_results_in_aff4:
          # Write our result back to a mapped location in AFF4 space.
          self._WriteResultToMappedAFF4Location(result)

  def _WriteResultToCollection(self, result, artifact_name):
    """Write any results to the collection."""
    if self.args.split_output_by_artifact:
      if artifact_name not in self.output_collection_map:
        urn = self.state.output_urn.Add(artifact_name)
        collection = aff4.FACTORY.Create(urn, "RDFValueCollection", mode="rw",
                                         token=self.token)
        # Cache the opened object.
        self.output_collection_map[artifact_name] = collection
      self.output_collection_map[artifact_name].Add(result)
    else:
      if not self.output_collection:
        self.output_collection = aff4.FACTORY.Create(
            self.state.output_urn, "RDFValueCollection", mode="rw",
            token=self.token)
      self.output_collection.Add(result)

  def _FinalizeCollection(self, artifact_name):
    """Finalize writes to the Collection."""
    total = 0
    if self.args.split_output_by_artifact:
      for collection in self.output_collection_map.values():
        total += len(collection)
        collection.Flush()
    else:
      if self.output_collection:
        self.output_collection.Flush()
        total += len(self.output_collection)
    self.Log("Wrote results from Artifact %s to %s. Collection size %d.",
             artifact_name, self.state.output_urn, total)

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
    """

    rdf_type = artifact.GRRArtifactMappings.rdf_map.get(output_type)
    if rdf_type is None:
      raise artifact_lib.ArtifactProcessingError(
          "No defined RDF type for %s" % output_type)

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

  def _GetArtifactClassFromName(self, name):
    if name not in artifact_lib.Artifact.classes:
      raise RuntimeError("ArtifactCollectorFlow failed due to unknown Artifact"
                         " %s" % name)
    return artifact_lib.Artifact.classes[name]

  @flow.StateHandler()
  def End(self):
    if self.args.output:
      urn = self.state.output_urn
    else:
      urn = self.client_id
    self.Notify("ViewObject", urn,
                "Completed artifact collection of %s. Collected %d. Errors %d."
                % (self.args.artifact_list, self.state.collected_count,
                   self.state.failed_count))
