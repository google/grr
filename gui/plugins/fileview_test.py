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
    # Open the main page
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

    # Navigate to the bin C.0000000000000001 directory
    self.WaitUntil(sel.is_element_present, "link=bin C.0000000000000001")
    sel.click("link=bin C.0000000000000001")

    # Filter the table for bash (should match both bash and rbash)
    sel.type("css=input[type=text]", "bash")
    sel.key_up("css=input[type=text]", "h")
    self.WaitUntilEqual("rbash", sel.get_text, "css=tr:nth(2) span")
    self.assertEqual(
        2, sel.get_css_count("css=#main_rightTopPane  tbody > tr"))
    self.assertEqual("bash", sel.get_text("css=tr:nth(1) span"))
    self.assertEqual("rbash", sel.get_text("css=tr:nth(2) span"))

    # If we anchor cat at the start should only filter one.
    sel.type("css=input[type=text]", "^cat")
    sel.key_up("css=input[type=text]", "t")
    self.WaitUntilEqual("cat", sel.get_text, "css=tr:nth(1) span")
    self.assertEqual(
        1, sel.get_css_count("css=#main_rightTopPane  tbody > tr"))
    sel.click("css=tr:nth(1)")
    self.WaitUntilEqual("aff4:/C.0000000000000001/fs/os/"
                        "c/bin C.0000000000000001/cat",
                        sel.get_text, "css=h3")
    self.failUnless(sel.is_text_present("1026267"))

    # Lets download it.
    sel.click("css=span:contains(\"Download\")")
    self.WaitUntil(sel.is_element_present,
                   "css=span:contains(\"Get a new Version\")")
    sel.click("css=span:contains(\"Get a new Version\")")
    sel.click("path_0")
    self.WaitUntilEqual("fs", sel.get_text, "css=tr:nth(1) span")
    self.WaitUntilEqual("Error", sel.get_text, "css=h1")
    self.failUnless(
        sel.is_text_present("aff4:/C.0000000000000001 does not appear"
                            " to be a file object."))
    sel.click("css=span:contains(\"Stats\")")
    self.WaitUntilEqual("aff4:/C.0000000000000001", sel.get_text, "css=h3")

    # Grab the root directory again - should produce an Interrogate flow.
    sel.click("css=button[id^=refresh]")

    # Go to the flow management screen.
    sel.click("css=span.flapLabel")
    self.WaitUntil(sel.is_text_present, "Flow Management")
    sel.click("css=div:contains(\"Flow Management\") + span")
    self.WaitUntil(sel.is_element_present, "link=Manage launched flows")
    sel.click("link=Manage launched flows")

    # Check that GetFile is for the cat file.
    self.WaitUntilEqual("GetFile", sel.get_text,
                        "//table/tbody/tr[1]/td[4]")
    sel.click("//table/tbody/tr[1]/td[4]")

    self.WaitUntilEqual(
        "path:/c/bin C.0000000000000001/cat pathtype:0",
        sel.get_text, "css=table > tbody td.proto_value:contains(\"path\")")

    # Check that the older event is Interrogate
    self.assertEqual("Interrogate",
                     sel.get_text("//table/tbody/tr[2]/td[4]"))
