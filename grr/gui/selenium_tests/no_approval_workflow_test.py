#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests acl policies when approvals system is disabled."""

import unittest
from grr.gui import gui_test_lib

from grr.lib import flags


class TestWorkflowWithoutApprovals(gui_test_lib.GRRSeleniumTest):
  """Tests acl policies when approvals system is not used."""

  def setUp(self):
    super(TestWorkflowWithoutApprovals, self).setUp()
    self.UninstallACLChecks()

  def testHostInformationDoesNotAskForApproval(self):
    self.Open("/#/clients/C.0000000000000001")

    # Make sure "Host Information" tab got shown.
    self.WaitUntil(self.IsTextPresent, "Last Local Clock")
    self.WaitUntil(self.IsTextPresent, "GRR Client Version")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")

  def testBrowseVirtualFileSystemDoesNotAskForApproval(self):
    self.Open("/#/clients/C.0000000000000001")

    # Clicking on the navigator link explicitly to make sure it's not disabled.
    self.Click("css=a[grrtarget='client.vfs']")

    # Make sure "Browse Virtual Filesystem" pane is displayed.
    self.WaitUntil(self.IsTextPresent, "Please select a file or a folder to "
                   "see its details here.")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")

  def testStartFlowDoesNotAskForApproval(self):
    self.Open("/#/clients/C.0000000000000001")

    # Clicking on the navigator link explicitly to make sure it's not disabled.
    self.Click("css=a[grrtarget='client.launchFlows']")

    # Make sure "Start new flows" pane is displayed.
    self.WaitUntil(self.IsTextPresent, "Please Select a flow to launch")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")

  def testManageLaunchedFlowsDoesNotAskForApproval(self):
    self.Open("/#/clients/C.0000000000000001")

    # Clicking on the navigator link explicitly to make sure it's not disabled.
    self.Click("css=a[grrtarget='client.flows']")

    # Make sure "Manage launched flows" pane is displayed.
    self.WaitUntil(self.IsTextPresent,
                   "Please select a flow to see its details here.")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
