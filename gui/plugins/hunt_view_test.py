#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test the hunt_view interface."""



import traceback

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flow
from grr.lib import hunt_test
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


def CreateHunts():
  """Create some test hunts."""
  test_hunt = hunt_test.HuntTest(methodName="run")
  test_hunt.setUp()
  return test_hunt


class TestHuntView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  reason = "Felt like it!"

  @staticmethod
  def SetUp():
    result = TestHuntView(methodName="run")
    result.setUp()
    result.CreateSampleHunt()

    return result

  def setUp(self):
    super(TestHuntView, self).setUp()
    self.hunts = CreateHunts()

  def tearDown(self):
    self.UninstallACLChecks()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                                token=self.token)
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.hunts.DeleteClients(10)

  def CreateSampleHunt(self, stopped=False):
    self.client_ids = self.hunts.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])

    if stopped:
      hunt.WriteToDataStore()
    else:
      hunt.Run()

      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                                  token=self.token)
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)
      foreman.Close()

    return hunt

  def CreateGenericHuntWithCollection(self):
    self.client_ids = self.hunts.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt("GenericHunt", collect_replies=True,
                                   token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])

    hunt.state.collection.Add(rdfvalue.RDFURN("aff4:/sample/1"))
    hunt.state.collection.Add(rdfvalue.RDFURN(
        "aff4:/C.0000000000000001/fs/os/c/bin/bash"))
    hunt.state.collection.Add(rdfvalue.RDFURN("aff4:/sample/3"))

    hunt.WriteToDataStore()

    return hunt

  def SetupTestHuntView(self):
    # Create some clients and a hunt to view.
    hunt = self.CreateSampleHunt()
    hunt.Close()

    # Run the hunt.
    client_mock = self.hunts.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt = aff4.FACTORY.Open(hunt.session_id, token=self.token, mode="rw",
                             age=aff4.ALL_TIMES)

    hunt.LogResult(self.client_ids[2], "Result 1")
    # Log an error just with some random traceback.
    hunt.LogClientError(self.client_ids[1], "Client Error 1",
                        traceback.format_exc())

    started = hunt.GetValuesForAttribute(hunt.Schema.CLIENTS)
    self.assertEqual(len(set(started)), 10)
    hunt.Close()

  def CheckState(self, state):
    self.WaitUntil(self.IsElementPresent, "css=div[state=\"%s\"]" % state)

  def testHuntView(self):
    """Test that we can see all the hunt data."""
    self.SetupTestHuntView()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Client Count")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    # Click the Log Tab.
    self.Click("css=a[renderer=HuntLogRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntLogRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Result 1")

    # Click the Error Tab.
    self.Click("css=a[renderer=HuntErrorRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntErrorRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Client Error 1")

    # Click the Rules Tab.
    self.Click("css=a[renderer=HuntRuleRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntRuleRenderer_]")
    self.WaitUntil(self.IsTextPresent, "GRR client")

  def testToolbarStateForStoppedHunt(self):
    self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Client Count")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    self.assertTrue(self.IsElementPresent,
                    "css=button[name=RunHunt][disabled!='']")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=PauseHunt][disabled='']")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=ModifyHunt][disabled='']")

  def testToolbarStateForRunningHunt(self):
    self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Client Count")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    self.assertTrue(self.IsElementPresent,
                    "css=button[name=RunHunt][disabled='']")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=PauseHunt][disabled!='']")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=ModifyHunt][disabled='']")

  def testRunHuntWithoutACLChecks(self):
    self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Check the hunt is not in a running state.
    self.CheckState("stopped")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Client Count")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    # Click on Run button and check that dialog appears.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click Cancel and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt started successfully!")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=Proceed][disabled!='']")

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    # Check the hunt is in a running state.
    self.CheckState("RUNNING")

  def CreateApproval(self, session_id):
    # Create the approval and approve it.
    token = access_control.ACLToken(username="test")
    token.supervisor = True
    flow.GRRFlow.StartFlow(None, "RequestHuntApprovalFlow",
                           hunt_id=rdfvalue.RDFURN(session_id),
                           reason=self.reason,
                           approver="approver",
                           token=token)

    self.MakeUserAdmin("approver")
    token = access_control.ACLToken(username="approver")
    token.supervisor = True
    flow.GRRFlow.StartFlow(None, "GrantHuntApprovalFlow",
                           hunt_urn=session_id, reason=self.reason,
                           delegate="test",
                           token=token)

  def testRunHuntWithACLChecks(self):
    hunt = self.CreateSampleHunt(stopped=True)
    self.InstallACLChecks()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Click on Run button and check that dialog appears.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent,
                   "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    self.CreateApproval(hunt.session_id)

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt started successfully!")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=Proceed][disabled!='']")

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    # Check the hunt is in a running state.
    self.CheckState("RUNNING")

  def testPauseHuntWithoutACLChecks(self):
    self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Check the hunt is in a running state.
    self.CheckState("RUNNING")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Client Count")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    # Click on Pause button and check that dialog appears.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click Cancel and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # Click on Pause and wait for dialog again.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt paused successfully!")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=Proceed][disabled!='']")

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    # Check the hunt is in a running state.
    self.CheckState("stopped")

  def testPauseHuntWithACLChecks(self):
    hunt = self.CreateSampleHunt(stopped=False)
    self.InstallACLChecks()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Click on Pause button and check that dialog appears.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent,
                   "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    self.CreateApproval(hunt.session_id)

    # Click on Pause and wait for dialog again.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt paused successfully")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=Proceed][disabled!='']")

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    # Check the hunt is in a running state.
    self.CheckState("stopped")

  def testModifyHuntWithACLChecks(self):
    hunt = self.CreateSampleHunt(stopped=True)
    self.InstallACLChecks()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")

    self.Type("css=input[name=client_limit]", "4483")
    self.Type("css=input[name=expiry_time]", "5m")

    # Click on Proceed.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # Now create an approval.
    self.CreateApproval(hunt.session_id)

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")

    self.Type("css=input[name=client_limit]", "4483")
    self.Type("css=input[name=expiry_time]", "5m")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=Proceed][disabled!='']")

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.WaitUntil(self.IsTextPresent, "4483")

  def SetupHuntDetailView(self):
    """Create some clients and a hunt to view."""
    hunt = self.CreateSampleHunt()
    # Run the hunt.
    client_mock = self.hunts.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt.LogClientError(self.client_ids[1], "Client Error 1",
                        traceback.format_exc())
    hunt.Flush()

  def testHuntDetailView(self):
    """Test the detailed client view works."""
    self.SetupHuntDetailView()

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.Click("css=td:contains('SampleHunt')")

    # Click the Overview Tab then the Details Link.
    self.Click("css=a[renderer=HuntOverviewRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntOverviewRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")
    self.Click("css=a[id^=ViewHuntDetails_]")
    self.WaitUntil(self.IsTextPresent, "Viewing Hunt aff4:/hunts/")

    self.WaitUntil(self.IsTextPresent, "COMPLETED")
    self.WaitUntil(self.IsTextPresent, "BAD")

    # Select the first client which should have errors.
    self.Click("css=td:contains('%s')" % self.client_ids[1].Basename())
    self.WaitUntil(self.IsElementPresent,
                   "css=div[id^=HuntClientOverviewRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Last Checkin")

    self.Click("css=a:[renderer=HuntLogRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntLogRenderer_]")
    self.WaitUntil(self.IsTextPresent, "No entries")

    self.Click("css=a:[renderer=HuntErrorRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntErrorRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Client Error 1")

    self.Click("css=a:[renderer=HuntHostInformationRenderer]")
    self.WaitUntil(self.IsElementPresent,
                   "css=div[id^=HuntHostInformationRenderer_]")

    self.WaitUntil(self.IsTextPresent, "CLIENT_INFO")
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

  def testHuntResultsView(self):
    self.CreateGenericHuntWithCollection()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=a[renderer=HuntResultsRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntResultsRenderer_]")

    self.assertTrue(self.IsTextPresent("aff4:/sample/1"))
    self.assertTrue(self.IsTextPresent(
        "aff4:/C.0000000000000001/fs/os/c/bin/bash"))
    self.assertTrue(self.IsTextPresent("aff4:/sample/3"))

    self.Click("link=aff4:/C.0000000000000001/fs/os/c/bin/bash")
    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a:contains('Browse Virtual Filesystem')")

  def testHuntStatsView(self):
    self.SetupTestHuntView()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.Click("css=td:contains('SampleHunt')")

    self.WaitUntil(self.IsElementPresent,
                   "css=a[renderer=HuntStatsRenderer]")
    # Click the Stats tab.
    self.Click("css=a[renderer=HuntStatsRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntStatsRenderer_]")

    self.assertTrue(self.IsTextPresent("Total number of clients"))
    self.assertTrue(self.IsTextPresent("20"))

    self.assertTrue(self.IsTextPresent("User CPU mean"))
    self.assertTrue(self.IsTextPresent("2.8"))

    self.assertTrue(self.IsTextPresent("User CPU stdev"))
    self.assertTrue(self.IsTextPresent("3.4"))

    self.assertTrue(self.IsTextPresent("System CPU mean"))
    self.assertTrue(self.IsTextPresent("5.5"))

    self.assertTrue(self.IsTextPresent("System CPU stdev"))
    self.assertTrue(self.IsTextPresent("6.8"))

    self.assertTrue(self.IsTextPresent("Network bytes sent mean"))
    self.assertTrue(self.IsTextPresent("8.3"))

    self.assertTrue(self.IsTextPresent("Network bytes sent stdev"))
    self.assertTrue(self.IsTextPresent("10.3"))
