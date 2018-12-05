#!/usr/bin/env python
"""Test the flow export."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestFlowExport(gui_test_lib.GRRSeleniumTest):

  def setUp(self):
    super(TestFlowExport, self).setUp()

    self.client_id = self.SetupClient(0).Basename()
    self.RequestAndGrantClientApproval(self.client_id)
    self.action_mock = action_mocks.FileFinderClientMock()

  def testExportCommandIsShownForStatEntryResults(self):
    session_id = flow_test_lib.TestFlowHelper(
        gui_test_lib.FlowWithOneStatEntryResult.__name__,
        client_mock=self.action_mock,
        client_id=self.client_id,
        token=self.token)
    if not data_store.RelationalDBFlowsEnabled():
      session_id = session_id.Basename()

    self.Open("/#/clients/%s/flows" % self.client_id)
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=li[heading=Results]")
    self.Click("link=Show export command")

    expected_command = ("/usr/bin/grr_api_shell 'http://localhost:8000/' "
                        "--exec_code 'grrapi.Client(\"%s\")."
                        "Flow(\"%s\").GetFilesArchive()."
                        "WriteToFile(\"./flow_results_%s_%s.zip\")'" % (
                            self.client_id,
                            session_id,
                            self.client_id.replace(".", "_"),
                            session_id.replace(":", "_"),
                        ))
    self.WaitUntil(self.IsTextPresent, expected_command)

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


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
