#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the fileview interface."""


from grr.lib import access_control
from grr.lib import flow
from grr.lib import test_lib


class TestNotifications(test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  @classmethod
  def GenerateNotifications(cls):
    """Generate some fake notifications."""
    token = access_control.ACLToken("test", "test fixture")
    cls.session_id = flow.FACTORY.StartFlow("aff4:/C.0000000000000001",
                                            "Interrogate", token=token)
    rdf_flow = flow.FACTORY.FetchFlow(cls.session_id, token=token)
    flow_obj = flow.FACTORY.LoadFlow(rdf_flow)
    flow_obj.Notify("ViewObject", "aff4:/C.0000000000000001/fs/os/proc/10/exe",
                    "File fetch completed.")

    # Generate an error for this flow.
    flow_obj.Error("not a real backtrace")
    flow.FACTORY.ReturnFlow(rdf_flow, token=token)

  def testNotifications(self):
    """Test the notifications interface."""
    # Have something for us to look at.
    self.GenerateNotifications()

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")

    # There should be 2 notifications ready
    self.WaitUntilEqual(
        "2", self.GetText, "css=button[id=notification_button]")

    # Clicking on this should show the table
    self.Click("css=button[id=notification_button]")

    # This should clear the notifications.
    self.WaitUntilEqual(
        "0", self.GetText, "css=button[id=notification_button]")

    # Select a ViewObject notification - should navigate to the object.
    self.WaitUntilEqual(
        "aff4:/C.0000000000000001/fs/os/proc/10/exe",
        self.GetText, "css=a[target_hash]:contains('exe')")

    self.Click("css=td:contains('exe')")

    # The navigation bar should browse the vfs
    self.WaitUntilEqual(
        "Browse Virtual Filesystem",
        self.GetText, "css=li[class='active']")

    # The tree is opened to the correct place
    self.WaitUntil(self.IsElementPresent,
                   "css=li[id=_fs-os-proc-10]")

    # The stats pane shows the target file
    self.WaitUntilContains(
        "aff4:/C.0000000000000001/fs/os/proc/10/exe",
        self.GetText, "css=.tab-content h3")

    # Now select a FlowStatus notification - should navigate to the broken flow.
    self.Click("css=button[id=notification_button]")

    self.WaitUntilContains("terminated due to error",
                           self.GetText, "css=td:contains('error')")

    self.Click("css=td:contains('error')")

    # The navigation bar should manage the flows
    self.WaitUntilEqual(
        "Manage launched flows",
        self.GetText, "css=li[class='active']")

    # The stats pane shows the relevant flow
    self.WaitUntilContains(
        self.session_id, self.GetText, "css=.tab-content h3")
