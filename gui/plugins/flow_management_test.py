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

"""Test the flow_management interface."""


from grr.lib import flow
from grr.lib import test_lib


class RecursiveTestFlow(flow.GRRFlow):
  """A test flow which starts some subflows."""

  def __init__(self, depth=0, **kwargs):
    self.depth = depth
    super(RecursiveTestFlow, self).__init__(**kwargs)

  @flow.StateHandler(next_state="End")
  def Start(self):
    if self.depth < 2:
      for _ in range(2):
        self.CallFlow("RecursiveTestFlow", depth=self.depth+1,
                      next_state="End")


class TestFlowManagement(test_lib.GRRSeleniumTest):
  """Test the flow management GUI."""

  def testFlowManagement(self):
    """Test that scheduling flows works."""
    sel = self.selenium
    sel.open("/")

    self.WaitUntil(sel.is_element_present, "css=input[name=q]")
    sel.type("css=input[name=q]", "0001")
    sel.click("css=input[type=submit]")

    self.WaitUntilEqual(u"aff4:/C.0000000000000001",
                        sel.get_text, "css=span[type=subject]")

    # Choose client 1
    sel.click("css=td:contains('0001')")

    # First screen should be the Host Information already.
    self.WaitUntil(sel.is_text_present, "VFSGRRClient")

    sel.click("css=a[grrtarget=LaunchFlows]")
    self.WaitUntil(sel.is_element_present, "id=_Processes")
    self.failUnless(sel.is_element_present("id=_Processes"))
    sel.click("css=ins.jstree-icon")
    self.WaitUntil(sel.is_element_present, "link=ListProcesses")

    self.assertEqual("ListProcesses", sel.get_text("link=ListProcesses"))
    sel.click("link=ListProcesses")
    self.WaitUntil(sel.is_element_present, "css=input[value=Launch]")
    self.failUnless(sel.is_text_present("C.0000000000000001"))

    self.failUnless(sel.is_text_present(
        "Prototype: ListProcesses"))

    sel.click("css=input[value=Launch]")
    self.WaitUntil(sel.is_element_present, "css=input[value=Back]")
    self.failUnless(sel.is_text_present("Launched flow ListProcesses"))
    self.failUnless(sel.is_text_present("client_id = C.0000000000000001"))

    sel.click("css=input[value=Back]")
    self.WaitUntil(sel.is_element_present, "css=input[value=Launch]")
    self.assertEqual("Client ID", sel.get_text("css=td.proto_key"))
    sel.click("css=#_Network > ins.jstree-icon")
    self.WaitUntil(sel.is_element_present, "link=Netstat")
    self.assertEqual("Netstat", sel.get_text("link=Netstat"))
    sel.click("css=#_Browser > ins.jstree-icon")

    # Check that we can get a file in chinese
    sel.click("css=#_Filesystem > ins.jstree-icon")
    self.WaitUntil(sel.is_element_present, "link=GetFile")
    sel.click("link=GetFile")
    self.WaitUntil(sel.is_element_present, "css=input[name=v_path]")
    sel.type("css=input[name=v_path]", u"/dev/c/msn升级程序[1].exe")
    sel.click("css=input[value=Launch]")

    self.WaitUntil(sel.is_text_present, "Launched flow GetFile")

    # Test that recursive tests are shown in a tree table.
    flow.FACTORY.StartFlow(
        "aff4:/C.0000000000000001", "RecursiveTestFlow", token=self.token)

    sel.click("css=a:contains('Manage launched flows')")

    self.WaitUntilEqual("RecursiveTestFlow", sel.get_text,
                        "//table/tbody/tr[1]/td[3]")

    visibility = []
    for i in range(1, 11):
      visibility.append(sel.is_visible("//table/tbody/tr[%s]" % i))

    self.assertEqual(visibility, [1, 0, 0, 0, 0, 0, 0, 1, 1, 0])

    # Click on the first tree_closed to open it.
    sel.click("css=.tree_closed")

    visibility = []
    for i in range(1, 11):
      visibility.append(sel.is_visible("//table/tbody/tr[%s]" % i))

    self.assertEqual(visibility, [1, 1, 0, 0, 1, 0, 0, 1, 1, 0])
