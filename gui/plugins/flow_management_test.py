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


from grr.lib import test_lib


class TestFlowManagement(test_lib.GRRSeleniumTest):
  """Test the flow management GUI."""

  def testFlowManagement(self):
    """Test that scheduling flows works."""
    sel = self.selenium
    sel.open("/")

    sel.type("css=input[name=Host]", "0001")
    sel.key_up("css=input[name=Host]", "1")
    self.WaitUntilEqual(u"aff4:/C.0000000000000001",
                        sel.get_text, "css=span[type=subject]")

    # Choose client 1
    sel.click("css=td:contains('0001')")
    self.WaitUntil(sel.is_element_present, "css=#_fs")
    sel.click("css=#_fs ins.jstree-icon")

    self.WaitUntil(sel.is_element_present, "css=#_fs-os")
    sel.click("css=#_fs-os ins.jstree-icon")

    self.WaitUntil(sel.is_element_present, "css=#_fs-os-c")
    sel.click("css=#_fs-os-c ins.jstree-icon")

    self.WaitUntil(sel.is_text_present, "Start")
    self.assertEqual("GRR Admin Console", sel.get_title())

    self.failUnless(sel.is_text_present("Help"))
    self.WaitUntil(sel.is_element_present, "select_button")

    sel.click("select_button")
    self.WaitUntil(sel.is_element_present, "css=input[name=Host]")
    self.failUnless(sel.is_text_present("aff4:/C.0000000000000001"))
    self.failUnless(sel.is_text_present("HostC.0000000000000001"))

    sel.click("css=td.sorting_1 > span")
    self.assertEqual("HostC.0000000000000001", sel.get_text("select_button"))
    sel.click("css=span.flapLabel")

    self.WaitUntil(sel.is_element_present, "css=div.label")
    sel.click("css=div.label")
    self.WaitUntil(sel.is_element_present, "css=a.label")
    sel.click("css=a.label")
    self.WaitUntil(sel.is_element_present, "id=_Processes")
    self.failUnless(sel.is_element_present("id=_Processes"))
    sel.click("css=ins.jstree-icon")
    self.WaitUntil(sel.is_element_present, "link=ListProcesses")

    self.assertEqual("ListProcesses", sel.get_text("link=ListProcesses"))
    sel.click("link=ListProcesses")
    self.WaitUntil(sel.is_element_present, "css=input#submit[value=Launch]")
    self.failUnless(sel.is_text_present("aff4:/C.0000000000000001"))
    self.failUnless(sel.is_text_present("Prototype: ListProcesses()"))
    sel.click("submit")
    self.WaitUntil(sel.is_element_present, "css=input#submit[value=Back]")
    self.failUnless(sel.is_text_present("Launched flow ListProcesses"))
    self.failUnless(sel.is_text_present("client_id = aff4:/C.0000000000000001"))

    sel.click("submit")
    self.WaitUntil(sel.is_element_present, "css=input#submit[value=Launch]")
    self.assertEqual("Client ID", sel.get_text("css=td.proto_key"))
    sel.click("css=#_Network > ins.jstree-icon")
    self.WaitUntil(sel.is_element_present, "link=NetstatFlow")
    self.assertEqual("NetstatFlow", sel.get_text("link=NetstatFlow"))
    sel.click("css=#_Browser > ins.jstree-icon")

    # Check that we can get a file in chinese
    sel.click("css=#_Filesystem > ins.jstree-icon")
    self.WaitUntil(sel.is_element_present, "link=GetFile")
    sel.click("link=GetFile")
    self.WaitUntil(sel.is_element_present, "css=input[name=v_path]")
    sel.type("css=input[name=v_path]", u"/dev/c/msn升级程序[1].exe")
    sel.click("submit")

    self.WaitUntil(sel.is_text_present, "Launched flow GetFile with parameters")
