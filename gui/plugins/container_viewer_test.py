#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the collection viewer interface."""


from grr.client import vfs

from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestContainerViewer(test_lib.GRRSeleniumTest):
  """Test the collection viewer interface."""

  @staticmethod
  def CreateCollectionFixture():
    """Creates a new collection we can play with."""
    # Create a client for testing
    client_id = rdfvalue.ClientURN("C.0000000000000004")
    token = access_control.ACLToken("test", "Fixture")

    fd = aff4.FACTORY.Create(client_id, "VFSGRRClient", token=token)
    fd.Set(fd.Schema.CERT(config_lib.CONFIG["Client.certificate"]))
    fd.Close()

    # Install the mock
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture
    client_mock = test_lib.ActionMock("Find")

    output_path = "analysis/FindFlowTest"

    findspec = rdfvalue.RDFFindSpec(path_regex="bash")
    findspec.pathspec.path = "/"
    findspec.pathspec.pathtype = rdfvalue.PathSpec.PathType.OS

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=client_id,
        findspec=findspec, token=token, output=output_path):
      pass

    # Make the view a bit more interesting
    fd = aff4.FACTORY.Open(client_id.Add(output_path), mode="rw", token=token)
    fd.CreateView(["stat.st_mtime", "type", "stat.st_size", "size", "Age"])
    fd.Close()

  def setUp(self):
    super(TestContainerViewer, self).setUp()

    # Create a new collection
    with self.ACLChecksDisabled():
      self.CreateCollectionFixture()
      self.GrantClientApproval("C.0000000000000004")

  def testContainerViewer(self):
    self.Open("/")

    self.Type("client_query", "0004")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000004",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0004')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")

    # Navigate to the analysis directory
    self.Click("link=analysis")

    self.Click("css=span[type=subject]:contains(\"FindFlowTest\")")

    self.WaitUntil(self.IsElementPresent, "css=td:contains(\"VIEW\")")
    self.assert_("View details" in self.GetText(
        "css=a[href=\"#"
        "c=C.0000000000000004&"
        "container=aff4%3A%2FC.0000000000000004%2Fanalysis%2FFindFlowTest&"
        "main=ContainerViewer&"
        "reason=Running+tests\"]"))

    self.Click("css=a:contains(\"View details\")")

    self.WaitUntil(self.IsElementPresent, "css=button[id=export]")

    self.ClickUntil("css=#_C_2E0000000000000004 ins.jstree-icon",
                    self.IsElementPresent,
                    "css=#_C_2E0000000000000004-fs ins.jstree-icon")
    self.ClickUntil("css=#_C_2E0000000000000004-fs ins.jstree-icon",
                    self.IsElementPresent,
                    "css=#_C_2E0000000000000004-fs-os ins.jstree-icon")
    self.ClickUntil("css=#_C_2E0000000000000004-fs-os ins.jstree-icon",
                    self.IsElementPresent,
                    "link=c")

    # Navigate to the bin C.0000000000000001 directory
    self.Click("link=c")

    # Check the filter string
    self.assertEqual("subject startswith 'aff4:/C.0000000000000004/fs/os/c/'",
                     self.GetValue("query"))

    # We should have exactly 4 files
    self.WaitUntilEqual(4, self.GetCssCount,
                        "css=.containerFileTable tbody > tr")

    # Check the rows
    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin %(client_id)s/bash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(0) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin %(client_id)s/rbash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(1) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin/bash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(2) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000004/fs/os/c/bin/rbash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(3) td:nth(1)"))

    # Check that query filtering works (Pressing enter)
    self.Type("query", "stat.st_size < 5000")
    self.Click("css=form[name=query_form] button[type=submit]")

    # This should be fixed eventually and the test turned back on.
    self.WaitUntilContains("Filtering by subfields is not implemented yet.",
                           self.GetText, "css=#footer_message")

    # self.WaitUntilEqual("4874", self.GetText,
    #                    "css=.tableContainer  tbody > tr:nth(0) td:nth(4)")

    # We should have exactly 1 file
    # self.assertEqual(
    #    1, self.GetCssCount("css=.tableContainer  tbody > tr"))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
