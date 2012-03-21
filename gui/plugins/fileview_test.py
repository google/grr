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

from grr.lib import test_lib


class TestFileView(test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  def testFileView(self):
    """Test the fileview interface."""
    sel = self.selenium

    sel.open("/")

    self.WaitUntil(sel.is_element_present, "css=input[name=q]")
    sel.type("css=input[name=q]", "0001")
    sel.click("css=input[type=submit]")

    self.WaitUntilEqual(u"aff4:/C.0000000000000001",
                        sel.get_text, "css=span[type=subject]")

    # Choose client 1
    sel.click("css=td:contains('0001')")

    # Go to Browse VFS
    sel.click("css=a:contains('Browse Virtual Filesystem')")

    self.WaitUntil(sel.is_element_present, "css=#_fs")
    sel.click("css=#_fs ins.jstree-icon")

    self.WaitUntil(sel.is_element_present, "css=#_fs-os")
    sel.click("css=#_fs-os ins.jstree-icon")

    self.WaitUntil(sel.is_element_present, "css=#_fs-os-c")
    sel.click("css=#_fs-os-c ins.jstree-icon")

    # Test the hex viewer.
    self.WaitUntil(sel.is_element_present, "css=#_fs-os-proc")
    sel.click("css=#_fs-os-proc ins.jstree-icon")

    self.WaitUntil(sel.is_element_present, "css=#_fs-os-proc-10")
    sel.click("css=#_fs-os-proc-10 a")

    self.WaitUntil(sel.is_element_present,
                   "css=span[type=subject]:contains(\"cmdline\")")

    sel.click("css=span[type=subject]:contains(\"cmdline\")")

    sel.click("css=#HexView")

    self.WaitUntilContains("6c730068656c6c6f20776f726c6427002d6c",
                           sel.get_text, "hex_area")

    self.WaitUntilContains("ls.hello world'.-l", sel.get_text, "data_area")

    sel.click("css=a:contains(\"Stats\")")

    # Navigate to the bin C.0000000000000001 directory
    self.WaitUntil(sel.is_element_present, "link=bin C.0000000000000001")
    sel.click("link=bin C.0000000000000001")

    # Filter the table for bash (should match both bash and rbash)
    self.WaitUntil(sel.is_element_present, "css=th:contains('Name')")
    sel.click("css=th:contains('Name') img")

    sel.type("css=.sort-dialog input[type=text]", "bash")
    sel.click("css=.sort-dialog input[type=submit]")

    self.WaitUntilEqual("rbash", sel.get_text, "css=tr:nth(2) span")
    self.assertEqual(
        2, sel.get_css_count("css=#main_rightTopPane  tbody > tr"))
    self.assertEqual("bash", sel.get_text("css=tr:nth(1) span"))
    self.assertEqual("rbash", sel.get_text("css=tr:nth(2) span"))

    # Check that the previous search test is still available in the form.
    sel.click("css=th:contains('Name') img")
    self.assertEqual("bash", sel.get_value("css=.sort-dialog input"))

    # If we anchor cat at the start should only filter one.
    sel.type("css=.sort-dialog input[type=text]", "^cat")
    sel.click("css=.sort-dialog input[type=submit]")

    self.WaitUntilEqual("cat", sel.get_text, "css=tr:nth(1) span")
    self.assertEqual(
        1, sel.get_css_count("css=#main_rightTopPane  tbody > tr"))
    sel.click("css=tr:nth(1)")

    self.WaitUntilEqual("aff4:/C.0000000000000001/fs/os/"
                        "c/bin C.0000000000000001/cat",
                        sel.get_text, "css=div h3")
    self.failUnless(sel.is_text_present("1026267"))

    # Lets download it.
    sel.click("css=span:contains(\"Download\")")
    self.WaitUntil(sel.is_element_present,
                   "css=span:contains(\"Get a new Version\")")
    sel.click("css=span:contains(\"Get a new Version\")")
    sel.click("path_0")
    self.WaitUntilEqual("fs", sel.get_text, "css=tr:nth(1) span")

    sel.click("css=span:contains(\"Stats\")")
    self.WaitUntilEqual(
        "aff4:/C.0000000000000001", sel.get_text, "css=div h3")

    # Grab the root directory again - should produce an Interrogate flow.
    sel.click("css=button[id^=refresh]")

    # Go to the flow management screen.
    sel.click("css=a:contains('Manage launched flows')")

    # Check that GetFile is for the cat file.
    self.WaitUntilEqual("GetFile", sel.get_text,
                        "//table/tbody/tr[2]/td[3]")
    sel.click("//table/tbody/tr[2]/td[3]")

    self.WaitUntilContains(
        "cat",
        sel.get_text, "css=table > tbody td.proto_value:contains(\"path\")")

    # Check that the older event is Interrogate
    self.assertEqual("Interrogate",
                     sel.get_text("//table/tbody/tr[1]/td[3]"))
