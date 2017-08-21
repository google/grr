#!/usr/bin/env python
"""Test the flow archive."""

import os


import mock
import unittest
from grr.gui import api_call_handler_utils
from grr.gui import api_call_router_with_approval_checks
from grr.gui import gui_test_lib
from grr.gui.api_plugins import flow as api_flow

from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import aff4
from grr.server import flow
from grr.server.flows.general import transfer as flows_transfer
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib


class TestFlowArchive(gui_test_lib.GRRSeleniumTest):

  def setUp(self):
    super(TestFlowArchive, self).setUp()

    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    with aff4.FACTORY.Open(
        self.client_id, mode="rw", token=self.token) as client:
      client.Set(client.Schema.HOSTNAME("HostC.0000000000000001"))
    self.RequestAndGrantClientApproval(self.client_id)
    self.action_mock = action_mocks.FileFinderClientMock()

  def testDoesNotShowGenerateArchiveButtonForNonExportableRDFValues(self):
    for _ in flow_test_lib.TestFlowHelper(
        gui_test_lib.FlowWithOneNetworkConnectionResult.__name__,
        self.action_mock,
        client_id=self.client_id,
        token=self.token):
      pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('FlowWithOneNetworkConnectionResult')")
    self.Click("link=Results")

    self.WaitUntil(self.IsTextPresent, "42")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testDoesNotShowGenerateArchiveButtonWhenResultCollectionIsEmpty(self):
    for _ in flow_test_lib.TestFlowHelper(
        gui_test_lib.RecursiveTestFlow.__name__,
        self.action_mock,
        client_id=self.client_id,
        token=self.token):
      pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('RecursiveTestFlow')")
    self.Click("link=Results")

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testShowsGenerateArchiveButtonForGetFileFlow(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    for _ in flow_test_lib.TestFlowHelper(
        flows_transfer.GetFile.__name__,
        self.action_mock,
        client_id=self.client_id,
        pathspec=pathspec,
        token=self.token):
      pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")

    self.WaitUntil(self.IsTextPresent,
                   "Files referenced in this collection can be downloaded")

  def testGenerateArchiveButtonGetsDisabledAfterClick(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    for _ in flow_test_lib.TestFlowHelper(
        flows_transfer.GetFile.__name__,
        self.action_mock,
        client_id=self.client_id,
        pathspec=pathspec,
        token=self.token):
      pass

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")
    self.Click("css=button.DownloadButton")

    self.WaitUntil(self.IsElementPresent, "css=button.DownloadButton[disabled]")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

  def testShowsErrorMessageIfArchiveStreamingFailsBeforeFirstChunkIsSent(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=flows_transfer.GetFile.__name__,
        client_id=self.client_id,
        pathspec=pathspec,
        token=self.token)

    for _ in flow_test_lib.TestFlowHelper(
        flow_urn, self.action_mock, client_id=self.client_id, token=self.token):
      pass

    def RaisingStub(*unused_args, **unused_kwargs):
      raise RuntimeError("something went wrong")

    with utils.Stubber(api_call_handler_utils.CollectionArchiveGenerator,
                       "Generate", RaisingStub):
      self.Open("/#c=C.0000000000000001")

      self.Click("css=a[grrtarget='client.flows']")
      self.Click("css=td:contains('GetFile')")
      self.Click("link=Results")
      self.Click("css=button.DownloadButton")
      self.WaitUntil(self.IsTextPresent,
                     "Can't generate archive: Unknown error")
      self.WaitUntil(
          self.IsUserNotificationPresent,
          "Archive generation failed for flow %s" % flow_urn.Basename())

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetExportedFlowResults")
  def testClickingOnDownloadAsCsvZipStartsDownload(self, mock_method):
    self.checkClickingOnDownloadAsStartsDownloadForType(mock_method, "csv-zip",
                                                        "CSV (Zipped)")

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetExportedFlowResults")
  def testClickingOnDownloadAsYamlZipStartsDownload(self, mock_method):
    self.checkClickingOnDownloadAsStartsDownloadForType(
        mock_method, "flattened-yaml-zip", "Flattened YAML (Zipped)")

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetExportedFlowResults")
  def testClickingOnDownloadAsSqliteZipStartsDownload(self, mock_method):
    self.checkClickingOnDownloadAsStartsDownloadForType(
        mock_method, "sqlite-zip", "SQLite Scripts (Zipped)")

  def checkClickingOnDownloadAsStartsDownloadForType(self, mock_method, plugin,
                                                     plugin_display_name):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=flows_transfer.GetFile.__name__,
        client_id=self.client_id,
        pathspec=pathspec,
        token=self.token)
    for _ in flow_test_lib.TestFlowHelper(
        flow_urn, self.action_mock, client_id=self.client_id, token=self.token):
      pass

    self.Open("/#/clients/C.0000000000000001/flows/%s" % flow_urn.Basename())
    self.Click("link=Results")
    self.Select("id=plugin-select", plugin_display_name)
    self.Click("css=grr-download-collection-as button[name='download-as']")

    def MockMethodIsCalled():
      try:
        mock_method.assert_called_once_with(
            api_flow.ApiGetExportedFlowResultsArgs(
                client_id=self.client_id.Basename(),
                flow_id=flow_urn.Basename(),
                plugin_name=plugin),
            token=mock.ANY)

        return True
      except AssertionError:
        return False

    self.WaitUntil(MockMethodIsCalled)

  def testDoesNotShowDownloadAsPanelIfCollectionIsEmpty(self):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=gui_test_lib.RecursiveTestFlow.__name__,
        client_id=self.client_id,
        token=self.token)
    for _ in flow_test_lib.TestFlowHelper(
        flow_urn, self.action_mock, client_id=self.client_id, token=self.token):
      pass

    self.Open("/#/clients/C.0000000000000001/flows/%s" % flow_urn.Basename())
    self.Click("link=Results")

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsElementPresent, "grr-download-collection-as")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
