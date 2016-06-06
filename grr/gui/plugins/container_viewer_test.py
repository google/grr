#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the collection viewer interface."""


from grr.gui import runtests_test

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib

from grr.lib.aff4_objects import collects


class TestContainerViewer(test_lib.GRRSeleniumTest):
  """Test the collection viewer interface."""

  def CreateCollectionFixture(self):
    with aff4.FACTORY.Create("aff4:/C.0000000000000001/analysis/FindFlowTest",
                             collects.AFF4Collection,
                             token=self.token) as out_fd:
      out_fd.CreateView(["stat.st_mtime", "type", "stat.st_size", "size",
                         "Age"])

      for urn in [
          "aff4:/C.0000000000000001/fs/os/c/bin C.0000000000000001/rbash",
          "aff4:/C.0000000000000001/fs/os/c/bin C.0000000000000001/bash",
          "aff4:/C.0000000000000001/fs/os/c/bin/bash",
          "aff4:/C.0000000000000001/fs/os/c/bin/rbash",
      ]:
        fd = aff4.FACTORY.Open(urn, token=self.token)
        out_fd.Add(urn=urn, stat=fd.Get(fd.Schema.STAT))

  def setUp(self):
    super(TestContainerViewer, self).setUp()

    # Create a new collection
    with self.ACLChecksDisabled():
      self.CreateCollectionFixture()
      self.RequestAndGrantClientApproval("C.0000000000000001")

  def testContainerViewer(self):
    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a[grrtarget='client.vfs']")

    # Navigate to the analysis directory
    self.Click("link=analysis")

    self.Click("css=span[type=subject]:contains(\"FindFlowTest\")")

    self.WaitUntil(self.IsElementPresent, "css=td:contains(\"VIEW\")")
    self.assertIn("View details", self.GetText(
        "css=a[href=\"#"
        "c=aff4%3A%2FC.0000000000000001&"
        "container=aff4%3A%2FC.0000000000000001%2Fanalysis%2FFindFlowTest&"
        "main=ContainerViewer&"
        "reason=Running+tests\"]"))

    self.Click("css=a:contains(\"View details\")")

    self.WaitUntil(self.IsElementPresent, "css=button[id=export]")

    self.ClickUntil("css=#_C_2E0000000000000001 i.jstree-icon",
                    self.IsElementPresent,
                    "css=#_C_2E0000000000000001-fs i.jstree-icon")
    self.ClickUntil("css=#_C_2E0000000000000001-fs i.jstree-icon",
                    self.IsElementPresent,
                    "css=#_C_2E0000000000000001-fs-os i.jstree-icon")
    self.ClickUntil("css=#_C_2E0000000000000001-fs-os i.jstree-icon",
                    self.IsElementPresent, "link=c")

    # Navigate to the bin C.0000000000000001 directory
    self.Click("link=c")

    # Check the filter string
    self.assertEqual("subject startswith 'aff4:/C.0000000000000001/fs/os/c/'",
                     self.GetValue("query"))

    # We should have exactly 4 files
    self.WaitUntilEqual(4, self.GetCssCount,
                        "css=.containerFileTable tbody > tr")

    # Check the rows
    self.assertEqual(
        "C.0000000000000001/fs/os/c/bin C.0000000000000001/bash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(0) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000001/fs/os/c/bin C.0000000000000001/rbash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(1) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000001/fs/os/c/bin/bash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(2) td:nth(1)"))

    self.assertEqual(
        "C.0000000000000001/fs/os/c/bin/rbash",
        self.GetText("css=.containerFileTable  tbody > tr:nth(3) td:nth(1)"))

    # Check that query filtering works (Pressing enter)
    self.Type("query", "stat.st_size < 5000")
    self.Click("css=form[name=query_form] button[type=submit]")

    self.WaitUntilEqual("4874", self.GetText,
                        "css=.containerFileTable tbody > tr:nth(0) td:nth(4)")

    # We should have exactly 1 file
    self.assertEqual(1, self.GetCssCount("css=.containerFileTable tbody > tr"))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
