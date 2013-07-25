#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the flow_management interface."""


from grr.gui import runtests_test

from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib import type_info


class RecursiveTestFlow(flow.GRRFlow):
  """A test flow which starts some subflows."""

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Integer(
          name="depth",
          default=0))

  @flow.StateHandler(next_state="End")
  def Start(self):
    if self.state.depth < 2:
      for _ in range(2):
        self.CallFlow("RecursiveTestFlow", depth=self.state.depth+1,
                      next_state="End")


class TestFlowManagement(test_lib.GRRSeleniumTest):
  """Test the flow management GUI."""

  def testFlowManagement(self):
    """Test that scheduling flows works."""
    with self.ACLChecksDisabled():
      self.GrantClientApproval("C.0000000000000001")

    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # First screen should be the Host Information already.
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

    self.Click("css=a[grrtarget=LaunchFlows]")
    self.Click("css=#_Processes")

    self.assertEqual("ListProcesses", self.GetText("link=ListProcesses"))
    self.Click("link=ListProcesses")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    self.WaitUntil(self.IsTextPresent, "Prototype: ListProcesses")

    self.Click("css=input[value=Launch]")
    self.WaitUntil(self.IsTextPresent, "Launched flow ListProcesses")
    self.WaitUntil(self.IsTextPresent, "aff4:/C.0000000000000001/flows/")

    self.Click("css=input[value=Back]")
    self.WaitUntil(self.IsElementPresent, "css=input[value=Launch]")
    self.assertEqual("C.0000000000000001",
                     self.GetText("css=.FormBody .uneditable-input"))
    self.Click("css=#_Network")
    self.assertEqual("Netstat", self.GetText("link=Netstat"))
    self.Click("css=#_Browser")

    # Check that we can get a file in chinese
    self.Click("css=#_Filesystem")
    self.Click("link=GetFile")

    self.Type("css=input[name=v_pathspec_path]", u"/dev/c/msn升级程序[1].exe")
    self.Click("css=input[value=Launch]")

    self.WaitUntil(self.IsTextPresent, "Launched flow GetFile")

    # Test that recursive tests are shown in a tree table.
    flow.GRRFlow.StartFlow(
        "aff4:/C.0000000000000001", "RecursiveTestFlow", token=self.token)

    self.Click("css=a:contains('Manage launched flows')")

    self.WaitUntilEqual("RecursiveTestFlow", self.GetText,
                        "//table/tbody/tr[1]/td[3]")

    self.WaitUntilEqual("GetFile", self.GetText,
                        "//table/tbody/tr[2]/td[3]")

    # Check that child flows are not shown.
    self.assertNotEqual(self.GetText("//table/tbody/tr[2]/td[3]"),
                        "RecursiveTestFlow")

    # Click on the first tree_closed to open it.
    self.Click("css=.tree_closed")

    self.WaitUntilEqual("RecursiveTestFlow", self.GetText,
                        "//table/tbody/tr[1]/td[3]")

    self.WaitUntilEqual("RecursiveTestFlow", self.GetText,
                        "//table/tbody/tr[2]/td[3]")

    # Select the requests tab
    self.Click("Requests")
    self.Click("css=td:contains(GetFile)")

    self.WaitUntil(self.IsElementPresent,
                   "css=td:contains(flow:request:00000001)")

    # Check that a StatFile client action was issued as part of the GetFile
    # flow.
    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains(StatFile)")

  def testCancelFlowWorksCorrectly(self):
    """Tests that cancelling flows works."""

    with self.ACLChecksDisabled():
      self.GrantClientApproval("C.0000000000000001")

    flow.GRRFlow.StartFlow("aff4:/C.0000000000000001", "RecursiveTestFlow",
                           token=self.token)

    # Open client and find the flow
    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")
    self.Click("css=td:contains('0001')")
    self.Click("css=a:contains('Manage launched flows')")

    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=button[name=cancel_flow]")

    # The window should be updated now
    self.WaitUntil(self.IsTextPresent, "Cancelled in GUI")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
