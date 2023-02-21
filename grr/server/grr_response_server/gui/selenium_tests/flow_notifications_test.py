#!/usr/bin/env python
"""Test flow notifications."""

import os
from unittest import mock

from absl import app

from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.flows.general import transfer as flows_transfer
from grr_response_server.gui import archive_generator
from grr_response_server.gui import gui_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestFlowNotifications(gui_test_lib.GRRSeleniumTest):
  """Test flow notifications."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.RequestAndGrantClientApproval(self.client_id)
    self.action_mock = action_mocks.FileFinderClientMock()

  def testNotificationPointingToFlowIsShownOnFlowCompletion(self):
    self.Open("/")

    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    session_id = flow_test_lib.TestFlowHelper(
        flows_transfer.GetFile.__name__,
        client_mock=self.action_mock,
        client_id=self.client_id,
        pathspec=pathspec,
        creator=self.test_username)

    # Clicking on this should show the notifications table.
    self.Click("css=button[id=notification_button]")
    self.WaitUntil(self.IsTextPresent, "Notifications")

    # Click on the "flow completed" notification.
    self.Click("css=td:contains('Flow GetFile completed')")
    self.WaitUntilNot(self.IsTextPresent, "Notifications")

    # Check that clicking on a notification changes the location and shows
    # the flow page.
    self.WaitUntilEqual("/#/clients/%s/flows/%s" % (self.client_id, session_id),
                        self.GetCurrentUrlPath)
    self.WaitUntil(self.IsTextPresent, session_id)

  def testShowsNotificationIfArchiveStreamingFailsInProgress(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    session_id = flow_test_lib.TestFlowHelper(
        flows_transfer.GetFile.__name__,
        client_mock=self.action_mock,
        client_id=self.client_id,
        pathspec=pathspec,
        creator=self.test_username)

    def RaisingStub(*unused_args, **unused_kwargs):
      yield b"foo"
      yield b"bar"
      raise RuntimeError("something went wrong")

    with mock.patch.object(archive_generator.CollectionArchiveGenerator,
                           "Generate", RaisingStub):
      self.Open("/#/clients/%s" % self.client_id)

      self.Click("css=a[grrtarget='client.flows']")
      self.Click("css=td:contains('GetFile')")
      self.Click("link=Results")
      self.Click("css=button.DownloadButton")

      self.WaitUntil(self.IsUserNotificationPresent,
                     "Archive generation failed for flow %s" % session_id)
      # There will be no failure message, as we can't get a status from an
      # iframe that triggers the download.
      self.WaitUntilNot(self.IsTextPresent,
                        "Can't generate archive: Unknown error")

  def testShowsNotificationWhenArchiveGenerationIsDone(self):
    pathspec = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test.plist"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    session_id = flow_test_lib.TestFlowHelper(
        flows_transfer.GetFile.__name__,
        client_mock=self.action_mock,
        client_id=self.client_id,
        pathspec=pathspec,
        creator=self.test_username)

    self.Open("/#/clients/%s" % self.client_id)

    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('GetFile')")
    self.Click("link=Results")
    self.Click("css=button.DownloadButton")
    self.WaitUntil(self.IsTextPresent, "Generation has started")
    self.WaitUntil(self.IsUserNotificationPresent,
                   "Downloaded archive of flow %s" % session_id)


if __name__ == "__main__":
  app.run(test_lib.main)
