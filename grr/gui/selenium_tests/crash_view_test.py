#!/usr/bin/env python
"""Test the flow_management interface."""

import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server import foreman as rdf_foreman
from grr.server.hunts import implementation
from grr.server.hunts import standard
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib


class TestCrashView(gui_test_lib.GRRSeleniumTest):
  """Tests the crash view."""

  client_id = rdf_client.ClientURN("C.0000000000000001")

  def SetUpCrashedFlow(self):
    client = flow_test_lib.CrashClientMock(self.client_id, self.token)
    for _ in flow_test_lib.TestFlowHelper(
        flow_test_lib.FlowWithOneClientRequest.__name__,
        client,
        client_id=self.client_id,
        token=self.token,
        check_flow_errors=False):
      pass

  def testOpeningCrashesOfUnapprovedClientRedirectsToHostInfoPage(self):
    self.Open("/#/clients/C.0000000000000002/crashes")

    # As we don't have an approval for C.0000000000000002, we should be
    # redirected to the host info page.
    self.WaitUntilEqual("/#/clients/C.0000000000000002/host-info",
                        self.GetCurrentUrlPath)
    self.WaitUntil(self.IsTextPresent,
                   "You do not have an approval for this client.")

  def testClientCrashedFlow(self):
    self.SetUpCrashedFlow()
    self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    self.Click("css=a[grrtarget='client.flows']")
    self.WaitUntil(self.IsTextPresent,
                   flow_test_lib.FlowWithOneClientRequest.__name__)

    # Check that skull icon is in place.
    self.WaitUntil(self.IsElementPresent, "css=img[src$='skull-icon.png']")

    # Click on the crashed flow.
    self.Click("css=td:contains(FlowWithOneClientRequest)")

    # Check that "Flow Information" tab displays crash data.
    self.WaitUntil(self.AllTextsPresent, [
        "CLIENT_CRASHED", "aff4:/C.0000000000000001/flows/",
        "Reason: Client crashed."
    ])

  def SetUpCrashedFlowInHunt(self):
    client_ids = [rdf_client.ClientURN("C.%016X" % i) for i in range(0, 10)]
    client_mocks = dict([(client_id, flow_test_lib.CrashClientMock(
        client_id, self.token)) for client_id in client_ids])

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client", attribute_regex=""))
    ])

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.SampleHunt.__name__,
        client_rule_set=client_rule_set,
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      self.assertTrue(foreman.AssignTasksToClient(client_id))
    hunt_test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False,
                                                  self.token)

    return client_ids

  def testClientCrashedFlowInHunt(self):
    client_ids = self.SetUpCrashedFlowInHunt()

    self.Open("/")

    # Go to hunt manager and select a hunt.
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.Click("css=td:contains('SampleHunt')")

    # Click on "Crashes" tab.
    self.Click("css=li[heading=Crashes]")

    # Check that all crashes were registered for this hunt.
    self.WaitUntil(self.AllTextsPresent,
                   [client_id.Basename() for client_id in client_ids])

    # Search for the C.0000000000000001 and select it.
    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.RequestAndGrantClientApproval("C.0000000000000001")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")
    self.Click("css=td:contains('0001')")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    # Open the "Advanced" dropdown.
    self.Click("css=li#HostAdvanced > a")
    self.WaitUntil(self.IsVisible, "css=a[grrtarget='client.crashes']")
    # Select list of crashes.
    self.Click("css=a[grrtarget='client.crashes']")

    self.WaitUntil(self.AllTextsPresent, [
        "C.0000000000000001", "Crash type", "aff4:/flows/", "CrashHandler",
        "Crash message", "Client killed during transaction"
    ])

  def testHuntClientCrashesTabShowsDatesInUTC(self):
    self.SetUpCrashedFlowInHunt()

    self.Open("/")

    # Go to hunt manager, select a hunt, open "Crashes" tab.
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.Click("css=td:contains('SampleHunt')")
    self.Click("css=li[heading=Crashes]")

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-hunt-crashes dt:contains('Timestamp') ~ dd:contains('UTC')")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
