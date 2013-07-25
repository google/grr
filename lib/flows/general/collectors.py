#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""These flows are designed for high performance transfers."""



import logging

from grr.lib import aff4
from grr.lib import artifact
from grr.lib import flow
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import type_info


class ArtifactCollectorFlow(flow.GRRFlow):
  """Flow that takes a list of artifacts and collects them."""

  category = "/Collectors/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.MultiSelectList(
          description="A list of Artifact class names.",
          name="artifact_list",
          default=[],
          ),
      type_info.Bool(
          description="Whether raw filesystem access should be used.",
          name="use_tsk",
          default=True)
      )

  @flow.StateHandler(next_state="ProcessCollected")
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.state.Register("collected_count", 0)
    self.state.Register("failed_count", 0)

    if self.state.use_tsk:
      self.state.Register("path_type", rdfvalue.PathSpec.PathType.TSK)
    else:
      self.state.Register("path_type", rdfvalue.PathSpec.PathType.OS)

    for cls_name in self.state.artifact_list:
      artifact_cls = self._GetArtifactClassFromName(cls_name)
      artifact_obj = artifact_cls()

      # Ensure we've been written sanely. Note that this could be removed if it
      # turns out to be expensive. Artifact tests should catch these.
      artifact_obj.Validate()

      self.Collect(artifact_obj)

  def Collect(self, artifact_obj):
    """Collect the raw data from the client for this artifact."""
    # Turn SUPPORTED_OS into a condition.
    for supported_os in artifact_obj.SUPPORTED_OS:
      artifact_obj.CONDITIONS.append(artifact.SUPPORTED_OS_MAP[supported_os])

    artifact_name = artifact_obj.__class__.__name__

    # Check each of the conditions match our target.
    for condition in artifact_obj.CONDITIONS:
      if not condition(self.client):
        logging.debug("Artifact %s condition %s failed on %s",
                      artifact_name, condition.func_name, self.client.client_id)
        return

    # Call the collector defined action for each collector.
    for collector in artifact_obj.COLLECTORS:
      for condition in collector.conditions:
        if not condition(self.client):
          logging.debug("Artifact Collector %s condition %s failed on %s",
                        artifact_name, condition.func_name,
                        self.client.client_id)
          continue

      # Handoff to the the correct Collector action.
      action_name = collector.action
      self.current_artifact_name = artifact_name
      if action_name == "RunCommand":
        self.RunCommand(**collector.args)
      elif action_name == "GetFile":
        self.GetFile(path_type=self.state.path_type, **collector.args)
      elif action_name == "GetFiles":
        self.GetFiles(path_type=self.state.path_type, **collector.args)
      elif action_name == "WMIQuery":
        self.WMIQuery(**collector.args)
      else:
        raise RuntimeError("Invalid action action_name in %s" % artifact_name)

  def GetFiles(self, path_list, path_type):
    """Get a set of files."""
    new_path_list = []
    for path in path_list:
      # Temporary hacks for handling conversion handling artifact nomenclature
      # conversion.
      # In particular this is where knowledgebase interpolation will eventually
      # go once we have defined it.
      path = path.replace("%%systemroot%%", "c:\\windows\\system32")
      new_path_list.append(path)

    self.CallFlow(
        "GlobAndDownload", paths=new_path_list, pathtype=path_type,
        request_data={"artifact_name": self.current_artifact_name},
        next_state="ProcessCollected"
        )

  def GetFile(self, path, path_type):
    """Convenience shortcut to GetFiles to get a single file path."""
    self.GetFiles([path], path_type=path_type)

  def RunCommand(self, cmd, args):
    """Run a command."""
    self.CallClient("ExecuteCommand", cmd=cmd, args=args,
                    request_data={"artifact_name": self.current_artifact_name},
                    next_state="ProcessCollected")

  def WMIQuery(self, query):
    """Run a Windows WMI Query."""
    self.CallClient(
        "WmiQuery", query=query,
        request_data={"artifact_name": self.current_artifact_name,
                      "query": query},
        next_state="ProcessCollected"
        )

  @flow.StateHandler()
  def ProcessCollected(self, responses):
    """Each individual collector will call back into here.

    Args:
      responses: Responses from the collection.

    Raises:
      artifact.ArtifactDefinitionError: On bad definition.
      artifact.ArtifactProcessingError: On failure to process.
    """
    flow_name = self.__class__.__name__
    artifact_cls_name = responses.request_data["artifact_name"]
    if responses.success:
      self.Log("Artifact %s completed successfully in flow %s",
               artifact_cls_name, flow_name)
      self.state.collected_count += 1
    else:
      self.Log("Artifact %s collection failed. Flow %s failed to complete",
               artifact_cls_name, flow_name)
      self.state.failed_count += 1
      return

    # Now we've finished collection process the results.
    artifact_cls = self._GetArtifactClassFromName(artifact_cls_name)
    artifact_obj = artifact_cls()

    if not hasattr(artifact_obj, "PROCESSOR"):
      # No processor for the responses set, we're done.
      return
    processor = artifact_obj.PROCESSOR
    processor_obj = parsers.Parser.classes.get(processor)()

    # Determine where to write the responses in AFF4 space.
    aff4_obj, aff4_attr, operator = (
        self.GetAFF4PathForArtifactResponses(processor_obj))

    # Now process the responses.
    for response in responses:
      if isinstance(processor_obj, parsers.CommandParser):
        result_parser = processor_obj.Parse(cmd=response.request.cmd,
                                            args=response.request.args,
                                            stdout=response.stdout,
                                            stderr=response.stderr,
                                            return_val=response.exit_status,
                                            time_taken=response.time_used)
      elif isinstance(processor_obj, parsers.WMIQueryParser):
        result_parser = processor_obj.Parse(responses.request_data["query"],
                                            response)

      if result_parser:
        if operator == "Append":
          for result in result_parser:
            aff4_attr.Append(result)
          aff4_obj.Set(aff4_attr)

        elif operator == "Overwrite":
          # We set for each new value, overwriting older ones.
          for result in result_parser:
            aff4_obj.Set(aff4_attr)

    # Flush the results to the object.
    aff4_obj.Flush()
    logging.debug("Wrote Artifact %s results to %s on %s", artifact_cls_name,
                  aff4_obj.urn, aff4_attr.__class__.__name__)
    self.SendReply(aff4_obj.urn)

  def GetAFF4PathForArtifactResponses(self, processor):
    """Use the RDFValue type to find where in AFF4 space to write results."""
    if hasattr(processor, "out_type"):
      rdf_type = artifact.GRRArtifactMappings.rdf_map.get(processor.out_type)
      if rdf_type is None:
        raise artifact.ArtifactProcessingError(
            "No defined RDF type for %s" % processor.out_type)

      # "info/software", "InstalledSoftwarePackages", "INSTALLED_PACKAGES",
      # "Append"
      relative_path, aff4_type, aff4_attribute, operator = rdf_type

      urn = self.client_id.Add(relative_path)
      result_object = aff4.FACTORY.Open(urn, aff4_type=aff4_type, mode="w",
                                        token=self.token)
      if not result_object:
        raise artifact.ArtifactProcessingError(
            "Failed to open result object for %s" % processor)
      result_attr = getattr(result_object.Schema, aff4_attribute)()
      if not isinstance(result_attr, rdfvalue.RDFValue):
        raise artifact.ArtifactProcessingError(
            "Failed to get attribute %s for artifact %s" %
            (aff4_attribute, processor.__name__))

      return result_object, result_attr, operator

  def _GetArtifactClassFromName(self, name):
    if name not in artifact.Artifact.classes:
      raise RuntimeError("ArtifactCollectorFlow failed due to unknown Artifact"
                         " %s" % name)
    return artifact.Artifact.classes[name]

  @flow.StateHandler()
  def End(self):
    self.Notify("FlowStatus", self.client_id,
                "Completed artifact collection of %s. Collected %d. Errors %d."
                % (self.state.artifact_list, self.state.collected_count,
                   self.state.failed_count))
