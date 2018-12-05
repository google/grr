#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests acl policies when approvals system is disabled."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags

from grr_response_server.gui import gui_test_lib

from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestWorkflowWithoutApprovals(gui_test_lib.GRRSeleniumTest):
  """Tests acl policies when approvals system is not used."""

  def setUp(self):
    super(TestWorkflowWithoutApprovals, self).setUp()
    self.client_id = self.SetupClient(0).Basename()
    self.UninstallACLChecks()

  def testHostInformationDoesNotAskForApproval(self):
    self.Open("/#/clients/%s" % self.client_id)

    # Make sure "Host Information" tab got shown.
    self.WaitUntil(self.IsTextPresent, "Last Local Clock")
    self.WaitUntil(self.IsTextPresent, "GRR Client Version")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")

  def testBrowseVirtualFileSystemDoesNotAskForApproval(self):
    self.Open("/#/clients/%s" % self.client_id)

    # Clicking on the navigator link explicitly to make sure it's not disabled.
    self.Click("css=a[grrtarget='client.vfs']")

    # Make sure "Browse Virtual Filesystem" pane is displayed.
    self.WaitUntil(
        self.IsTextPresent, "Please select a file or a folder to "
        "see its details here.")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")

  def testStartFlowDoesNotAskForApproval(self):
    self.Open("/#/clients/%s" % self.client_id)

    # Clicking on the navigator link explicitly to make sure it's not disabled.
    self.Click("css=a[grrtarget='client.launchFlows']")

    # Make sure "Start new flows" pane is displayed.
    self.WaitUntil(self.IsTextPresent, "Please Select a flow to launch")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")

  def testManageLaunchedFlowsDoesNotAskForApproval(self):
    self.Open("/#/clients/%s" % self.client_id)

    # Clicking on the navigator link explicitly to make sure it's not disabled.
    self.Click("css=a[grrtarget='client.flows']")

    # Make sure "Manage launched flows" pane is displayed.
    self.WaitUntil(self.IsTextPresent,
                   "Please select a flow to see its details here.")

    self.WaitUntilNot(self.IsElementPresent,
                      "css=h3:contains('Create a new approval')")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
