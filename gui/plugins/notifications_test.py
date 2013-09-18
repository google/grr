#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the fileview interface."""


from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib


class TestNotifications(test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  @classmethod
  def GenerateNotifications(cls):
    """Generate some fake notifications."""
    token = access_control.ACLToken(username="test", reason="test fixture")
    cls.session_id = flow.GRRFlow.StartFlow(
        client_id="aff4:/C.0000000000000001", flow_name="Interrogate",
        token=token)

    with aff4.FACTORY.Open(cls.session_id, mode="rw", token=token) as flow_obj:
      flow_obj.Notify("ViewObject",
                      "aff4:/C.0000000000000001/fs/os/proc/10/exe",
                      "File fetch completed.")

      # Generate an error for this flow.
      with flow_obj.GetRunner() as runner:
        runner.Error("not a real backtrace")

  def setUp(self):
    super(TestNotifications, self).setUp()

    # Have something for us to look at.
    with self.ACLChecksDisabled():
      self.GenerateNotifications()
      self.GrantClientApproval("C.0000000000000001")

  def testNotifications(self):
    """Test the notifications interface."""
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")

    # There should be 3 notifications ready (2 that we generate + 1 about
    # approval).
    self.WaitUntilEqual(
        "3", self.GetText, "css=button[id=notification_button]")

    # Clicking on this should show the table
    self.Click("css=button[id=notification_button]")

    # This should clear the notifications.
    self.WaitUntilEqual(
        "0", self.GetText, "css=button[id=notification_button]")

    # Notifications should be clear even after we reload the page.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.WaitUntilEqual("0", self.GetText, "css=button[id=notification_button]")

    # Clicking on this should show the table
    self.Click("css=button[id=notification_button]")

    # Select a ViewObject notification - should navigate to the object.
    self.WaitUntilEqual(
        "aff4:/C.0000000000000001/fs/os/proc/10/exe",
        self.GetText, "css=a[target_hash]:contains('exe')")

    self.ClickUntil("css=td:contains('File fetch completed')",
                    self.IsElementPresent, "css=li[id=_fs-os-proc-10]")

    self.WaitUntilEqual("Browse Virtual Filesystem",
                        self.GetText, "css=li[class='active']")

    # The tree is opened to the correct place
    self.WaitUntil(self.IsElementPresent, "css=li[id=_fs-os-proc-10]")

    # The stats pane shows the target file
    self.WaitUntilContains(
        "aff4:/C.0000000000000001/fs/os/proc/10/exe",
        self.GetText, "css=.tab-content h3")

    # Now select a FlowStatus notification - should navigate to the broken flow.
    self.Click("css=button[id=notification_button]")

    self.WaitUntilContains("terminated due to error",
                           self.GetText, "css=td:contains('error')")

    self.ClickUntil("css=td:contains('terminated due to error')",
                    self.IsTextPresent, "Flow Information")

    # The navigation bar should manage the flows
    self.WaitUntilEqual(
        "Manage launched flows",
        self.GetText, "css=li[class='active']")

    # The stats pane shows the relevant flow
    self.WaitUntilContains(
        self.session_id, self.GetText, "css=.tab-content h3")

  def testUserSettings(self):
    """Tests that user settings UI is working."""
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")

    # Open settings dialog and change mode from BASIC to ADVANCED
    self.Click("css=button[id=user_settings_button]")
    self.assertEqual(
        "ADVANCED",
        self.GetSelectedLabel("css=#user_settings_dialog select#settings-mode"))

    self.Select("css=#user_settings_dialog select#settings-mode",
                "BASIC (default)")
    self.Click("css=#user_settings_dialog button[name=Proceed]")

    # Check that the mode value was saved
    self.Click("css=button[id=user_settings_button]")
    self.assertEqual(
        "BASIC (default)",
        self.GetSelectedLabel(
            "css=#user_settings_dialog select#settings-mode").strip())


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
