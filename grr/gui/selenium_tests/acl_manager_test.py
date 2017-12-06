#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests the access control authorization workflow."""

import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.server import access_control
from grr.server import aff4
from grr.server.aff4_objects import security


class TestACLWorkflow(gui_test_lib.GRRSeleniumTest):
  """Tests the access control workflow."""

  # Using an Unicode string for the test here would be optimal but Selenium
  # can't correctly enter Unicode text into forms.
  reason = "Felt like it!"

  def testNavigatorLinksDisabledForClientWithoutApproval(self):
    self.Open("/#/clients/C.0000000000000001?navigator-test")

    self.WaitUntil(self.IsElementPresent,
                   "css=a[grrtarget='client.vfs'].disabled")
    self.WaitUntil(self.IsElementPresent,
                   "css=a[grrtarget='client.launchFlows'].disabled")
    self.WaitUntil(self.IsElementPresent,
                   "css=a[grrtarget='client.flows'].disabled")

    # Only the "Host Information" navigation link should be active.
    self.WaitUntil(self.IsElementPresent,
                   "css=a[grrtarget='client.hostInfo']:not(.disabled)")

  def testApprovalNotificationIsShownInHostInfoForUnapprovedClient(self):
    self.Open("/#/clients/C.0000000000000001")

    self.WaitUntil(self.IsTextPresent,
                   "You do not have an approval for this client.")

  def testClickingOnRequestApprovalShowsApprovalDialog(self):
    self.Open("/#/clients/C.0000000000000001")

    self.Click("css=button[name=requestApproval]")

    self.WaitUntil(self.IsElementPresent,
                   "css=h3:contains('Create a new approval')")

  def testClientACLWorkflow(self):
    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # We do not have an approval, so we need to request one.
    self.WaitUntil(self.IsElementPresent, "css=div.no-approval")
    self.Click("css=button[name=requestApproval]")
    self.WaitUntil(self.IsElementPresent,
                   "css=h3:contains('Create a new approval')")

    # This asks the user "test" (which is us) to approve the request.
    self.Type("css=grr-request-approval-dialog input[name=acl_approver]",
              self.token.username)
    self.Type("css=grr-request-approval-dialog input[name=acl_reason]",
              self.reason)
    self.Click(
        "css=grr-request-approval-dialog button[name=Proceed]:not([disabled])")

    self.WaitForNotification("aff4:/users/%s" % self.token.username)
    # User test logs in as an approver.
    self.Open("/")

    self.WaitUntil(lambda: self.GetText("notification_button") != "0")

    self.Click("notification_button")

    self.Click("css=td:contains('grant access to GRR client')")

    self.WaitUntilContains("Grant access", self.GetText,
                           "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent,
                   "The user %s has requested" % self.token.username)

    self.Click("css=button:contains('Approve')")

    self.WaitUntil(self.IsTextPresent, "Approval granted.")

    self.WaitForNotification("aff4:/users/%s" % self.token.username)
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntil(lambda: self.GetText("notification_button") != "0")

    self.Click("notification_button")

    self.Click("css=td:contains('has granted you access')")

    # This is insufficient - we need 2 approvers.
    self.WaitUntil(self.IsTextPresent,
                   "You do not have an approval for this client.")

    # Lets add another approver.
    token = access_control.ACLToken(username="approver")
    security.ClientApprovalGrantor(
        reason=self.reason,
        delegate=self.token.username,
        subject_urn=rdf_client.ClientURN("C.0000000000000001"),
        token=token).Grant()

    # Check if we see that the approval has already been granted.
    self.Open("/")

    self.Click("notification_button")

    self.Click("css=td:contains('grant access to GRR client')")

    self.WaitUntil(self.IsTextPresent,
                   "This approval has already been granted!")

    # Try again:
    self.Open("/")

    self.Click("notification_button")

    self.Click("css=td:contains('has granted you access')")

    # Host information page should be displayed.
    self.WaitUntil(self.IsTextPresent, "Last booted")
    self.WaitUntil(self.IsTextPresent, "Interfaces")

    # One email for the original request and one for each approval.
    self.assertEqual(len(self.emails_sent), 3)

  def testRecentReasonBox(self):
    self.Open("/")

    test_reason = u"ástæða"
    token = access_control.ACLToken(
        username=self.token.username, reason=test_reason)
    self.RequestAndGrantClientApproval("C.0000000000000006", token=token)

    self.Type("client_query", "C.0000000000000006")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000006", self.GetText,
                        "css=span[type=subject]")

    # Choose client 6
    self.Click("css=td:contains('0006')")

    self.WaitUntil(self.IsTextPresent, u"Access reason: %s" % test_reason)

    # By now we should have a recent reason set, let's see if it shows up in the
    # ACL dialog.
    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # We do not have an approval, so check that the hint is shown, that the
    # interrogate button is disabled and that the menu is disabled.
    self.WaitUntil(self.IsElementPresent, "css=div.no-approval")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Interrogate')[disabled]")
    self.WaitUntil(self.IsElementPresent, "css=a.nav-link.disabled")

    # Request an approval.
    self.Click("css=button[name=requestApproval]")
    self.WaitUntil(self.IsElementPresent,
                   "css=h3:contains('Create a new approval')")

    self.WaitUntilEqual(2, self.GetCssCount, "css=grr-request-approval-dialog "
                        "select[name=acl_recent_reasons] option")
    self.assertEqual("Enter New Reason...",
                     self.GetText(
                         "css=grr-request-approval-dialog "
                         "select[name=acl_recent_reasons] option:nth(0)"))
    self.assertEqual(test_reason,
                     self.GetText(
                         "css=grr-request-approval-dialog "
                         "select[name=acl_recent_reasons] option:nth(1)"))

    # The reason text box should be there and enabled.
    element = self.GetElement(
        "css=grr-request-approval-dialog input[name=acl_reason]")
    self.assertTrue(element.is_enabled())

    self.Select(
        "css=grr-request-approval-dialog select[name=acl_recent_reasons]",
        test_reason)

    # Make sure clicking the recent reason greys out the reason text box.
    element = self.GetElement(
        "css=grr-request-approval-dialog input[name=acl_reason]")
    self.assertFalse(element.is_enabled())

    # Ok now submit this.
    self.Type("css=grr-request-approval-dialog input[name=acl_approver]",
              self.token.username)
    self.Click(
        "css=grr-request-approval-dialog button[name=Proceed]:not([disabled])")

    # "Request Approval" dialog should go away.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # And make sure the approval was created...
    def GetApprovals():
      fd = aff4.FACTORY.Open(
          "aff4:/ACL/C.0000000000000001/%s" % self.token.username,
          token=self.token)
      return list(fd.ListChildren())

    self.WaitUntilEqual(1, lambda: len(GetApprovals()))

    # ... using the correct reason.
    approvals = GetApprovals()
    approval = aff4.FACTORY.Open(approvals[0], token=self.token)
    self.assertEqual(
        utils.SmartUnicode(approval.Get(approval.Schema.REASON)), test_reason)


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
