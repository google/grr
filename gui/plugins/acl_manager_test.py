#!/usr/bin/env python

# Copyright 2012 Google Inc.
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

"""Tests the access control authorization workflow."""



from grr.client import conf as flags

from grr.lib import access_control
from grr.lib import data_store
from grr.lib import flow
from grr.lib import test_lib

FLAGS = flags.FLAGS


class TestACLWorkflow(test_lib.GRRSeleniumTest):
  """Tests the access control workflow."""

  @classmethod
  def InstallACLChecks(cls):
    data_store.DB.security_manager = access_control.AccessControlManager()


  def testACLWorkflow(self):
    self.InstallACLChecks()

    sel = self.selenium
    sel.open("/")

    self.WaitUntil(sel.is_element_present, "css=input[name=q]")
    sel.type("css=input[name=q]", "0001")
    sel.click("css=input[type=submit]")

    self.WaitUntilEqual(u"aff4:/C.0000000000000001",
                        sel.get_text, "css=span[type=subject]")

    # Choose client 1
    sel.click("css=td:contains('0001')")

    # This should be rejected now and a form request is made.
    self.WaitUntil(sel.is_element_present,
                   "css=h3:contains('Create a new approval')")

    # This asks the user "test" (which is us) to approve the request.
    sel.type("css=input[id=acl_approver]", "test")
    sel.type("css=input[id=acl_reason]", "Felt like it!")
    sel.click("css=form.acl_form input[type=submit]")

    # User test logs in as an approver.
    sel.open("/")
    self.WaitUntilEqual("1",
                        sel.get_text, "notification_button")

    sel.click("notification_button")
    self.WaitUntil(sel.get_text, "css=td:contains('grant access')")
    sel.click("css=td:contains('grant access')")

    self.WaitUntilContains("Grant Access for GRR Use",
                           sel.get_text, "css=h1:contains('Grant')")

    sel.click("css=button:contains('Approve')")

    self.WaitUntilContains(
        "You have granted access for C.0000000000000001 to test",
        sel.get_text, "css=div.TableBody")

    # Now test starts up
    sel.open("/")

    # We should be notified that we have an approval
    self.WaitUntilEqual("1",
                        sel.get_text, "notification_button")

    sel.click("notification_button")

    self.WaitUntil(sel.get_text, "css=td:contains('has approved')")
    sel.click("css=td:contains('has approved')")

    # This is insufficient - we need 2 approvers.
    self.WaitUntilContains("Requires 2 approvers for access.",
                           sel.get_text, "css=div#acl_form")

    # Lets add another approver.
    token = data_store.ACLToken(username="approver")
    flow.FACTORY.StartFlow("C.0000000000000001", "GrantAccessFlow",
                           reason="Felt like it!", delegate="test", token=token)

    # Try again:
    sel.open("/")
    self.WaitUntil(sel.is_element_present, "notification_button")

    sel.click("notification_button")

    self.WaitUntil(sel.get_text, "css=td:contains('has approved')")
    sel.click("css=td:contains('has approved')")

    self.WaitUntilEqual("fs", sel.get_text, "css=span:contains('fs')")
    sel.click("css=span:contains('fs')")

    # This is ok - it should work now
    self.WaitUntilContains("aff4:/C.0000000000000001/fs",
                           sel.get_text, "css=h3:contains('fs')")

