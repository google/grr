#!/usr/bin/env python
"""A flow to run checks for a host."""
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.checks import checks
from grr.proto import flows_pb2


class CheckFlowArgs(rdfvalue.RDFProtoStruct):
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
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["MapArtifactData"])
  def Start(self):
    """."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.Register("knowledge_base",
                        client.Get(client.Schema.KNOWLEDGE_BASE))
    self.state.Register("labels", client.GetLabels())
    self.state.Register("artifacts_wanted", set())
    self.state.Register("artifacts_fetched", set())
    self.state.Register("checks_run", [])
    self.state.Register("checks_with_findings", [])
    self.state.Register("results_store", None)
    self.state.Register("host_data", {})
    self.CallState(next_state="MapArtifactData")

  @flow.StateHandler(next_state=["AddResponses", "RunChecks"])
  def MapArtifactData(self, responses):
    """Get processed data, mapped to artifacts."""
    self.state.artifacts_wanted = checks.CheckRegistry.SelectArtifacts(
        os=self.state.knowledge_base.os)
    # Fetch Artifacts and map results to the artifacts that generated them.
    # This is an inefficient collection, but necessary because results need to
    # be mapped to the originating artifact. An alternative would be to have
    # rdfvalues labeled with originating artifact ids.
    for artifact_id in self.state.artifacts_wanted:
      self.CallFlow("ArtifactCollectorFlow", artifact_list=[artifact_id],
                    request_data={"artifact_id": artifact_id},
                    next_state="AddResponses")
    self.CallState(next_state="RunChecks")

  @flow.StateHandler()
  def AddResponses(self, responses):
    artifact_id = responses.request_data["artifact_id"]
    # TODO(user): Check whether artifact collection succeeded.
    self.state.host_data[artifact_id] = list(responses)

  @flow.StateHandler(next_state=["Done"])
  def RunChecks(self, responses):
    if not responses.success:
      raise RuntimeError("Checks did not run successfully.")
    # Hand host data across to checks. Do this after all data has been collected
    # in case some checks require multiple artifacts/results.
    for finding in checks.CheckHost(self.state.host_data,
                                    os=self.state.knowledge_base.os):
      self.state.checks_run.append(finding.check_id)
      if finding.anomaly:
        self.state.checks_with_findings.append(finding.check_id)
      self.SendReply(finding)

