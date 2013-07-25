#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test the hunt_view interface."""



import traceback

from grr.gui import runtests_test

from grr.lib import aff4
from grr.lib import flags
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestHuntView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  reason = "Felt like it!"

  def CreateSampleHunt(self, stopped=False):
    self.client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt(
        "GenericHunt",
        flow_name="GetFile",
        args=rdfvalue.Dict(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        output_plugins=[],
        token=self.token)

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
    self.client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt(
        "GenericHunt", output_plugins=[("CollectionPlugin", {})],
        token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])

    collection = hunt.state.output_objects[0].collection
    collection.Add(rdfvalue.RDFURN("aff4:/sample/1"))
    collection.Add(rdfvalue.RDFURN(
        "aff4:/C.0000000000000001/fs/os/c/bin/bash"))
    collection.Add(rdfvalue.RDFURN("aff4:/sample/3"))

    hunt.WriteToDataStore()

    return hunt

  def SetupTestHuntView(self):
    # Create some clients and a hunt to view.
    hunt = self.CreateSampleHunt()
    hunt.Close()

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
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
    with self.ACLChecksDisabled():
      self.SetupTestHuntView()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

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
    with self.ACLChecksDisabled():
      self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Client Count")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RunHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=PauseHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt]:not([disabled])")

  def testToolbarStateForRunningHunt(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Client Count")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RunHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=PauseHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt][disabled]")

  def testRunHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

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

    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.session_id)

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt started successfully!")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    # Check the hunt is in a running state.
    self.CheckState("RUNNING")

  def testPauseHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

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

    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.session_id)

    # Click on Pause and wait for dialog again.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt paused successfully")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    # Check the hunt is in a running state.
    self.CheckState("stopped")

  def testModifyHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

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
    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.session_id)

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")

    self.Type("css=input[name=client_limit]", "4483")
    self.Type("css=input[name=expiry_time]", "5m")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, "4483")

  def SetupHuntDetailView(self, failrate=2):
    """Create some clients and a hunt to view."""
    hunt = self.CreateSampleHunt()
    # Run the hunt.
    client_mock = test_lib.SampleHuntMock(failrate=failrate)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt.LogClientError(self.client_ids[1], "Client Error 1",
                        traceback.format_exc())
    hunt.Flush()

  def testHuntDetailView(self):
    """Test the detailed client view works."""
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=-1)

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Overview Tab then the Details Link.
    self.Click("css=a[renderer=HuntOverviewRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntOverviewRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")
    self.Click("css=a[id^=ViewHuntDetails_]")
    self.WaitUntil(self.IsTextPresent, "Viewing Hunt aff4:/hunts/")

    self.WaitUntil(self.IsTextPresent, "COMPLETED")

    # Select the first client which should have errors.
    self.Click("css=td:contains('%s')" % self.client_ids[1].Basename())
    self.WaitUntil(self.IsElementPresent,
                   "css=div[id^=HuntClientOverviewRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Last Checkin")

    self.Click("css=a:[renderer=HuntLogRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntLogRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Flow GetFile completed.")

    self.Click("css=a:[renderer=HuntErrorRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntErrorRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Client Error 1")

    self.Click("css=a:[renderer=HuntHostInformationRenderer]")
    self.WaitUntil(self.IsElementPresent,
                   "css=div[id^=HuntHostInformationRenderer_]")

    self.WaitUntil(self.IsTextPresent, "CLIENT_INFO")
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

  def testHuntResultsView(self):
    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=a[renderer=HuntResultsRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntResultsRenderer_]")

    self.WaitUntil(self.IsTextPresent, "aff4:/sample/1")
    self.WaitUntil(self.IsTextPresent,
                   "aff4:/C.0000000000000001/fs/os/c/bin/bash")
    self.WaitUntil(self.IsTextPresent, "aff4:/sample/3")

    with self.ACLChecksDisabled():
      self.GrantClientApproval("C.0000000000000001")

    self.Click("link=aff4:/C.0000000000000001/fs/os/c/bin/bash")
    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a:contains('Browse Virtual Filesystem')")

  def testHuntStatsView(self):
    with self.ACLChecksDisabled():
      self.SetupTestHuntView()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    self.WaitUntil(self.IsElementPresent,
                   "css=a[renderer=HuntStatsRenderer]")
    # Click the Stats tab.
    self.Click("css=a[renderer=HuntStatsRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntStatsRenderer_]")

    self.assertTrue(self.IsTextPresent("Total number of clients"))
    self.assertTrue(self.IsTextPresent("10"))

    self.assertTrue(self.IsTextPresent("User CPU mean"))
    self.assertTrue(self.IsTextPresent("5.5"))

    self.assertTrue(self.IsTextPresent("User CPU stdev"))
    self.assertTrue(self.IsTextPresent("2.9"))

    self.assertTrue(self.IsTextPresent("System CPU mean"))
    self.assertTrue(self.IsTextPresent("11"))

    self.assertTrue(self.IsTextPresent("System CPU stdev"))
    self.assertTrue(self.IsTextPresent("5.7"))

    self.assertTrue(self.IsTextPresent("Network bytes sent mean"))
    self.assertTrue(self.IsTextPresent("16.5"))

    self.assertTrue(self.IsTextPresent("Network bytes sent stdev"))
    self.assertTrue(self.IsTextPresent("8.6"))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
