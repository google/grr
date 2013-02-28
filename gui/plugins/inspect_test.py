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

"""Test the inspect interface."""


from grr.lib import test_lib


class TestInspectView(test_lib.GRRSeleniumTest):
  """Test the inspect interface."""

  def testInspect(self):
    """Test the inspect UI."""

    sel = self.selenium
    sel.open("/")

    self.WaitUntil(sel.is_element_present, "client_query")

    sel.type("client_query", "0001")
    sel.click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        sel.get_text, "css=span[type=subject]")

    # Choose client 1
    sel.click("css=td:contains('0001')")
    self.WaitUntil(sel.is_element_present, "css=a[grrtarget=LaunchFlows]")

    sel.click("css=a[grrtarget=LaunchFlows]")
    self.WaitUntil(sel.is_element_present, "id=_Administrative")
    sel.click("css=#_Administrative ins")

    self.WaitUntil(sel.is_text_present, "Interrogate")
    sel.click("css=a:contains(Interrogate)")

    self.WaitUntil(sel.is_element_present, "css=input[value=Launch]")
    sel.click("css=input[value=Launch]")

    sel.click("css=a[grrtarget=InspectView]")

    self.WaitUntil(sel.is_element_present, "css=td:contains(GetPlatformInfo)")

    # Check that the we can see the requests in the table.
    for request in "GetPlatformInfo GetConfig EnumerateInterfaces Find".split():
      self.assertTrue(sel.is_element_present(
          "css=td:contains(%s)" % request))

    sel.click("css=td:contains(GetPlatformInfo)")

    # Check that the proto is rendered inside the tab.
    self.WaitUntil(sel.is_element_present,
                   "css=.tab-content td.proto_value:contains(GetPlatformInfo)")

    # Check that the request tab is currently selected.
    self.assertTrue(
        sel.is_element_present("css=li.active:contains(Request)"))

    # Here we emulate a mock client with no actions (None) this should produce
    # an error.
    mock = test_lib.MockClient("C.0000000000000001", None, token=self.token)
    while mock.Next():
      pass

    # Now select the Responses tab:
    sel.click("css=li a:contains(Responses)")
    self.WaitUntil(sel.is_element_present, "css=td:contains('flow:response:')")

    self.assertTrue(sel.is_element_present(
        "css=.tab-content td.proto_value:contains(GENERIC_ERROR)"))

    self.assertTrue(sel.is_element_present(
        "css=.tab-content td.proto_value:contains(STATUS)"))
