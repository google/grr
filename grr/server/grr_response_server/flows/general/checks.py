#!/usr/bin/env python
"""A flow to run checks for a host."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import parsers
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import artifact
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.check_lib import checks
from grr_response_server.flows.general import collectors


class CheckFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CheckFlowArgs

  # TODO(hanuszczak): Add a `use_tsk` field to the flow args because otherwise
  # it is useless on Windows.
  @property
  def path_type(self):
    return rdf_paths.PathSpec.PathType.OS


@flow_base.DualDBFlow
class CheckRunnerMixin(object):
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

  def Start(self):
    """Initialize the system check flow."""
    self.state.knowledge_base = self.client_knowledge_base
    self.state.artifacts_wanted = {}
    self.state.artifacts_fetched = set()
    self.state.checks_run = []
    self.state.checks_with_findings = []
    self.state.results_store = None
    self.state.host_data = {}
    self.MapArtifactData()

  def MapArtifactData(self):
    """Get processed data, mapped to artifacts.

    Identifies the artifacts that should be collected based on the os and labels
    of the client machine.

    Artifacts are acquired from the CheckRegistry as a dict, with artifact names
    as keys and a list of the parsers required by the checks as values.  These
    are used to only trigger the parsers required for the checks in cases where
    multiple parsers can be applied, and to parse the results once, rather than
    re-parse them within each check that uses the results.
    """
    self.state.artifacts_wanted = checks.CheckRegistry.SelectArtifacts(
        os_name=self.state.knowledge_base.os,
        restrict_checks=self.args.restrict_checks)
    for artifact_name in self.state.artifacts_wanted:
      self.CallFlow(
          collectors.ArtifactCollectorFlow.__name__,
          artifact_list=[artifact_name],
          apply_parsers=False,
          request_data={"artifact_name": artifact_name},
          next_state="AddResponses")
    self.CallState(next_state="RunChecks")

  def _RunProcessors(self, artifact_name, responses):
    """Manages processing of raw data from the artifact collection.

    The raw data and parsed results are stored in different result contexts:
    Anomaly, Parser and Raw. Demuxing these results makes the specific data
    types available to checks working in different contexts.

    Then, iterate over the parsers that should be applied to the raw data and
    map rdfvalues to the Parse context.

    Args:
      artifact_name: The name of the artifact being processed as a string.
      responses: A list of RDF value responses.
    """
    parser_factory = parsers.ArtifactParserFactory(artifact_name)
    artifact_data = self.state.host_data.get(artifact_name)

    results = artifact.ApplyParsersToResponses(parser_factory, responses, self)
    for result in results:
      if isinstance(result, rdf_anomaly.Anomaly):
        artifact_data["ANOMALY"].append(result)
      else:
        artifact_data["PARSER"].append(result)

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
    artifact_name = unicode(responses.request_data["artifact_name"])
    # In some cases, artifacts may not find anything. We create an empty set of
    # host data so the checks still run.
    artifact_data = self.state.host_data.get(artifact_name, {})
    artifact_data["ANOMALY"] = []
    artifact_data["PARSER"] = []
    artifact_data["RAW"] = [r for r in responses]
    self.state.host_data[artifact_name] = artifact_data

    # If there are respones, run them through the parsers.
    if responses:
      self._RunProcessors(artifact_name, list(responses))

  def RunChecks(self, responses):
    if not responses.success:
      raise RuntimeError("Checks did not run successfully.")
    # Hand host data across to checks. Do this after all data has been collected
    # in case some checks require multiple artifacts/results.
    for finding in checks.CheckHost(
        self.state.host_data,
        os_name=self.state.knowledge_base.os,
        restrict_checks=self.args.restrict_checks):
      self.state.checks_run.append(finding.check_id)
      if finding.anomaly:
        self.state.checks_with_findings.append(finding.check_id)
      self.SendReply(finding)
