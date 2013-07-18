#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the flow_management interface."""


from grr.lib import aff4
from grr.lib import flow
from grr.lib import hunt_test
from grr.lib import hunts
from grr.lib import rdfvalue
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
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # First screen should be the Host Information already.
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

    self.Click("css=a[grrtarget=LaunchFlows]")
    self.WaitUntil(self.IsElementPresent, "id=_Processes")
    self.Click("css=#_Processes")

    self.WaitUntil(self.IsElementPresent, "link=ListProcesses")

    self.assertEqual("ListProcesses", self.GetText("link=ListProcesses"))
    self.Click("link=ListProcesses")
    self.WaitUntil(self.IsElementPresent, "css=input[value=Launch]")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    self.WaitUntil(self.IsTextPresent, "Prototype: ListProcesses")

    self.Click("css=input[value=Launch]")
    self.WaitUntil(self.IsElementPresent, "css=input[value=Back]")
    self.WaitUntil(self.IsTextPresent, "Launched flow ListProcesses")
    self.WaitUntil(self.IsTextPresent, "aff4:/C.0000000000000001/flows/")

    self.Click("css=input[value=Back]")
    self.WaitUntil(self.IsElementPresent, "css=input[value=Launch]")
    self.assertEqual("C.0000000000000001",
                     self.GetText("css=.FormBody .uneditable-input"))
    self.Click("css=#_Network")
    self.WaitUntil(self.IsElementPresent, "link=Netstat")
    self.assertEqual("Netstat", self.GetText("link=Netstat"))
    self.Click("css=#_Browser")

    # Check that we can get a file in chinese
    self.Click("css=#_Filesystem")
    self.Click("link=GetFile")

    self.WaitUntil(self.IsElementPresent, "css=input[name=v_pathspec_path]")
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

    # There should only be 3 rows (since the child flows are not shown).
    self.assertFalse(self.IsElementPresent("//table/tbody/tr[4]"))

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

  def SetUpHunt(self):
    hunt = hunts.SampleHunt(token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    client_ids = ["C.0000000000000001"]
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    foreman.AssignTasksToClient(client_ids[0])

    # Run the hunt.
    client_mock = hunt_test.HuntTest.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)
