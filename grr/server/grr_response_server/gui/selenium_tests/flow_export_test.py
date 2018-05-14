#!/usr/bin/env python
"""Test the flow export."""


import unittest
from grr.lib import flags

from grr.server.grr_response_server import flow
from grr.server.grr_response_server.gui import gui_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib


@db_test_lib.DualDBTest
class TestFlowExport(gui_test_lib.GRRSeleniumTest):

  def setUp(self):
    super(TestFlowExport, self).setUp()

    self.client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(self.client_id)
    self.action_mock = action_mocks.FileFinderClientMock()

  def testExportCommandIsShownForStatEntryResults(self):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=gui_test_lib.FlowWithOneStatEntryResult.__name__,
        client_id=self.client_id,
        token=self.token)
    flow_test_lib.TestFlowHelper(
        flow_urn, self.action_mock, client_id=self.client_id, token=self.token)

    self.Open("/#/clients/%s/flows" % self.client_id)
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=li[heading=Results]")
    self.Click("link=Show export command")

    self.WaitUntil(
        self.IsTextPresent, "/usr/bin/grr_api_shell 'http://localhost:8000/' "
        "--exec_code 'grrapi.Client(\"%s\")."
        "Flow(\"%s\").GetFilesArchive()."
        "WriteToFile(\"./flow_results_%s_%s.zip\")'" % (
            self.client_id,
            flow_urn.Basename(),
            self.client_id.replace(".", "_"),
            flow_urn.Basename().replace(":", "_"),
        ))

  def testExportCommandIsNotShownWhenNoResults(self):
    # RecursiveTestFlow doesn't send any results back.
    flow_test_lib.TestFlowHelper(
        gui_test_lib.RecursiveTestFlow.__name__,
        self.action_mock,
        client_id=self.client_id,
        token=self.token)

    self.Open("/#/clients/%s/flows" % self.client_id)
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-flow-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show export command")

  def testExportCommandIsNotShownForNonFileResults(self):
    flow_test_lib.TestFlowHelper(
        gui_test_lib.FlowWithOneNetworkConnectionResult.__name__,
        self.action_mock,
        client_id=self.client_id,
        token=self.token)

    self.Open("/#/clients/%s/flows" % self.client_id)
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
