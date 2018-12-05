#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests Hunt ACLs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server import access_control
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import gui_test_lib
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestHuntACLWorkflow(gui_test_lib.GRRSeleniumHuntTest):
  # Using an Unicode string for the test here would be optimal but Selenium
  # can't correctly enter Unicode text into forms.
  reason = "Felt like it!"

  def CreateSampleHunt(self, token=None):

    with implementation.StartHunt(
        hunt_name=standard.SampleHunt.__name__,
        client_rate=100,
        filename="TestFilename",
        client_rule_set=self._CreateForemanClientRuleSet(),
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

    self.WaitForNotification(self.token.username)
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
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")

    self.Click("css=button:contains('Approve')")
    self.WaitUntil(self.IsTextPresent, "Approval granted.")

    self.WaitForNotification(self.token.username)
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
    self.WaitUntilContains("Need at least 1 additional approver for access.",
                           self.GetText, "css=grr-request-approval-dialog")

    # Lets add another approver.
    approval_id = self.ListHuntApprovals(requestor=self.token.username)[0].id
    self.GrantHuntApproval(
        hunt_id.Basename(),
        approval_id=approval_id,
        approver=u"approver",
        requestor=self.token.username,
        admin=False)

    self.WaitForNotification(self.token.username)
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
    self.WaitUntilContains("Need at least 1 admin approver for access",
                           self.GetText, "css=grr-request-approval-dialog")

    # Let's make "approver" an admin.
    self.CreateAdminUser(u"approver")

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
    hunt1_id = self.CreateSampleHunt(
        token=access_control.ACLToken(username=u"otheruser"))
    hunt2_id = self.CreateSampleHunt(
        token=access_control.ACLToken(username=self.token.username))
    self.CreateAdminUser(u"approver")

    self.RequestAndGrantHuntApproval(
        hunt1_id.Basename(),
        reason=self.reason,
        approver=u"approver",
        requestor=u"otheruser")
    self.RequestAndGrantHuntApproval(
        hunt2_id.Basename(),
        reason=self.reason,
        approver=u"approver",
        requestor=self.token.username)

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

  def _RequestAndOpenApprovalFromSelf(self, hunt_id):
    self.RequestHuntApproval(
        hunt_id.Basename(),
        reason=self.reason,
        approver=self.token.username,
        requestor=self.token.username)

    self.WaitForNotification(self.token.username)
    self.Open("/")
    self.WaitUntil(lambda: self.GetText("notification_button") != "0")
    self.Click("notification_button")
    self.Click("css=td:contains('Please grant access to hunt')")

  def testWarningIsShownIfReviewedHuntIsNotACopy(self):
    hunt_id = self.CreateSampleHunt()
    self._RequestAndOpenApprovalFromSelf(hunt_id)

    self.WaitUntil(self.IsTextPresent,
                   "This hunt is new. It wasn't copied from another hunt")
    # Make sure that only the correct message appears and the others are not
    # shown.
    self.WaitUntilNot(self.IsTextPresent, "This hunt was copied from")
    self.WaitUntilNot(self.IsTextPresent, "This hunt was created from a flow")

  def _CreateHuntFromFlow(self):
    self.client_id = self.SetupClient(0)

    flow_args = rdf_file_finder.FileFinderArgs(
        paths=["a/*", "b/*"],
        action=rdf_file_finder.FileFinderAction(action_type="STAT"))
    session_id = flow_test_lib.StartFlow(
        file_finder.FileFinder, client_id=self.client_id, flow_args=flow_args)

    ref = rdf_hunts.FlowLikeObjectReference.FromFlowIdAndClientId(
        session_id, self.client_id.Basename())
    # Modify flow_args so that there are differences.
    flow_args.paths = ["b/*", "c/*"]
    flow_args.action.action_type = "DOWNLOAD"
    flow_args.conditions = [
        rdf_file_finder.FileFinderCondition(
            condition_type="SIZE",
            size=rdf_file_finder.FileFinderSizeCondition(min_file_size=42))
    ]
    return self.CreateHunt(
        flow_args=flow_args,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        original_object=ref), session_id

  def testFlowDiffIsShownIfHuntCreatedFromFlow(self):
    h, _ = self._CreateHuntFromFlow()
    self._RequestAndOpenApprovalFromSelf(h.urn)

    self.WaitUntil(self.IsTextPresent, "This hunt was created from a flow")
    # Make sure that only the correct message appears and the others are not
    # shown.
    self.WaitUntilNot(self.IsTextPresent,
                      "This hunt is new. It wasn't copied from another hunt")
    self.WaitUntilNot(self.IsTextPresent, "This hunt was copied from")

    self.WaitUntil(self.IsElementPresent, "css=.diff-removed:contains('a/*')")
    self.WaitUntil(self.IsElementPresent, "css=.diff-added:contains('c/*')")
    self.WaitUntil(self.IsElementPresent,
                   "css=tr.diff-changed:contains('Action'):contains('STAT')")
    self.WaitUntil(
        self.IsElementPresent,
        "css=tr.diff-changed:contains('Action'):contains('DOWNLOAD')")
    self.WaitUntil(
        self.IsElementPresent,
        "css=tr.diff-added:contains('Conditions'):contains('Size')"
        ":contains('42')")

  def testOriginalFlowLinkIsShownIfHuntCreatedFromFlow(self):
    h, flow_id = self._CreateHuntFromFlow()
    self.RequestAndGrantClientApproval(self.client_id)
    self._RequestAndOpenApprovalFromSelf(h.urn)

    self.WaitUntil(self.IsTextPresent, "This hunt was created from a flow")
    self.Click("css=a:contains('%s')" % flow_id)

    self.WaitUntil(self.IsElementPresent, "css=grr-client-flows-view")

  def _CreateHuntFromHunt(self):
    flow_args = rdf_file_finder.FileFinderArgs(
        paths=["a/*", "b/*"],
        action=rdf_file_finder.FileFinderAction(action_type="STAT"))
    flow_runner_args = rdf_flow_runner.FlowRunnerArgs(
        flow_name=file_finder.FileFinder.__name__)
    client_rule_set = self._CreateForemanClientRuleSet()
    source_h = self.CreateHunt(
        flow_args=flow_args,
        flow_runner_args=flow_runner_args,
        description="foo-description",
        client_rule_set=client_rule_set)

    ref = rdf_hunts.FlowLikeObjectReference.FromHuntId(source_h.urn.Basename())

    # Modify flow_args so that there are differences.
    flow_args.paths = ["b/*", "c/*"]
    client_rule_set.rules[0].regex.field = "FQDN"
    output_plugins = [
        rdf_output_plugin.OutputPluginDescriptor(plugin_name="TestOutputPlugin")
    ]
    new_h = self.CreateHunt(
        flow_args=flow_args,
        flow_runner_args=flow_runner_args,
        description="bar-description",
        client_rule_set=client_rule_set,
        output_plugins=output_plugins,
        original_object=ref)

    return new_h, source_h

  def testHuntDiffIsShownIfHuntIsCopied(self):
    new_h, _ = self._CreateHuntFromHunt()
    self._RequestAndOpenApprovalFromSelf(new_h.urn)

    self.WaitUntil(self.IsTextPresent, "This hunt was copied from")
    # Make sure that only the correct message appears and the others are not
    # shown.
    self.WaitUntilNot(self.IsTextPresent, "This hunt was created from a flow")
    self.WaitUntilNot(self.IsTextPresent,
                      "This hunt is new. It wasn't copied from another hunt")

    self.WaitUntil(self.IsElementPresent, "css=.diff-removed:contains('a/*')")
    self.WaitUntil(self.IsElementPresent, "css=.diff-added:contains('c/*')")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr.diff-changed:contains('foo-description')")
    self.WaitUntil(self.IsElementPresent,
                   "css=tr.diff-changed:contains('bar-description')")

    self.WaitUntil(
        self.IsElementPresent, "css=tr.diff-added:contains('Output Plugins'):"
        "contains('TestOutputPlugin')")

    self.WaitUntil(
        self.IsElementPresent,
        "css=td table.diff-removed:contains('Rule type'):"
        "contains('REGEX'):contains('CLIENT_NAME')")
    self.WaitUntil(
        self.IsElementPresent, "css=td table.diff-added:contains('Rule type'):"
        "contains('REGEX'):contains('FQDN')")

  def testOriginalHuntLinkIsShownIfHuntCreatedFromHunt(self):
    new_h, source_h = self._CreateHuntFromHunt()
    self._RequestAndOpenApprovalFromSelf(new_h.urn)

    self.WaitUntil(self.IsTextPresent, "This hunt was copied from")
    self.Click("css=a:contains('%s')" % source_h.urn.Basename())

    self.WaitUntil(self.IsElementPresent, "css=grr-hunts-view")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
