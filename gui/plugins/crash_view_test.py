#!/usr/bin/env python
"""Test the flow_management interface."""


from grr.lib import aff4
from grr.lib import hunt_test
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestCrashView(test_lib.GRRSeleniumTest):
  client_id = rdfvalue.ClientURN("C.0000000000000001")

  def setUp(self):
    super(TestCrashView, self).setUp()
    self.hunts = hunt_test.HuntTest(methodName="run")
    self.hunts.setUp()

  def tearDown(self):
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                                token=self.token)
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.hunts.DeleteClients(10)

  def SetUpCrashedFlow(self):
    client = test_lib.CrashClientMock(self.client_id, self.token)
    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client, client_id=self.client_id,
        pathspec=rdfvalue.PathSpec(path="/", pathtype=1), token=self.token,
        check_flow_errors=False):
      pass

  def testClientCrashedFlow(self):
    self.SetUpCrashedFlow()

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

    self.Click("css=a:contains('Manage launched flows')")
    self.WaitUntil(self.IsTextPresent, "ListDirectory")

    # Check that skull icon is in place.
    self.WaitUntil(self.IsElementPresent,
                   "css=img[src='/static/images/skull-icon.png']")

    # Click on the crashed flow.
    self.Click("css=td:contains(ListDirectory)")

    # Check that "Flow Information" tab displays crash data.
    self.WaitUntil(self.IsTextPresent, "GRRFlow")
    self.WaitUntil(self.IsTextPresent, "CLIENT_CRASH")
    self.WaitUntil(self.IsTextPresent, "aff4:/flows/W:CrashHandler")
    self.WaitUntil(self.IsTextPresent, "Client killed during transaction")

    # Check that client crash is present in global crashes list.
    self.Open("/")
    self.WaitUntil(self.IsTextPresent, "All Clients Crashes")

    # Open the "Advanced" dropdown.
    self.Click("css=a[href='#ManagementAdvanced']")
    self.WaitUntil(self.IsVisible, "css=a:contains('All Clients Crashes')")
    # Check that needed data are displayed.
    self.Click("css=a:contains('All Clients Crashes')")
    self.WaitUntil(self.IsTextPresent, "Crash Details")
    self.WaitUntil(self.IsTextPresent, "aff4:/flows/W:CrashHandler")
    self.WaitUntil(self.IsTextPresent, "Client killed during transaction")

    # Click on a session id link and check that we're redirected to a flow.
    self.Click("css=a:contains('%s/flows')" % self.client_id)
    self.WaitUntil(self.IsTextPresent, "Manage launched flows")
    self.WaitUntil(self.IsTextPresent, "Flow Name")
    self.WaitUntil(self.IsTextPresent, "Flow Information")

  def SetUpCrashedFlowInHunt(self):
    client_ids = [rdfvalue.ClientURN("C.%016X" % i) for i in range(0, 10)]
    for client_id in client_ids:
      test_lib.ClientFixture(client_id, token=self.token)
    client_mocks = dict([(client_id, test_lib.CrashClientMock(
        client_id, self.token)) for client_id in client_ids])

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)
    test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False, self.token)

    return client_ids

  def testClientCrashedFlowInHunt(self):
    client_ids = self.SetUpCrashedFlowInHunt()

    self.Open("/")

    # Open the "Advanced" dropdown.
    self.Click("css=a[href='#ManagementAdvanced']")
    self.WaitUntil(self.IsVisible, "css=a[grrtarget=GlobalCrashesRenderer]")

    # Check that all crashed are registered in "All Clients Crashes"
    self.Click("css=a[grrtarget=GlobalCrashesRenderer]")
    for client_id in client_ids:
      self.WaitUntil(self.IsTextPresent, client_id)

    # Go to hunt manager and select a hunt.
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.Click("css=td:contains('SampleHunt')")

    # Click on "Crashes" tab.
    self.WaitUntil(self.IsElementPresent,
                   "css=a[renderer=HuntCrashesRenderer]")
    self.Click("css=a[renderer=HuntCrashesRenderer]")

    # Check that all crashes were registered for this hunt.
    for client_id in client_ids:
      self.WaitUntil(self.IsTextPresent, client_id)

    # Search for the C.0000000000000001 and select it.
    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")
    self.Click("css=td:contains('0001')")
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

    # Open the "Advanced" dropdown.
    self.Click("css=a[href='#HostAdvanced']")
    self.WaitUntil(self.IsVisible, "css=a[grrtarget=ClientCrashesRenderer]'")
    # Select list of crashes.
    self.Click("css=a[grrtarget=ClientCrashesRenderer]'")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")
    self.WaitUntil(self.IsTextPresent, "Crash Type")
    self.WaitUntil(self.IsTextPresent, "aff4:/flows/W:CrashHandler")
    self.WaitUntil(self.IsTextPresent, "Crash Message")
    self.WaitUntil(self.IsTextPresent, "Client killed during transaction")
