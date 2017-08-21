#!/usr/bin/env python
"""Test flow notifications."""
import os


import unittest
from grr.gui import api_call_handler_utils
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import aff4
from grr.server import flow
from grr.server.flows.general import transfer as flows_transfer
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib


class TestFlowNotifications(gui_test_lib.GRRSeleniumTest):
  """Test flow notifications."""

  def setUp(self):
    super(TestFlowNotifications, self).setUp()
    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    with aff4.FACTORY.Open(
        self.client_id, mode="rw", token=self.token) as client:
      client.Set(client.Schema.HOSTNAME("HostC.0000000000000001"))
    self.RequestAndGrantClientApproval(self.client_id)
    self.action_mock = action_mocks.FileFinderClientMock()

  def testNotificationPointingToFlowIsShownOnFlowCompletion(self):
    self.Open("/")

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

    # Clicking on this should show the notifications table.
    self.Click("css=button[id=notification_button]")
    self.WaitUntil(self.IsTextPresent, "Notifications")

    # Click on the "flow completed" notification.
    self.Click("css=td:contains('Flow GetFile completed')")
    self.WaitUntilNot(self.IsTextPresent, "Notifications")

    # Check that clicking on a notification changes the location and shows
    # the flow page.
    self.WaitUntilEqual("/#/clients/%s/flows/%s" % (self.client_id.Basename(),
                                                    flow_urn.Basename()),
                        self.GetCurrentUrlPath)
    self.WaitUntil(self.IsTextPresent, utils.SmartStr(flow_urn))

  def testShowsNotificationIfArchiveStreamingFailsInProgress(self):
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
      yield "foo"
      yield "bar"
      raise RuntimeError("something went wrong")

    with utils.Stubber(api_call_handler_utils.CollectionArchiveGenerator,
                       "Generate", RaisingStub):
      self.Open("/#c=C.0000000000000001")

      self.Click("css=a[grrtarget='client.flows']")
      self.Click("css=td:contains('GetFile')")
      self.Click("link=Results")
      self.Click("css=button.DownloadButton")

      self.WaitUntil(
          self.IsUserNotificationPresent,
          "Archive generation failed for flow %s" % flow_urn.Basename())
      # There will be no failure message, as we can't get a status from an
      # iframe that triggers the download.
      self.WaitUntilNot(self.IsTextPresent,
                        "Can't generate archive: Unknown error")

  def testShowsNotificationWhenArchiveGenerationIsDone(self):
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

    self.Open("/#c=C.0000000000000001")

    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")
    self.Click("css=button.DownloadButton")
    self.WaitUntil(self.IsTextPresent, "Generation has started")
    self.WaitUntil(self.IsUserNotificationPresent,
                   "Downloaded archive of flow %s" % flow_urn.Basename())


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
