#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests the access control authorization workflow."""


from grr.lib import access_control
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestACLWorkflow(test_lib.GRRSeleniumTest):
  """Tests the access control workflow."""

  # Using an Unicode string for the test here would be optimal but Selenium
  # can't correctly enter Unicode text into forms.
  reason = "Felt like it!"

  def CreateSampleHunt(self, token=None):
    hunt = hunts.SampleHunt(token=token or self.token)

    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])

    hunt.WriteToDataStore()
    return hunt

  def setUp(self):
    # super_token will be used for StartFlow calls to replicate the way
    # gatekeeper works. When the gatekeeper is used, it executes flows
    # with supervisor=True
    super(TestACLWorkflow, self).setUp()

  def tearDown(self):
    self.UninstallACLChecks()
    super(TestACLWorkflow, self).tearDown()

  def testClientACLWorkflow(self):
    self.InstallACLChecks()

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsElementPresent,
                   "css=h3:contains('Create a new approval')")

    # This asks the user "test" (which is us) to approve the request.
    self.Type("css=input[id=acl_approver]", "test")
    self.Type("css=input[id=acl_reason]", self.reason)
    self.Click("acl_dialog_submit")

    # User test logs in as an approver.
    self.Open("/")
    self.WaitUntilEqual("1", self.GetText, "notification_button")

    self.Click("notification_button")
    self.Click("css=td:contains('grant access')")

    self.WaitUntilContains("Grant Access for GRR Use",
                           self.GetText, "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent, "The user test has requested")

    self.Click("css=button:contains('Approve')")

    self.WaitUntil(self.IsTextPresent,
                   "You have granted access for C.0000000000000001 to test")

    # Now test starts up
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")

    self.Click("notification_button")

    self.WaitUntil(self.GetText, "css=td:contains('has approved')")
    self.Click("css=td:contains('has approved')")

    # This is insufficient - we need 2 approvers.
    self.WaitUntilContains("Requires 2 approvers for access.",
                           self.GetText, "css=div#acl_form")

    # Lets add another approver.
    token = access_control.ACLToken(username="approver")
    flow.FACTORY.StartFlow("C.0000000000000001", "GrantClientApprovalFlow",
                           reason=self.reason, delegate="test",
                           token=token)

    # Try again:
    self.Open("/")

    self.Click("notification_button")

    self.Click("css=td:contains('has approved')")

    self.Click("css=span:contains('fs')")

    # This is ok - it should work now
    self.WaitUntilContains("aff4:/C.0000000000000001/fs",
                           self.GetText, "css=h3:contains('fs')")


  def testHuntACLWorkflow(self):
    hunt = self.CreateSampleHunt()

    self.InstallACLChecks()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select a Hunt.
    self.Click("css=td:contains('SampleHunt')")

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsElementPresent,
                   "css=h3:contains('Create a new approval')")

    # This asks the user "test" (which is us) to approve the request.
    self.Type("css=input[id=acl_approver]", "test")
    self.Type("css=input[id=acl_reason]", self.reason)
    self.Click("acl_dialog_submit")

    # "Request Approval" dialog should go away
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    self.Open("/")
    self.WaitUntilEqual("1", self.GetText, "notification_button")

    self.Click("notification_button")
    self.Click("css=td:contains('grant permission to run a hunt')")

    self.WaitUntilContains("Grant Access for GRR Use",
                           self.GetText, "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent, "The user test has requested")

    # Hunt overview should be visible
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")
    self.WaitUntil(self.IsTextPresent, "Client Count")

    self.Click("css=button:contains('Approve')")
    self.WaitUntil(self.IsTextPresent,
                   "You have granted access for %s to test" % hunt.session_id)

    # Now test starts up
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")
    self.Click("notification_button")
    self.WaitUntil(self.GetText,
                   "css=td:contains('has approved your permission')")
    self.Click("css=tr:contains('has approved your permission') a")

    # Run SampleHunt (it should be selected by default).
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is insufficient - we need 2 approvers.
    self.WaitUntilContains("Requires 2 approvers for access.",
                           self.GetText, "css=div#acl_form")

    # Lets add another approver.
    token = access_control.ACLToken(username="approver")
    flow.FACTORY.StartFlow(None, "GrantHuntApprovalFlow",
                           hunt_urn=hunt.session_id, reason=self.reason,
                           delegate="test",
                           token=token)

    # Now test starts up
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")
    self.Click("notification_button")
    self.Click("css=tr:contains('has approved your permission') a")
    # Wait for modal backdrop to go away.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Run SampleHunt (it should be selected by default).
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is still insufficient - one of the approvers should have
    # "admin" label.
    self.WaitUntilContains("At least one approver should have 'admin' label.",
                           self.GetText, "css=div#acl_form")

    # Let's make "approver" an admin.
    self.MakeUserAdmin("approver")

    # And try again
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Select and run SampleHunt.
    self.Click("css=td:contains('SampleHunt')")

    # Run SampleHunt (it should be selected by default).
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")
    # Click on "Proceed" and wait for the success status message.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt started successfully!")

  def Create2HuntsForDifferentUsers(self):
    # Create 2 hunts. Hunt1 by "otheruser" and hunt2 by "test".
    # Both hunts will be approved by user "approver".
    hunt1 = self.CreateSampleHunt(
        token=access_control.ACLToken(username="otheruser"))
    hunt2 = self.CreateSampleHunt(
        token=access_control.ACLToken(username="test"))

    self.InstallACLChecks()
    self.MakeUserAdmin("approver")

    token = access_control.ACLToken(username="otheruser")
    flow.FACTORY.StartFlow(None, "RequestHuntApprovalFlow",
                           hunt_id=hunt1.session_id,
                           reason=self.reason,
                           approver="approver",
                           token=token)
    token = access_control.ACLToken(username="test")
    flow.FACTORY.StartFlow(None, "RequestHuntApprovalFlow",
                           hunt_id=hunt2.session_id,
                           reason=self.reason,
                           approver="approver",
                           token=token)

    token = access_control.ACLToken(username="approver")
    flow.FACTORY.StartFlow(None, "GrantHuntApprovalFlow",
                           hunt_urn=hunt1.session_id, reason=self.reason,
                           delegate="otheruser",
                           token=token)
    token = access_control.ACLToken(username="approver")
    flow.FACTORY.StartFlow(None, "GrantHuntApprovalFlow",
                           hunt_urn=hunt2.session_id, reason=self.reason,
                           delegate="test",
                           token=token)

    return (hunt1, hunt2)

  def testHuntApprovalsArePerHunt(self):
    self.Create2HuntsForDifferentUsers()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    #
    # Check that test user can't start/pause/modify hunt1.
    #
    self.Click("css=tr:contains('SampleHunt') td:contains('otheruser')")

    # Run hunt

    # Click on Run button and check that dialog appears.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.WaitUntil(self.IsTextPresent, "No approvals available")

    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt][!disabled]")

    # Modify hunt

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")
    self.WaitUntil(self.IsElementPresent, "css=input[name=client_limit]")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("name=Proceed")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.WaitUntil(self.IsTextPresent, "No approvals available")

    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    #
    # Check that test user can start/pause/modify hunt2.
    #
    self.Click("css=tr:contains('SampleHunt') td:contains('test')")

    # Run hunt

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt started successfully")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=Proceed][disabled!='']")

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=PauseHunt][!disabled]")

    # Pause hunt

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
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt][!disabled]")

    # Modify hunt

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Modify a hunt")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertTrue(self.IsElementPresent,
                    "css=button[name=Proceed][disabled!='']")

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")
