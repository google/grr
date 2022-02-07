#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr_response_server.flows.general import read_low_level
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ReadLowLevelTest(gui_test_lib.GRRSeleniumTest):
  """Tests the ReadLowLevel Flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testSubmitForm(self):
    self.Open(f"/v2/clients/{self.client_id}")

    self.WaitUntil(self.IsElementPresent, "css=input[name=flowSearchBox]")

    self.Type(
        "css=input[name=flowSearchBox]",
        "Read raw bytes from device",
        end_with_enter=True)

    self.WaitUntil(self.IsElementPresent, "css=input[name=path]")
    self.WaitUntil(self.IsElementPresent, "css=input[name=length]")
    self.WaitUntil(self.IsElementPresent, "css=input[name=offset]")

    self.Type("css=input[name=path]", "/place")
    self.Type("css=input[name=length]", "123")
    self.Type("css=input[name=offset]", "456")

    self.Click("css=button[type=submit]")

    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('/place')")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('123')")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('456')")
    self.assertLen(flow_test_lib.ListAllFlows(client_id=self.client_id), 1)

  def testDisplaysDownloadButtonAndArgs(self):
    flow_args = rdf_read_low_level.ReadLowLevelArgs(
        path="/path", length="789", offset="987")

    flow_id = flow_test_lib.StartFlow(
        read_low_level.ReadLowLevel,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)
    print("flow_id", flow_id)

    self.Open(f"/v2/clients/{self.client_id}")

    self.WaitUntil(self.IsElementPresent,
                   f"css=.flow-id span:contains('{flow_id}')")

    self.ScrollToBottom()
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('/path')")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('789')")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('987')")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=a[mat-stroked-button]:contains('Download')")
    flow_test_lib.MarkFlowAsFinished(client_id=self.client_id, flow_id=flow_id)
    with flow_test_lib.FlowResultMetadataOverride(
        read_low_level.ReadLowLevel,
        rdf_flow_objects.FlowResultMetadata(
            is_metadata_set=True,
            num_results_per_type_tag=[
                rdf_flow_objects.FlowResultCount(
                    type=rdf_read_low_level.ReadLowLevelFlowResult.__name__,
                    count=1)
            ])):
      self.WaitUntil(self.IsElementPresent,
                     "css=a[mat-stroked-button]:contains('Download')")

    self.WaitUntil(
        self.IsElementPresent,
        f"css=a[href='/api/v2/clients/{self.client_id}/vfs-blob/temp/"
        f"{self.client_id}_{flow_id}_path']")

    self.Click("css=result-accordion .title:contains('/path')")

    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion:contains('Path: /path')")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion:contains('Length: 789')")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion:contains('Offset: 987')")


if __name__ == "__main__":
  app.run(test_lib.main)
