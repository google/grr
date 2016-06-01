#!/usr/bin/env python
"""Test the flow_management interface."""


from grr.gui import runtests_test

from grr.lib import aff4
from grr.lib import flags
from grr.lib import hunts
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.server import foreman as rdf_foreman


class TestCrashView(test_lib.GRRSeleniumTest):
  """Tests the crash view."""

  client_id = rdf_client.ClientURN("C.0000000000000001")

  def SetUpCrashedFlow(self):
    client = test_lib.CrashClientMock(self.client_id, self.token)
    for _ in test_lib.TestFlowHelper("FlowWithOneClientRequest",
                                     client,
                                     client_id=self.client_id,
                                     token=self.token,
                                     check_flow_errors=False):
      pass

  def testClientCrashedFlow(self):
    with self.ACLChecksDisabled():
      self.SetUpCrashedFlow()
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")
    self.WaitUntil(self.IsTextPresent, "HostC.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.WaitUntil(self.IsTextPresent, "FlowWithOneClientRequest")

    # Check that skull icon is in place.
    self.WaitUntil(self.IsElementPresent, "css=img[src$='skull-icon.png']")

    # Click on the crashed flow.
    self.Click("css=td:contains(FlowWithOneClientRequest)")

    # Check that "Flow Information" tab displays crash data.
    self.WaitUntil(self.AllTextsPresent, [
        "CLIENT_CRASH", "aff4:/flows/", ":CrashHandler",
        "Client killed during transaction"
    ])

    # Check that client crash is present in global crashes list.
    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "Advanced")

    # Open the "Advanced" dropdown.
    self.Click("css=li#ManagementAdvanced > a")
    self.WaitUntil(self.IsVisible, "css=a:contains('All Clients Crashes')")
    # Check that needed data are displayed.
    self.Click("css=a:contains('All Clients Crashes')")
    self.WaitUntil(self.AllTextsPresent, [
        "Crash Details", "aff4:/flows/", ":CrashHandler",
        "Client killed during transaction"
    ])

    # Click on a session id link and check that we're redirected to a flow.
    self.Click("css=a:contains('%s/flows')" % self.client_id)
    self.WaitUntil(self.AllTextsPresent, [
        "Manage launched flows", "Flow Name", "Flow Information"
    ])

  def SetUpCrashedFlowInHunt(self):
    client_ids = [rdf_client.ClientURN("C.%016X" % i) for i in range(0, 10)]
    client_mocks = dict([(client_id, test_lib.CrashClientMock(client_id,
                                                              self.token))
                         for client_id in client_ids])

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 token=self.token) as hunt:
      hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)
    test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False, self.token)

    return client_ids

  def testClientCrashedFlowInHunt(self):
    with self.ACLChecksDisabled():
      client_ids = self.SetUpCrashedFlowInHunt()

    self.Open("/")

    # Open the "Advanced" dropdown.
    self.Click("css=li#ManagementAdvanced > a")
    self.WaitUntil(self.IsVisible, "css=a[grrtarget=clientCrashes]")

    # Check that all crashed are registered in "All Clients Crashes"
    self.Click("css=a[grrtarget=clientCrashes]")
    self.WaitUntil(self.AllTextsPresent, [client_id
                                          for client_id in client_ids])

    # Go to hunt manager and select a hunt.
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.Click("css=td:contains('SampleHunt')")

    # Click on "Crashes" tab.
    self.Click("css=li[heading=Crashes]")

    # Check that all crashes were registered for this hunt.
    self.WaitUntil(self.AllTextsPresent, [client_id
                                          for client_id in client_ids])

    # Search for the C.0000000000000001 and select it.
    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")
    self.Click("css=td:contains('0001')")
    self.WaitUntil(self.IsTextPresent, "HostC.0000000000000001")

    # Open the "Advanced" dropdown.
    self.Click("css=li#HostAdvanced > a")
    self.WaitUntil(self.IsVisible, "css=a[grrtarget='client.crashes']")
    # Select list of crashes.
    self.Click("css=a[grrtarget='client.crashes']")

    self.WaitUntil(self.AllTextsPresent, [
        "C.0000000000000001", "Crash Type", "aff4:/flows/", "CrashHandler",
        "Crash Message", "Client killed during transaction"
    ])

  def testHuntClientCrashesTabShowsDatesInUTC(self):
    with self.ACLChecksDisabled():
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
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
