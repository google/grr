#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_server.flows.general import network
from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class NetstatTest(gui_test_lib.GRRSeleniumTest):
  """Tests the Netstat Flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)

  def testFiltering(self):
    flow_id = flow_test_lib.StartFlow(
        network.Netstat, creator=self.test_username, client_id=self.client_id)

    self.Open(f"/v2/clients/{self.client_id}")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('All connections')")

    flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
        rdf_client_network.NetworkConnection(process_name=f"process{i}")
        for i in range(10)
    ])

    self.Click("css=result-accordion .title:contains('All connections')")
    for i in range(10):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")

    self.Type("css=.filter-input input", "process0")
    self.WaitUntil(self.IsElementPresent, "css=td:contains('process0')")
    self.assertEqual(self.GetCssCount("css=td:contains('process')"), 1)

  def testSorting(self):
    flow_args = network.NetstatArgs(listening_only=True)
    flow_id = flow_test_lib.StartFlow(
        network.Netstat,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    self.Open(f"/v2/clients/{self.client_id}")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('Listening only')")

    flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
        rdf_client_network.NetworkConnection(process_name=f"process{i}")
        for i in range(3)
    ])

    self.Click("css=result-accordion .title:contains('Listening only')")
    for i in range(3):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")

    self.Click("css=.mat-sort-header:contains('Process Name')")
    for i in [0, 1, 2]:  # reordered results asc
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")

    self.Click("css=.mat-sort-header:contains('Process Name')")
    for i in [2, 1, 0]:  # reordered results desc
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")

  def testPaginationNavigation(self):
    flow_args = network.NetstatArgs(listening_only=True)
    flow_id = flow_test_lib.StartFlow(
        network.Netstat,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    self.Open(f"/v2/clients/{self.client_id}")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('Listening only')")

    flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
        rdf_client_network.NetworkConnection(process_name=f"process{i}")
        for i in range(15)
    ])

    self.Click("css=result-accordion .title:contains('Listening only')")
    for i in range(10):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")
    self.assertEqual(self.GetCssCount("css=td:contains('process')"), 10)

    # Navigation works in both top and bottom paginators.
    self.Click("css=.top-paginator .mat-paginator-navigation-last")
    for i in range(10, 15):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")
    self.assertEqual(self.GetCssCount("css=td:contains('process')"), 5)

    self.ScrollToBottom()
    self.Click("css=.bottom-paginator .mat-paginator-navigation-previous")
    for i in range(10):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")
    self.assertEqual(self.GetCssCount("css=td:contains('process')"), 10)

  def testPaginationSize(self):
    flow_args = network.NetstatArgs(listening_only=False)
    flow_id = flow_test_lib.StartFlow(
        network.Netstat,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=flow_args)

    self.Open(f"/v2/clients/{self.client_id}")
    self.WaitUntil(self.IsElementPresent,
                   "css=result-accordion .title:contains('All connections')")

    flow_test_lib.AddResultsToFlow(self.client_id, flow_id, [
        rdf_client_network.NetworkConnection(process_name=f"process{i}")
        for i in range(15)
    ])

    self.Click("css=result-accordion .title:contains('All connections')")
    for i in range(10):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")
    self.assertEqual(self.GetCssCount("css=td:contains('process')"), 10)

    # Select one paginator updates the other paginator as well as the displayed
    # rows.
    self.MatSelect("css=.bottom-paginator mat-select", "50")
    self.WaitUntilContains("50", self.GetText, "css=.top-paginator mat-select")
    self.WaitUntilContains("50", self.GetText,
                           "css=.bottom-paginator mat-select")
    for i in range(15):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")
    self.assertEqual(self.GetCssCount("css=td:contains('process')"), 15)

    self.MatSelect("css=.top-paginator mat-select", "10")
    self.WaitUntilContains("10", self.GetText, "css=.top-paginator mat-select")
    self.WaitUntilContains("10", self.GetText,
                           "css=.bottom-paginator mat-select")
    for i in range(10):
      self.WaitUntil(self.IsElementPresent, f"css=td:contains('process{i}')")
    self.assertEqual(self.GetCssCount("css=td:contains('process')"), 10)


if __name__ == "__main__":
  app.run(test_lib.main)
