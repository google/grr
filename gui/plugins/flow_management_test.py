#!/usr/bin/env python
"""Test the flow_management interface."""


import os

from grr.gui import runtests_test

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.flows.general import filesystem as flows_filesystem
from grr.lib.flows.general import processes as flows_processes
from grr.lib.flows.general import transfer as flows_transfer
from grr.lib.flows.general import webhistory as flows_webhistory
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
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

  def setUp(self):
    super(TestFlowManagement, self).setUp()

    with self.ACLChecksDisabled():
      self.client_id = rdf_client.ClientURN("C.0000000000000001")
      self.GrantClientApproval(self.client_id)
      self.action_mock = action_mocks.ActionMock(
          "TransferBuffer", "StatFile", "HashFile", "HashBuffer")

  def testFlowManagement(self):
    """Test that scheduling flows works."""
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

    # Some rows are present in the DOM but hidden because parent flow row
    # wasn't expanded yet. Due to this, we have to explicitly filter rows
    # with "visible" jQuery filter.
    self.WaitUntilEqual("RecursiveTestFlow", self.GetText,
                        "css=grr-client-flows-list tr:visible:nth(1) td:nth(2)")

    self.WaitUntilEqual("GetFile", self.GetText,
                        "css=grr-client-flows-list tr:visible:nth(2) td:nth(2)")

    # Click on the first tree_closed to open it.
    self.Click("css=grr-client-flows-list tr:visible:nth(1) .tree_closed")

    self.WaitUntilEqual("RecursiveTestFlow", self.GetText,
                        "css=grr-client-flows-list tr:visible:nth(2) td:nth(2)")

    # Select the requests tab
    self.Click("css=td:contains(GetFile)")
    self.Click("css=li[heading=Requests]")

    self.WaitUntil(self.IsElementPresent,
                   "css=td:contains(flow:request:00000001)")

    # Check that a StatFile client action was issued as part of the GetFile
    # flow.
    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains(StatFile)")

  def testLogsCanBeOpenedByClickingOnLogsTab(self):
    # RecursiveTestFlow doesn't send any results back.
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "RecursiveTestFlow", self.action_mock,
          client_id=self.client_id, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=li[heading=Log]")

    self.WaitUntil(self.IsTextPresent, "Subflow call 1")
    self.WaitUntil(self.IsTextPresent, "Subflow call 0")

  def testResultsAreDisplayedInResultsTab(self):
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneStatEntryResult", self.action_mock,
          client_id=self.client_id, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "aff4:/some/unique/path")

  def testEmptyTableIsDisplayedInResultsWhenNoResults(self):
    with self.ACLChecksDisabled():
      flow.GRRFlow.StartFlow(flow_name="FlowWithOneStatEntryResult",
                             client_id=self.client_id, sync=False,
                             token=self.token)

    self.Open("/#c=" + self.client_id.Basename())
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsElementPresent, "css=#main_bottomPane table thead "
                   "th:contains('Value')")

  def testExportTabIsEnabledForStatEntryResults(self):
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneStatEntryResult", self.action_mock,
          client_id=self.client_id, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneStatEntryResult')")
    self.Click("css=li[heading=Results]")
    self.Click("link=Show GRR export tool command")

    self.WaitUntil(
        self.IsTextPresent,
        "--username test --reason 'Running tests' collection_files "
        "--path aff4:/C.0000000000000001/analysis/FlowWithOneStatEntryResult")

  def testExportCommandIsNotDisabledWhenNoResults(self):
    # RecursiveTestFlow doesn't send any results back.
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "RecursiveTestFlow", self.action_mock,
          client_id=self.client_id, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-flow-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show GRR export tool command")

  def testExportCommandIsNotShownForNonFileResults(self):
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneNetworkConnectionResult", self.action_mock,
          client_id=self.client_id, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneNetworkConnectionResult')")
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-flow-results:contains('Value')")
    self.WaitUntilNot(self.IsTextPresent, "Show GRR export tool command")

  def testCancelFlowWorksCorrectly(self):
    """Tests that cancelling flows works."""
    flow.GRRFlow.StartFlow(client_id=self.client_id,
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

  def testDoesNotShowGenerateArchiveButtonForNonExportableRDFValues(self):
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneNetworkConnectionResult", self.action_mock,
          client_id=self.client_id, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('FlowWithOneNetworkConnectionResult')")
    self.Click("link=Results")

    self.WaitUntil(self.IsTextPresent, "42")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testDoesNotShowGenerateArchiveButtonWhenResultsCollectionIsEmpty(self):
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "RecursiveTestFlow", self.action_mock, client_id=self.client_id,
          token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("link=Results")

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testShowsGenerateArchiveButtonForGetFileFlow(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "GetFile", self.action_mock, client_id=self.client_id,
          pathspec=pathspec, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")

    self.WaitUntil(self.IsTextPresent,
                   "Files referenced in this collection can be downloaded")

  def testGenerateArchiveButtonGetsDisabledAfterClick(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          "GetFile", self.action_mock, client_id=self.client_id,
          pathspec=pathspec, token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")
    self.Click("css=button.DownloadButton")

    self.WaitUntil(self.IsElementPresent,
                   "css=button.DownloadButton[disabled]")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

  def testStartsArchiveGenerationWhenGenerateArchiveButtonIsClicked(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    flow_urn = flow.GRRFlow.StartFlow(flow_name="GetFile",
                                      client_id=self.client_id,
                                      pathspec=pathspec,
                                      token=self.token)

    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          flow_urn, self.action_mock, client_id=self.client_id,
          pathspec=pathspec, token=self.token):
        pass
      flow_results_urn = aff4.FACTORY.Open(
          flow_urn, token=self.token).GetRunner().output_urn

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")
    self.Click("css=button.DownloadButton")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

    with self.ACLChecksDisabled():
      flows_dir = aff4.FACTORY.Open(self.client_id.Add("flows"))
      flows = list(flows_dir.OpenChildren())
      export_flows = [
          f for f in flows
          if f.__class__.__name__ == "ExportCollectionFilesAsArchive"]
      self.assertEqual(len(export_flows), 1)
      self.assertEqual(export_flows[0].args.collection_urn, flow_results_urn)

  def testShowsNotificationWhenArchiveGenerationIsDone(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    flow_urn = flow.GRRFlow.StartFlow(flow_name="GetFile",
                                      client_id=self.client_id,
                                      pathspec=pathspec,
                                      token=self.token)

    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(
          flow_urn, self.action_mock, client_id=self.client_id,
          token=self.token):
        pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")
    self.Click("css=button.DownloadButton")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

    with self.ACLChecksDisabled():
      flows_dir = aff4.FACTORY.Open(self.client_id.Add("flows"))
      flows = list(flows_dir.OpenChildren())
      export_flows = [
          f for f in flows
          if f.__class__.__name__ == "ExportCollectionFilesAsArchive"]
      export_flow_urn = export_flows[0].urn

    self.Click("css=#notification_button")
    self.WaitUntil(self.IsTextPresent, "File transferred successfully")
    self.WaitUntilNot(self.IsTextPresent, "ready for download")
    self.Click("css=button:contains('Close')")

    with self.ACLChecksDisabled():
      for _ in test_lib.TestFlowHelper(export_flow_urn, token=self.token):
        pass

    self.Click("css=#notification_button")
    self.Click("css=tr:contains('ready for download')")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
