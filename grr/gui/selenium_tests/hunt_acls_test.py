#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests Hunt ACLs."""

import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.server import access_control
from grr.server import foreman as rdf_foreman
from grr.server.aff4_objects import security
from grr.server.hunts import implementation
from grr.server.hunts import standard


class TestACLWorkflow(gui_test_lib.GRRSeleniumHuntTest):
  # Using an Unicode string for the test here would be optimal but Selenium
  # can't correctly enter Unicode text into forms.
  reason = "Felt like it!"

  def CreateSampleHunt(self, token=None):
    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client", attribute_regex="GRR"))
    ])

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.SampleHunt.__name__,
        client_rate=100,
        filename="TestFilename",
        client_rule_set=client_rule_set,
        token=token or self.token) as hunt:

      return hunt.session_id

  def testHuntACLWorkflow(self):
    hunt_id = self.CreateSampleHunt()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
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

    # This asks our user to approve the request.
    self.Type("css=grr-request-approval-dialog input[name=acl_approver]",
              self.token.username)
    self.Type("css=grr-request-approval-dialog input[name=acl_reason]",
              self.reason)
    self.Click(
        "css=grr-request-approval-dialog button[name=Proceed]:not([disabled])")

    # "Request Approval" dialog should go away
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.WaitForNotification("aff4:/users/%s" % self.token.username)
    self.Open("/")

    self.WaitUntil(lambda: self.GetText("notification_button") != "0")

    self.Click("notification_button")
    self.Click("css=td:contains('Please grant access to hunt')")

    self.WaitUntilContains("Grant access", self.GetText,
                           "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent,
                   "The user %s has requested" % self.token.username)

    # Hunt overview should be visible
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")

    self.Click("css=button:contains('Approve')")
    self.WaitUntil(self.IsTextPresent, "Approval granted.")

    self.WaitForNotification("aff4:/users/%s" % self.token.username)
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntil(lambda: self.GetText("notification_button") != "0")
    self.Click("notification_button")
    self.WaitUntil(self.GetText,
                   "css=td:contains('has granted you access to hunt')")
    self.Click("css=tr:contains('has granted you access') a")

    # Run SampleHunt (it should be selected by default).
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]:not([disabled])")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is insufficient - we need 2 approvers.
    self.WaitUntilContains("Requires 2 approvers for access.", self.GetText,
                           "css=grr-request-approval-dialog")

    # Lets add another approver.
    token = access_control.ACLToken(username="approver")
    security.HuntApprovalGrantor(
        subject_urn=hunt_id,
        reason=self.reason,
        delegate=self.token.username,
        token=token).Grant()

    self.WaitForNotification("aff4:/users/%s" % self.token.username)
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntil(lambda: self.GetText("notification_button") != "0")
    self.Click("notification_button")
    self.Click("css=tr:contains('has granted you access') a")
    # Wait for modal backdrop to go away.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    # Run SampleHunt (it should be selected by default).
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is still insufficient - one of the approvers should have
    # "admin" label.
    self.WaitUntilContains("At least 1 approver(s) should have 'admin' label.",
                           self.GetText, "css=grr-request-approval-dialog")

    # Let's make "approver" an admin.
    self.CreateAdminUser("approver")

    # Check if we see that the approval has already been granted.
    self.Open("/")
    self.Click("notification_button")

    self.Click("css=td:contains('Please grant access to hunt')")

    self.WaitUntil(self.IsTextPresent,
                   "This approval has already been granted!")

    # And try again
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
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
    # Create 2 hunts. Hunt1 by "otheruser" and hunt2 by us.
    # Both hunts will be approved by user "approver".
    hunt1_id = self.CreateSampleHunt(token=access_control.ACLToken(
        username="otheruser"))
    hunt2_id = self.CreateSampleHunt(token=access_control.ACLToken(
        username=self.token.username))
    self.CreateAdminUser("approver")

    token = access_control.ACLToken(username="otheruser")
    security.HuntApprovalRequestor(
        subject_urn=hunt1_id,
        reason=self.reason,
        approver="approver",
        token=token).Request()
    token = access_control.ACLToken(username=self.token.username)
    security.HuntApprovalRequestor(
        subject_urn=hunt2_id,
        reason=self.reason,
        approver="approver",
        token=token).Request()

    token = access_control.ACLToken(username="approver")
    security.HuntApprovalGrantor(
        subject_urn=hunt1_id,
        reason=self.reason,
        delegate="otheruser",
        token=token).Grant()
    token = access_control.ACLToken(username="approver")
    security.HuntApprovalGrantor(
        subject_urn=hunt2_id,
        reason=self.reason,
        delegate=self.token.username,
        token=token).Grant()

  def testHuntApprovalsArePerHunt(self):
    self.Create2HuntsForDifferentUsers()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

    #
    # Check that test user can't start/stop/modify hunt1.
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
    self.WaitUntil(self.IsTextPresent, "No approval found")

    self.Click("css=grr-request-approval-dialog button[name=Cancel]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt]:not([disabled])")

    # Modify hunt

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify this hunt")
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-modify-hunt-dialog label:contains('Client limit') ~ * input")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("name=Proceed")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.WaitUntil(self.IsTextPresent, "No approval found")

    self.Click("css=grr-request-approval-dialog button[name=Cancel]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    #
    # Check that test user can start/stop/modify hunt2.
    #
    self.Click(
        "css=tr:contains('SampleHunt') td:contains('%s')" % self.token.username)

    # Modify hunt

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify this hunt")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # Run hunt

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button disappears.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt started successfully")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=StopHunt]:not([disabled])")

    # Stop hunt

    # Click on Stop and wait for dialog again.
    self.Click("css=button[name=StopHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to stop this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt stopped successfully")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt]:not([disabled])")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
