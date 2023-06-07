#!/usr/bin/env python
"""Test the flow_management interface."""

from absl import app

from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestCrashView(gui_test_lib.GRRSeleniumHuntTest):
  """Tests the crash view."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def SetUpCrashedFlow(self):
    client = flow_test_lib.CrashClientMock(self.client_id)
    flow_test_lib.TestFlowHelper(
        flow_test_lib.FlowWithOneClientRequest.__name__,
        client,
        client_id=self.client_id,
        creator=self.test_username,
        check_flow_errors=False)

  def testOpeningCrashesOfUnapprovedClientRedirectsToHostInfoPage(self):
    client_id = self.SetupClient(0)
    self.Open("/legacy#/clients/%s/crashes" % client_id)

    # As we don't have an approval for the client, we should be
    # redirected to the host info page.
    self.WaitUntilEqual(
        "/legacy#/clients/%s/host-info" % client_id, self.GetCurrentUrlPath
    )
    self.WaitUntil(self.IsTextPresent,
                   "You do not have an approval for this client.")

  def testClientCrashedFlow(self):
    self.SetUpCrashedFlow()
    self.RequestAndGrantClientApproval(self.client_id)

    self.Open("/legacy")

    self.Type("client_query", self.client_id)
    self.Click("client_query_submit")

    self.WaitUntilEqual(self.client_id, self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('%s')" % self.client_id)
    self.WaitUntil(self.IsTextPresent, self.client_id)

    self.Click("css=a[grrtarget='client.flows']")
    self.WaitUntil(self.IsTextPresent,
                   flow_test_lib.FlowWithOneClientRequest.__name__)

    # Check that skull icon is in place.
    self.WaitUntil(self.IsElementPresent, "css=img[src$='skull-icon.png']")

    # Click on the crashed flow.
    self.Click("css=td:contains(FlowWithOneClientRequest)")

    # Check that "Flow Information" tab displays crash data.
    self.WaitUntil(self.AllTextsPresent, [
        "CLIENT_CRASHED",
        self.client_id,
        "Client crashed.",
    ])

  def SetUpCrashedFlowInHunt(self):
    client_ids = self.SetupClients(10)
    hunt_id = self.StartHunt()
    self.RunHuntWithClientCrashes(client_ids)

    return hunt_id, client_ids

  def testClientCrashedFlowInHunt(self):
    hunt_id, client_ids = self.SetUpCrashedFlowInHunt()

    self.Open("/legacy")

    # Go to hunt manager and select a hunt.
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)

    # Click on "Crashes" tab.
    self.Click("css=li[heading=Crashes]")

    # Check that all crashes were registered for this hunt.
    self.WaitUntil(self.AllTextsPresent, client_ids)

    # Search for the client and select it.
    self.Type("client_query", client_ids[0])
    self.Click("client_query_submit")

    self.RequestAndGrantClientApproval(client_ids[0])

    self.WaitUntilEqual(client_ids[0], self.GetText, "css=span[type=subject]")
    self.Click("css=td:contains('%s')" % client_ids[0])
    self.WaitUntil(self.IsTextPresent, client_ids[0])

    # Open the "Advanced" dropdown.
    self.Click("css=li#HostAdvanced > a")
    self.WaitUntil(self.IsVisible, "css=a[grrtarget='client.crashes']")
    # Select list of crashes.
    self.Click("css=a[grrtarget='client.crashes']")

    self.WaitUntil(self.AllTextsPresent, [
        client_ids[0], "Crash type", "Client Crash", "Crash message",
        "Client killed during transaction"
    ])

  def testHuntClientCrashesTabShowsDatesInUTC(self):
    hunt_id, _ = self.SetUpCrashedFlowInHunt()

    self.Open("/legacy")

    # Go to hunt manager, select a hunt, open "Crashes" tab.
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Crashes]")

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-hunt-crashes dt:contains('Timestamp') ~ dd:contains('UTC')")


if __name__ == "__main__":
  app.run(test_lib.main)
