#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the fileview interface."""


from grr.lib import data_store
from grr.lib import flow
from grr.lib import test_lib


class TestNotifications(test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  @classmethod
  def GenerateNotifications(cls):
    """Generate some fake notifications."""
    token = data_store.ACLToken("test", "test fixture")
    cls.session_id = flow.FACTORY.StartFlow("aff4:/C.0000000000000001",
                                            "Interrogate", token=token)
    flow_pb = flow.FACTORY.FetchFlow(cls.session_id, token=token)
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)
    flow_obj.Notify("ViewObject", "aff4:/C.0000000000000001/fs/os/proc/10/exe",
                    "File fetch completed.")

    # Generate an error for this flow.
    flow_obj.Error()
    flow.FACTORY.ReturnFlow(flow_pb, token=token)

  def testNotifications(self):
    """Test the notifications interface."""
    # Have something for us to look at.
    self.GenerateNotifications()

    sel = self.selenium
    sel.open("/")

    self.WaitUntil(sel.is_element_present, "css=input[name=q]")

    # There should be 2 notifications ready
    self.WaitUntilEqual(
        "2", sel.get_text, "css=button[id=notification_button]")

    # Clicking on this should show the table
    sel.click("css=button[id=notification_button]")

    # This should clear the notifications.
    self.WaitUntilEqual(
        "0", sel.get_text, "css=button[id=notification_button]")

    # Select a ViewObject notification - should navigate to the object.
    self.WaitUntilEqual(
        "aff4:/C.0000000000000001/fs/os/proc/10/exe",
        sel.get_text, "css=a[target_hash]:contains('exe')")

    sel.click("css=a[target_hash]:contains('exe')")

    # The navigation bar should browse the vfs
    self.WaitUntilEqual(
        "Browse Virtual Filesystem",
        sel.get_text, "css=li[class='selected']")

    # The tree is opened to the correct place
    self.WaitUntil(sel.is_element_present,
                   "css=li[id=_fs-os-proc-10]")

    # The stats pane shows the target file
    self.WaitUntilContains(
        "aff4:/C.0000000000000001/fs/os/proc/10/exe",
        sel.get_text, "css=h3")

    # Now select a FlowStatus notification - should navigate to the broken flow.
    sel.click("css=button[id=notification_button]")

    self.WaitUntilContains("terminated due to error",
                           sel.get_text, "css=td:contains('error')")

    sel.click("css=td:contains('error')")

    # The navigation bar should manage the flows
    self.WaitUntilEqual(
        "Manage launched flows",
        sel.get_text, "css=li[class='selected']")

    # The stats pane shows the relevant flow
    self.WaitUntilContains(
        self.session_id, sel.get_text, "css=h3")
