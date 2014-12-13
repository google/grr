#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests the access control authorization workflow."""


import re
import time
import urlparse

from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import cronjobs


class TestACLWorkflow(test_lib.GRRSeleniumTest):
  """Tests the access control workflow."""

  # Using an Unicode string for the test here would be optimal but Selenium
  # can't correctly enter Unicode text into forms.
  reason = "Felt like it!"

  def CreateSampleHunt(self, token=None):
    with hunts.GRRHunt.StartHunt(
        hunt_name="SampleHunt",
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        token=token or self.token) as hunt:

      return hunt.session_id

  def WaitForNotification(self, user):
    sleep_time = 0.2
    iterations = 50
    for _ in xrange(iterations):
      try:
        fd = aff4.FACTORY.Open(user, "GRRUser", mode="r", ignore_cache=True,
                               token=self.token)
        pending_notifications = fd.Get(fd.Schema.PENDING_NOTIFICATIONS)
        if pending_notifications:
          return
      except IOError:
        pass
      time.sleep(sleep_time)
    self.fail("Notification for user %s never sent." % user)

  def testClientACLWorkflow(self):
    self.Open("/")

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
    self.ClickUntilNotVisible("acl_dialog_submit")

    self.WaitForNotification("aff4:/users/test")
    # User test logs in as an approver.
    self.Open("/")

    self.WaitUntilEqual("1", self.GetText, "notification_button")

    self.Click("notification_button")

    self.ClickUntilNotVisible(
        "css=td:contains('grant access to GRR client')")

    self.WaitUntilContains("Grant Access for GRR Use",
                           self.GetText, "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent, "The user test has requested")

    self.Click("css=button:contains('Approve')")

    self.WaitUntil(self.IsTextPresent,
                   "You have granted access for C.0000000000000001 to test")

    self.WaitForNotification("aff4:/users/test")
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")

    self.Click("notification_button")

    self.ClickUntilNotVisible("css=td:contains('has granted you access')")

    # This is insufficient - we need 2 approvers.
    self.WaitUntilContains("Requires 2 approvers for access.",
                           self.GetText, "css=div#acl_form")

    # Lets add another approver.
    token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(client_id="C.0000000000000001",
                           flow_name="GrantClientApprovalFlow",
                           reason=self.reason, delegate="test",
                           subject_urn=rdfvalue.ClientURN("C.0000000000000001"),
                           token=token)

    # Try again:
    self.Open("/")

    self.Click("notification_button")

    self.ClickUntilNotVisible("css=td:contains('has granted you access')")

    self.Click("css=span:contains('fs')")

    # This is ok - it should work now
    self.WaitUntilContains("aff4:/C.0000000000000001/fs",
                           self.GetText, "css=h3:contains('fs')")

    # One email for the original request and one for each approval.
    self.assertEqual(len(self.emails_sent), 3)

  def testRecentReasonBox(self):
    test_reason = u"ástæða"
    self.Open("/")
    with self.ACLChecksDisabled():
      token = access_control.ACLToken(
          username="test",
          reason=test_reason)
      self.GrantClientApproval("C.0000000000000006", token=token)

    self.Type("client_query", "0006")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000006",
                        self.GetText, "css=span[type=subject]")

    # Choose client 6
    self.Click("css=td:contains('0006')")

    self.WaitUntil(self.IsTextPresent, u"Access reason: %s" % test_reason)

    # By now we should have a recent reason set, let's see if it shows up in the
    # ACL dialog.

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsElementPresent,
                   "css=h3:contains('Create a new approval')")

    options = self.GetText("css=select[id=acl_recent_reasons]").split("\n")
    self.assertEqual(len(options), 2)
    self.assertEqual(options[0].strip(), "Enter New Reason...")
    self.assertEqual(options[1].strip(), test_reason)

    # The reason text box should be there and enabled.
    element = self.GetElement("css=input[id=acl_reason]")
    self.assertTrue(element.is_enabled())

    self.Select("css=select[id=acl_recent_reasons]", test_reason)

    # Make sure clicking the recent reason greys out the reason text box.
    element = self.GetElement("css=input[id=acl_reason]")
    self.assertFalse(element.is_enabled())

    # Ok now submit this.
    self.Type("css=input[id=acl_approver]", "test")
    self.ClickUntilNotVisible("acl_dialog_submit")

    # And make sure the approval was created...
    fd = aff4.FACTORY.Open("aff4:/ACL/C.0000000000000001/test",
                           token=self.token)
    approvals = list(fd.ListChildren())

    self.assertEqual(len(approvals), 1)

    # ... using the correct reason.
    self.assertEqual(
        utils.SmartUnicode(approvals[0].Basename().decode("base64")),
        test_reason)

  def testHuntACLWorkflow(self):
    with self.ACLChecksDisabled():
      hunt_id = self.CreateSampleHunt()

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

    self.WaitForNotification("aff4:/users/test")
    self.Open("/")
    self.WaitUntilEqual("1", self.GetText, "notification_button")

    self.Click("notification_button")
    self.ClickUntilNotVisible(
        "css=td:contains('Please grant access to hunt')")

    self.WaitUntilContains("Grant Access for GRR Use",
                           self.GetText, "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent, "The user test has requested")

    # Hunt overview should be visible
    self.WaitUntil(self.IsTextPresent, "SampleHunt")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")

    self.Click("css=button:contains('Approve')")
    self.WaitUntil(self.IsTextPresent,
                   "You have granted access for %s to test" % hunt_id)

    self.WaitForNotification("aff4:/users/test")
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")
    self.Click("notification_button")
    self.WaitUntil(self.GetText,
                   "css=td:contains('has granted you access to hunt')")
    self.ClickUntilNotVisible(
        "css=tr:contains('has granted you access') a")

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
    flow.GRRFlow.StartFlow(flow_name="GrantHuntApprovalFlow",
                           subject_urn=hunt_id, reason=self.reason,
                           delegate="test",
                           token=token)

    self.WaitForNotification("aff4:/users/test")
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")
    self.Click("notification_button")
    self.ClickUntilNotVisible(
        "css=tr:contains('has granted you access') a")
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
    self.WaitUntilContains("At least 1 approver(s) should have 'admin' label.",
                           self.GetText, "css=div#acl_form")

    # Let's make "approver" an admin.
    with self.ACLChecksDisabled():
      self.CreateAdminUser("approver")

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
    with self.ACLChecksDisabled():
      hunt1_id = self.CreateSampleHunt(
          token=access_control.ACLToken(username="otheruser"))
      hunt2_id = self.CreateSampleHunt(
          token=access_control.ACLToken(username="test"))
      self.CreateAdminUser("approver")

    token = access_control.ACLToken(username="otheruser")
    flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                           subject_urn=hunt1_id,
                           reason=self.reason,
                           approver="approver",
                           token=token)
    token = access_control.ACLToken(username="test")
    flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                           subject_urn=hunt2_id,
                           reason=self.reason,
                           approver="approver",
                           token=token)

    token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(flow_name="GrantHuntApprovalFlow",
                           subject_urn=hunt1_id, reason=self.reason,
                           delegate="otheruser",
                           token=token)
    token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(flow_name="GrantHuntApprovalFlow",
                           subject_urn=hunt2_id, reason=self.reason,
                           delegate="test",
                           token=token)

  def testHuntApprovalsArePerHunt(self):
    with self.ACLChecksDisabled():
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
                   "css=button[name=ModifyHunt]:not([disabled])")

    # Modify hunt

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")
    self.WaitUntil(self.IsElementPresent, "css=input[id=v_-client_limit]")

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
    self.assertTrue(self.IsElementPresent(
        "css=button[name=Proceed][disabled!='']"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=PauseHunt]:not([disabled])")

    # Pause hunt

    # Click on Pause and wait for dialog again.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt paused successfully")
    self.assertTrue(self.IsElementPresent(
        "css=button[name=Proceed][disabled!='']"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt]:not([disabled])")

    # Modify hunt

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Modify a hunt")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertTrue(self.IsElementPresent(
        "css=button[name=Proceed][disabled!='']"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

  def testCronJobACLWorkflow(self):
    with self.ACLChecksDisabled():
      cronjobs.ScheduleSystemCronFlows(token=self.token)
      cronjobs.CRON_MANAGER.DisableJob(
          rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    # Open up and click on Cron Job Viewer.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageCron]")

    # Select a cron job
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")
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

    self.Click("css=td:contains('Please grant access to a cron job')")

    self.WaitUntilContains("Grant Access for GRR Use",
                           self.GetText, "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent, "The user test has requested")

    # Cron job overview should be visible
    self.WaitUntil(self.IsTextPresent, "aff4:/cron/OSBreakDown")
    self.WaitUntil(self.IsTextPresent, "CRON_ARGS")

    self.Click("css=button:contains('Approve')")
    self.WaitUntil(self.IsTextPresent,
                   "You have granted access for aff4:/cron/OSBreakDown to test")

    # Now test starts up
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")
    self.Click("notification_button")
    self.WaitUntil(self.GetText,
                   "css=td:contains('has granted you access to "
                   "a cron job')")
    self.Click("css=tr:contains('has granted you access') a")

    # Enable OSBreakDown cron job (it should be selected by default).
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable and wait for dialog again.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is insufficient - we need 2 approvers.
    self.WaitUntilContains("Requires 2 approvers for access.",
                           self.GetText, "css=div#acl_form")

    # Lets add another approver.
    token = access_control.ACLToken(username="approver")
    flow.GRRFlow.StartFlow(
        flow_name="GrantCronJobApprovalFlow",
        subject_urn=rdfvalue.RDFURN("aff4:/cron/OSBreakDown"),
        reason=self.reason, delegate="test", token=token)

    # Now test starts up
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1", self.GetText, "notification_button")
    self.Click("notification_button")
    self.Click("css=tr:contains('has granted you access') a")
    # Wait for modal backdrop to go away.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    self.WaitUntil(self.IsTextPresent, "OSBreakDown")

    # Enable OSBreakDown cron job (it should be selected by default).
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is still insufficient - one of the approvers should have
    # "admin" label.
    self.WaitUntilContains("At least 1 approver(s) should have 'admin' label.",
                           self.GetText, "css=div#acl_form")

    # Let's make "approver" an admin.
    with self.ACLChecksDisabled():
      self.CreateAdminUser("approver")

    # And try again
    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")

    # Select and enable OSBreakDown cron job.
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was ENABLEd successfully!")

  def testEmailClientApprovalRequestLinkLeadsToACorrectPage(self):
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]

    messages_sent = []

    def SendEmailStub(unused_from_user, unused_to_user, unused_subject,
                      message, **unused_kwargs):
      messages_sent.append(message)

    # Request client approval, it will trigger an email message.
    with utils.Stubber(email_alerts, "SendEmail", SendEmailStub):
      flow.GRRFlow.StartFlow(client_id=client_id,
                             flow_name="RequestClientApprovalFlow",
                             reason="Please please let me",
                             subject_urn=client_id,
                             approver="test",
                             token=rdfvalue.ACLToken(username="iwantapproval",
                                                     reason="test"))
    self.assertEqual(len(messages_sent), 1)

    # Extract link from the message text and open it.
    m = re.search(r"href='(.+?)'", messages_sent[0], re.MULTILINE)
    link = urlparse.urlparse(m.group(1))
    self.Open(link.path + "?" + link.query + "#" + link.fragment)

    # Check that requestor's username and  reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, "iwantapproval")
    self.WaitUntil(self.IsTextPresent, "Please please let me")
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, str(client_id))
    self.WaitUntil(self.IsTextPresent, "HOSTNAME")
    self.WaitUntil(self.IsTextPresent, "MAC_ADDRESS")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
