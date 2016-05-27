#!/usr/bin/env python
"""A flow to run checks for a host."""
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import flow
from grr.lib import parsers
from grr.lib.checks import checks
# pylint: disable=unused-import
from grr.lib.flows.general import collectors as _
# pylint: enable=unused-import
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class CheckFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CheckFlowArgs


class CheckRunner(flow.GRRFlow):
  """This flow runs checks on a host.

  CheckRunner:
  - Identifies what checks should be run for a host.
  - Identifies the artifacts that need to be collected to perform those checks.
  - Orchestrates collection of the host data.
  - Routes host data to the relevant checks.
  - Returns check data ready for reporting.
  """
  friendly_name = "Run Checks"
  category = "/Checks/"
  args_type = CheckFlowArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["MapArtifactData"])
  def Start(self):
    """Initialize the system check flow."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.Register("knowledge_base",
                        self.client.Get(self.client.Schema.KNOWLEDGE_BASE))
    self.state.Register("labels", self.client.GetLabels())
    self.state.Register("artifacts_wanted", {})
    self.state.Register("artifacts_fetched", set())
    self.state.Register("checks_run", [])
    self.state.Register("checks_with_findings", [])
    self.state.Register("results_store", None)
    self.state.Register("host_data", {})
    self.state.Register("path_type", rdf_paths.PathSpec.PathType.OS)
    self.CallState(next_state="MapArtifactData")

  @flow.StateHandler(next_state=["AddResponses", "RunChecks"])
  def MapArtifactData(self, responses):
    """Get processed data, mapped to artifacts.

    Identifies the artifacts that should be collected based on the os and labels
    of the client machine.

    Artifacts are acquired from the CheckRegistry as a dict, with artifact names
    as keys and a list of the parsers required by the checks as values.  These
    are used to only trigger the parsers required for the checks in cases where
    multiple parsers can be applied, and to parse the results once, rather than
    re-parse them within each check that uses the results.

    Args:
      responses: Input from previous states as an rdfvalue.Dict
    """
    self.state.artifacts_wanted = checks.CheckRegistry.SelectArtifacts(
        os_name=self.state.knowledge_base.os,
        restrict_checks=self.args.restrict_checks)
    for artifact_name in self.state.artifacts_wanted:
      self.CallFlow("ArtifactCollectorFlow",
                    artifact_list=[artifact_name],
                    apply_parsers=False,
                    request_data={"artifact_name": artifact_name},
                    next_state="AddResponses")
    self.CallState(next_state="RunChecks")

  def _ProcessData(self, processor, responses, artifact_name, source):
    """Runs parsers over the raw data and maps it to artifact_data types.

    Args:
      processor: A processor method to use.
      responses: One or more response items, depending on whether the processor
        uses Parse or ParseMultiple.
      artifact_name: The name of the artifact.
      source: The origin of the data, if specified.
    """
    # Now parse the data and set state.
    artifact_data = self.state.host_data.get(artifact_name)
    result_iterator = artifact.ApplyParserToResponses(processor, responses,
                                                      source, self.state,
                                                      self.token)

    for rdf in result_iterator:
      if isinstance(rdf, rdf_anomaly.Anomaly):
        artifact_data["ANOMALY"].append(rdf)
      else:
        artifact_data["PARSER"].append(rdf)

  def _RunProcessors(self, artifact_name, responses):
    """Manages processing of raw data from the artifact collection.

    The raw data and parsed results are stored in different result contexts:
    Anomaly, Parser and Raw. Demuxing these results makes the specific data
    types available to checks working in different contexts.

    Then, iterate over the parsers that should be applied to the raw data and
    map rdfvalues to the Parse context.

    Args:
      artifact_name: The name of the artifact being processed as a string.
      responses: Input from previous states as an rdfvalue.Dict
    """
    source = responses.request_data.GetItem("source", None)

    # Find all the parsers that should apply to an artifact.
    processors = parsers.Parser.GetClassesByArtifact(artifact_name)
    saved_responses = {}
    # For each item of collected host data, identify whether to parse
    # immediately or once all the artifact data is collected.
    # Then, send the host data for parsing and demuxing.
    for response in responses:
      if processors:
        for processor_cls in processors:
          processor = processor_cls()
          if processor.process_together:
            # Store the response until we have them all.
            processor_name = processor.__class__.__name__
            saved_responses.setdefault(processor_name, []).append(response)
          else:
            # Process the response immediately
            self._ProcessData(processor, response, artifact_name, source)

    # If we were saving responses, process them now:
    for processor_name, responses_list in saved_responses.items():
      processor = parsers.Parser.classes[processor_name]()
      self._ProcessData(processor, responses_list, artifact_name, source)

  @flow.StateHandler()
  def AddResponses(self, responses):
    """Process the raw response data from this artifact collection.

    The raw data and parsed results are stored in different result contexts:
    Anomaly, Parser and Raw.

    Add raw responses to the collection of data obtained for this artifact.
    Then, iterate over the parsers that should be applied to the raw data and
    map rdfvalues to the Parse context.

    Args:
      responses: Input from previous states as an rdfvalue.Dict
    """
    artifact_name = responses.request_data["artifact_name"]
    # In some cases, artifacts may not find anything. We create an empty set of
    # host data so the checks still run.
    artifact_data = self.state.host_data.setdefault(artifact_name, {})
    artifact_data["ANOMALY"] = []
    artifact_data["PARSER"] = []
    artifact_data["RAW"] = [r for r in responses]

    # If there are respones, run them through the parsers.
    if responses:
      self._RunProcessors(artifact_name, responses)

  @flow.StateHandler(next_state=["Done"])
  def RunChecks(self, responses):
    if not responses.success:
      raise RuntimeError("Checks did not run successfully.")
    # Hand host data across to checks. Do this after all data has been collected
    # in case some checks require multiple artifacts/results.
    for finding in checks.CheckHost(self.state.host_data,
                                    os_name=self.state.knowledge_base.os,
                                    restrict_checks=self.args.restrict_checks):
      self.state.checks_run.append(finding.check_id)
      if finding.anomaly:
        self.state.checks_with_findings.append(finding.check_id)
      self.SendReply(finding)
