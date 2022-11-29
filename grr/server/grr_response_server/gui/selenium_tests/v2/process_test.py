#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server.flows.general import processes
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ListProcessesTest(gui_test_lib.GRRSeleniumTest):
  """Tests the ListProcesses Flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testDisplaysResults(self):
    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses,
        creator=self.test_username,
        client_id=self.client_id)
    flow_test_lib.MarkFlowAsFinished(self.client_id, flow_id)

    with flow_test_lib.FlowResultMetadataOverride(
        processes.ListProcesses,
        rdf_flow_objects.FlowResultMetadata(
            is_metadata_set=True,
            num_results_per_type_tag=[
                rdf_flow_objects.FlowResultCount(
                    type=rdf_client.Process.__name__, count=1)
            ])):
      self.Open(f"/v2/clients/{self.client_id}")
      self.WaitUntil(self.IsElementPresent,
                     "css=.flow-title:contains('Process')")

      flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
          rdf_client.Process(
              pid=5, name="testprocess", cmdline=["testprocess"])
      ])

      self.Click("css=result-accordion .title:contains('process')")
      self.WaitUntil(self.IsElementPresent, "css=:contains('testprocess')")


if __name__ == "__main__":
  app.run(test_lib.main)
