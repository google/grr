#!/usr/bin/env python
"""Test the flow export."""


from grr.gui import gui_test_lib
from grr.gui import runtests_test

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client


class TestFlowExport(gui_test_lib.GRRSeleniumTest):

  def setUp(self):
    super(TestFlowExport, self).setUp()

    with self.ACLChecksDisabled():
      self.client_id = rdf_client.ClientURN("C.0000000000000001")
      with aff4.FACTORY.Open(
          self.client_id, mode="rw", token=self.token) as client:
        client.Set(client.Schema.HOSTNAME("HostC.0000000000000001"))
      self.RequestAndGrantClientApproval(self.client_id)
      self.action_mock = action_mocks.FileFinderClientMock()

  def testExportTabIsEnabledForStatEntryResults(self):
    with self.ACLChecksDisabled():
      for s in test_lib.TestFlowHelper(
          "FlowWithOneStatEntryResult",
          self.action_mock,
          client_id=self.client_id,
          token=self.token):
        session_id = s

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=li[heading=Results]")
    self.Click("link=Show GRR export tool command")

    self.WaitUntil(self.IsTextPresent, "--username %s collection_files "
                   "--path %s/Results" % (self.token.username, session_id))

  def testExportCommandIsNotDisabledWhenNoResults(self):
    # RecursiveTestFlow doesn't send any results back.
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          gui_test_lib.RecursiveTestFlow.__name__,
          self.action_mock,
          client_id=self.client_id,
          token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-flow-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show GRR export tool command")

  def testExportCommandIsNotShownForNonFileResults(self):
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneNetworkConnectionResult",
          self.action_mock,
          client_id=self.client_id,
          token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('FlowWithOneNetworkConnectionResult')")
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-flow-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show GRR export tool command")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
