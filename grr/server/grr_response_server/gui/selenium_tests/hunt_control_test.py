#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the hunt_view interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_core.lib import rdfvalue
from grr_response_server import access_control
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestHuntControl(gui_test_lib.GRRSeleniumHuntTest):
  """Test the hunt start/stop/delete functionality."""

  def testToolbarStateForStoppedHunt(self):
    self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RunHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent, "css=button[name=StopHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt]:not([disabled])")

  def testToolbarStateForRunningHunt(self):
    self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")

    self.WaitUntil(self.IsElementPresent, "css=button[name=RunHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=StopHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt][disabled]")

  def testRunHunt(self):
    hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
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
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=grr-request-approval-dialog button[name=Cancel]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.RequestAndGrantHuntApproval(hunt.urn.Basename())

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt started successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    # Check the hunt is in a running state.
    self.CheckState("STARTED")

  def testStopHunt(self):
    hunt = self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Stop button and check that dialog appears.
    self.Click("css=button[name=StopHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to stop this hunt?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=grr-request-approval-dialog button[name=Cancel]")

    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.RequestAndGrantHuntApproval(hunt.session_id.Basename())

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

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Check the hunt is not in a running state.
    self.CheckState("STOPPED")

  def testModifyHunt(self):
    hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify this hunt")

    expiry_time = rdfvalue.Duration("5m").Expiry().Format("%Y-%m-%d %H:%M")

    self.Type(
        "css=grr-modify-hunt-dialog label:contains('Client limit') ~ * input",
        "4483")
    self.Type(
        "css=grr-modify-hunt-dialog label:contains('Client rate') ~ * input",
        "42")
    self.Type("css=grr-modify-hunt-dialog label:contains('Expires') ~ * input",
              expiry_time)

    # Click on Proceed.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=grr-request-approval-dialog button[name=Cancel]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # Now create an approval.
    self.RequestAndGrantHuntApproval(hunt.session_id.Basename())

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify this hunt")

    self.Type(
        "css=grr-modify-hunt-dialog label:contains('Client limit') ~ * input",
        "4483")
    self.Type(
        "css=grr-modify-hunt-dialog label:contains('Client rate') ~ * input",
        "42")
    self.Type("css=grr-modify-hunt-dialog label:contains('Expires') ~ * input",
              expiry_time)

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, "4483")
    self.WaitUntil(self.IsTextPresent, expiry_time)

  def testDeleteHunt(self):
    # This needs to be created by a different user so we can test the
    # approval dialog.
    hunt = self.CreateSampleHunt(
        stopped=True,
        token=access_control.ACLToken(username="random user", reason="test"))

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on delete button.
    self.Click("css=button[name=DeleteHunt]")
    self.WaitUntil(self.IsTextPresent, "Delete this hunt")

    # Click on Proceed.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=grr-request-approval-dialog button[name=Cancel]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # Now create an approval.
    self.RequestAndGrantHuntApproval(hunt.session_id.Basename())

    # Select a hunt again, as it's deselected after approval dialog
    # disappears. TODO(user): if this behavior is not convenient, fix it.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Delete button and check that dialog appears.
    self.Click("css=button[name=DeleteHunt]")
    self.WaitUntil(self.IsTextPresent, "Delete this hunt")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt deleted successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
