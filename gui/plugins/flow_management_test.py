#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test the flow_management interface."""


from grr.gui import runtests_test

from grr.lib import action_mocks
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.flows.general import filesystem as flows_filesystem
from grr.lib.flows.general import processes as flows_processes
from grr.lib.flows.general import transfer as flows_transfer
from grr.lib.flows.general import webhistory as flows_webhistory
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2


class RecursiveTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.RecursiveTestFlowArgs


class RecursiveTestFlow(flow.GRRFlow):
  """A test flow which starts some subflows."""
  args_type = RecursiveTestFlowArgs

  @flow.StateHandler(next_state="End")
  def Start(self):
    if self.args.depth < 2:
      for i in range(2):
        self.Log("Subflow call %d", i)
        self.CallFlow("RecursiveTestFlow", depth=self.args.depth + 1,
                      next_state="End")


class FlowWithOneStatEntryResult(flow.GRRFlow):
  """Test flow that calls SendReply once with a StatEntry value."""

  @flow.StateHandler()
  def Start(self):
    self.SendReply(rdf_client.StatEntry(aff4path="aff4:/some/unique/path"))


class FlowWithOneNetworkConnectionResult(flow.GRRFlow):
  """Test flow that calls SendReply once with a NetworkConnection value."""

  @flow.StateHandler()
  def Start(self):
    self.SendReply(rdf_client.NetworkConnection(pid=42))


class TestFlowManagement(test_lib.GRRSeleniumTest):
  """Test the flow management GUI."""

  def testFlowManagement(self):
    """Test that scheduling flows works."""
    with self.ACLChecksDisabled():
      self.GrantClientApproval("C.0000000000000001")

    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # First screen should be the Host Information already.
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

    self.Click("css=a[grrtarget=LaunchFlows]")
    self.Click("css=#_Processes")
    self.Click("link=" + flows_processes.ListProcesses.__name__)
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001")

    self.WaitUntil(self.IsTextPresent, "Prototype: ListProcesses")

    self.Click("css=button.Launch")
    self.WaitUntil(self.IsTextPresent, "Launched Flow ListProcesses")

    self.Click("css=#_Browser")
    # Wait until the tree has expanded.
    self.WaitUntil(self.IsTextPresent, flows_webhistory.FirefoxHistory.__name__)

    # Check that we can get a file in chinese
    self.Click("css=#_Filesystem")

    # Wait until the tree has expanded.
    self.WaitUntil(self.IsTextPresent,
                   flows_filesystem.UpdateSparseImageChunks.__name__)

    self.Click("link=" + flows_transfer.GetFile.__name__)

    self.Select("css=.form-group:has(> label:contains('Pathtype')) select",
                "OS")
    self.Type("css=.form-group:has(> label:contains('Path')) input",
              u"/dev/c/msn[1].exe")

    self.Click("css=button.Launch")

    self.WaitUntil(self.IsTextPresent, "Launched Flow GetFile")

    # Test that recursive tests are shown in a tree table.
    flow.GRRFlow.StartFlow(
        client_id="aff4:/C.0000000000000001",
        flow_name=RecursiveTestFlow.__name__,
        token=self.token)

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

  def testLogsCanBeOpenedByClickingOnLogsTab(self):
    client_id = rdf_client.ClientURN("C.0000000000000001")

    # RecursiveTestFlow doesn't send any results back.
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "RecursiveTestFlow", action_mocks.ActionMock(),
          client_id=client_id, token=self.token):
        pass

      self.GrantClientApproval(client_id)

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=li[renderer=FlowLogView]")

    self.WaitUntil(self.IsTextPresent, "Subflow call 1")
    self.WaitUntil(self.IsTextPresent, "Subflow call 0")

  def testResultsAreDisplayedInResultsTab(self):
    client_id = rdf_client.ClientURN("C.0000000000000001")

    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneStatEntryResult", action_mocks.ActionMock(),
          client_id=client_id, token=self.token):
        pass

      self.GrantClientApproval(client_id)

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=#Results")

    self.WaitUntil(self.IsTextPresent, "aff4:/some/unique/path")

  def testEmptyTableIsDisplayedInResultsWhenNoResults(self):
    client_id = "C.0000000000000001"
    with self.ACLChecksDisabled():
      flow.GRRFlow.StartFlow(flow_name="FlowWithOneStatEntryResult",
                             client_id=client_id, sync=False, token=self.token)
      self.GrantClientApproval(client_id)

    self.Open("/#c=" + client_id)
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=#Results")

    self.WaitUntil(self.IsElementPresent, "css=#main_bottomPane table thead "
                   "th:contains('Value')")

  def testExportTabIsEnabledForStatEntryResults(self):
    client_id = rdf_client.ClientURN("C.0000000000000001")

    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneStatEntryResult", action_mocks.ActionMock(),
          client_id=client_id, token=self.token):
        pass

      self.GrantClientApproval(client_id)

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=#Export")

    self.WaitUntil(
        self.IsTextPresent,
        "--username test --reason 'Running tests' collection_files "
        "--path aff4:/C.0000000000000001/analysis/FlowWithOneStatEntryResult")

  def testExportTabIsDisabledWhenNoResults(self):
    client_id = rdf_client.ClientURN("C.0000000000000001")

    # RecursiveTestFlow doesn't send any results back.
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "RecursiveTestFlow", action_mocks.ActionMock(),
          client_id=client_id, token=self.token):
        pass

      self.GrantClientApproval(client_id)

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.WaitUntil(self.IsElementPresent, "css=#Export.disabled")

  def testExportTabIsDisabledForNonFileResults(self):
    client_id = rdf_client.ClientURN("C.0000000000000001")

    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneNetworkConnectionResult", action_mocks.ActionMock(),
          client_id=client_id, token=self.token):
        pass

      self.GrantClientApproval(client_id)

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneNetworkConnectionResult')")
    self.WaitUntil(self.IsElementPresent, "css=#Export.disabled")

  def testCancelFlowWorksCorrectly(self):
    """Tests that cancelling flows works."""

    with self.ACLChecksDisabled():
      self.GrantClientApproval("C.0000000000000001")

    flow.GRRFlow.StartFlow(client_id="aff4:/C.0000000000000001",
                           flow_name="RecursiveTestFlow",
                           token=self.token)

    # Open client and find the flow
    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")
    self.Click("css=td:contains('0001')")
    self.Click("css=a:contains('Manage launched flows')")

    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=button[name=cancel_flow]")

    # The window should be updated now
    self.WaitUntil(self.IsTextPresent, "Cancelled in GUI")

  def testGlobalFlowManagement(self):
    """Test that scheduling flows works."""
    with self.ACLChecksDisabled():
      self.CreateAdminUser("test")

    self.Open("/")

    self.Click("css=a[grrtarget=GlobalLaunchFlows]")
    self.Click("css=#_Reporting")

    self.assertEqual("RunReport", self.GetText("link=RunReport"))
    self.Click("link=RunReport")
    self.WaitUntil(self.IsTextPresent, "Report name")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
