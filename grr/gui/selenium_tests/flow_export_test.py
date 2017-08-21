#!/usr/bin/env python
"""Test the flow export."""


import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server import flow
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib


class TestFlowExport(gui_test_lib.GRRSeleniumTest):

  def setUp(self):
    super(TestFlowExport, self).setUp()

    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    with aff4.FACTORY.Open(
        self.client_id, mode="rw", token=self.token) as client:
      client.Set(client.Schema.HOSTNAME("HostC.0000000000000001"))
    self.RequestAndGrantClientApproval(self.client_id)
    self.action_mock = action_mocks.FileFinderClientMock()

  def testExportCommandIsShownForStatEntryResults(self):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=gui_test_lib.FlowWithOneStatEntryResult.__name__,
        client_id=self.client_id,
        token=self.token)
    for _ in flow_test_lib.TestFlowHelper(
        flow_urn, self.action_mock, client_id=self.client_id, token=self.token):
      pass

    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=li[heading=Results]")
    self.Click("link=Show export command")

    self.WaitUntil(
        self.IsTextPresent, "/usr/bin/grr_api_shell 'http://localhost:8000/' "
        "--exec_code 'grrapi.Client(\"C.0000000000000001\")."
        "Flow(\"%s\").GetFilesArchive()."
        "WriteToFile(\"./flow_results_C_0000000000000001_%s.zip\")'" %
        (flow_urn.Basename(), flow_urn.Basename().replace(":", "_")))

  def testExportCommandIsNotShownWhenNoResults(self):
    # RecursiveTestFlow doesn't send any results back.
    for _ in flow_test_lib.TestFlowHelper(
        gui_test_lib.RecursiveTestFlow.__name__,
        self.action_mock,
        client_id=self.client_id,
        token=self.token):
      pass

    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-flow-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show export command")

  def testExportCommandIsNotShownForNonFileResults(self):
    for _ in flow_test_lib.TestFlowHelper(
        gui_test_lib.FlowWithOneNetworkConnectionResult.__name__,
        self.action_mock,
        client_id=self.client_id,
        token=self.token):
      pass

    self.Open("/#/clients/C.0000000000000001/flows")
    self.Click("css=td:contains('FlowWithOneNetworkConnectionResult')")
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-flow-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show export command")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
