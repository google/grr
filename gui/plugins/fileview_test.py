#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the fileview interface."""

import time

from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib


class TestFileView(test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  @staticmethod
  def CreateFileVersions():
    """Add a new version for a file."""
    # Mock the time function.
    old_time = time.time

    # Create another file at 2012-04-07 08:53:53.
    time.time = lambda: 1333788833

    token = access_control.ACLToken()
    # This file already exists in the fixture, and we overwrite it with a new
    # version at 2012-04-07 08:53:53.
    fd = aff4.FACTORY.Create(
        "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
        "AFF4MemoryStream", mode="w", token=token)
    fd.Write("Hello World")
    fd.Close()

    # Create another version of this file at 2012-04-09 16:27:13.
    time.time = lambda: 1333988833
    fd = aff4.FACTORY.Create(
        "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
        "AFF4MemoryStream", mode="w", token=token)
    fd.Write("Goodbye World")
    fd.Close()

    # Restore the mocks.
    time.time = old_time

  def testFileView(self):
    """Test the fileview interface."""
    # Prepare our fixture.
    with self.ACLChecksDisabled():
      self.CreateFileVersions()
      self.GrantClientApproval("C.0000000000000001")

    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("css=#_fs ins.jstree-icon")
    self.Click("css=#_fs-os ins.jstree-icon")
    self.Click("css=#_fs-os-c ins.jstree-icon")

    # Test file versioning.
    self.WaitUntil(self.IsElementPresent, "css=#_fs-os-c-Downloads")
    self.Click("link=Downloads")

    # Verify that we have the latest version in the table by default
    self.assertTrue(
        "2012-04-09 16:27:13" in self.GetText("css=tr:contains(\"a.txt\")"))

    # Click on the row.
    self.Click("css=tr:contains(\"a.txt\")")
    self.WaitUntilContains("a.txt @ 2012-04-09", self.GetText,
                           "css=div#main_rightBottomPane h3")

    # Check the data in this file.
    self.Click("css=#TextView")
    self.WaitUntilContains("Goodbye World", self.GetText,
                           "css=div#text_viewer_data_content")

    # Click on the version selector.
    self.Click("css=tr:contains(\"a.txt\") img.version-selector")
    self.WaitUntilContains("Versions of", self.GetText,
                           "css=.version-selector-dialog h4")

    # Select the previous version.
    self.Click("css=td:contains(\"2012-04-07\")")

    # Make sure the file content has changed. This version has "Hello World" in
    # it.
    self.WaitUntilContains("Hello World", self.GetText,
                           "css=div#text_viewer_data_content")

    # Test the hex viewer.
    self.Click("css=#_fs-os-proc ins.jstree-icon")
    self.Click("css=#_fs-os-proc-10 a")

    self.Click("css=span[type=subject]:contains(\"cmdline\")")
    self.Click("css=#HexView")

    # TODO(user): Using GetText() this way doesn't seem to be a great idea
    # because #hex_area contains a table and we're actually aggregating text
    # across multiple cells.
    self.WaitUntilContains(
        "6c 73 00 68 65 6c 6c 6f 20 77 6f 72 6c 64 27 00 2d 6c",
        self.GetText, "hex_area")

    # TODO(user): same here - see the GetText() todo item above.
    self.WaitUntilContains("l s . h e l l o w o r l d ' . - l",
                           self.GetText, "data_area")

    self.Click("css=a:contains(\"Stats\")")

    # Navigate to the bin C.0000000000000001 directory
    self.Click("link=bin C.0000000000000001")

    # Filter the table for bash (should match both bash and rbash)
    self.WaitUntil(self.IsElementPresent, "css=td:contains('bash')")
    self.Click("css=th:contains('Name') img")

    self.Type("css=.sort-dialog input[type=text]", "bash", end_with_enter=True)

    self.WaitUntilEqual("rbash", self.GetText, "css=tr:nth(2) span")
    self.assertEqual(
        2, self.GetCssCount("css=#main_rightTopPane  tbody > tr"))
    self.assertEqual("bash", self.GetText("css=tr:nth(1) span"))
    self.assertEqual("rbash", self.GetText("css=tr:nth(2) span"))

    # Check that the previous search test is still available in the form.
    self.Click("css=th:contains('Name') img")
    self.assertEqual("bash", self.GetValue("css=.sort-dialog input"))

    # If we anchor cat at the start should only filter one.
    self.Type("css=.sort-dialog input[type=text]", "^cat", end_with_enter=True)

    self.WaitUntilEqual("cat", self.GetText, "css=tr:nth(1) span")
    self.assertEqual(
        1, self.GetCssCount("css=#main_rightTopPane  tbody > tr"))
    self.Click("css=tr:nth(1)")

    self.WaitUntilContains(
        "aff4:/C.0000000000000001/fs/os/c/bin C.0000000000000001/cat",
        self.GetText, "css=.tab-content h3")
    self.WaitUntil(self.IsTextPresent, "1026267")

    # Lets download it.
    self.Click("Download")
    self.Click("css=button:contains(\"Get a new Version\")")

    self.Click("path_0")
    self.WaitUntilEqual("fs", self.GetText, "css=tr:nth(2) span")

    self.Click("Stats")
    self.WaitUntilContains(
        "aff4:/C.0000000000000001", self.GetText, "css=.tab-content h3")

    # Grab the root directory again - should produce an Interrogate flow.
    self.Click("css=button[id^=refresh]")

    # Go to the flow management screen.
    self.Click("css=a:contains('Manage launched flows')")

    # For the client update, 2 flows have to be issued: UpdateVFSFile and
    # Interrogate. UpdateVFSFile triggers VFSGRRClient.Update() method which
    # triggers Interrogate.
    self.WaitUntilEqual("Interrogate", self.GetText,
                        "//table/tbody/tr[1]/td[3]")
    self.WaitUntilEqual("UpdateVFSFile", self.GetText,
                        "//table/tbody/tr[2]/td[3]")
    self.Click("//table/tbody/tr[2]/td[3]")
    self.WaitUntilEqual(
        "aff4:/C.0000000000000001", self.GetText,
        "css=table > tbody td.proto_key:contains(\"vfs_file_urn\") "
        "~ td.proto_value")

    # Check that UpdateVFSFile is called for the cat file.
    # During the test this file is VFSMemoryFile, so its' Update method does
    # nothing, therefore UpdateVFSFile won't issue any other flows.
    self.WaitUntilEqual("UpdateVFSFile", self.GetText,
                        "//table/tbody/tr[3]/td[3]")
    self.Click("//table/tbody/tr[3]/td[3]")
    self.WaitUntilContains(
        "cat", self.GetText,
        "css=table > tbody td.proto_key:contains(\"vfs_file_urn\") "
        "~ td.proto_value")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
