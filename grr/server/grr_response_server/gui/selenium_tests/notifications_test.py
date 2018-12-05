#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the fileview interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import notification
from grr_response_server.flows.general import discovery
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins.client import ApiSearchClientsHandler
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestNotifications(gui_test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  @classmethod
  def GenerateNotifications(cls, client_id, token):
    """Generates fake notifications of different notification types."""
    session_id = flow_test_lib.StartFlow(
        discovery.Interrogate, client_id=client_id, creator=token.username)

    notification.Notify(
        token.username,
        rdf_objects.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        "Fake discovery message",
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.CLIENT,
            client=rdf_objects.ClientReference(client_id=client_id.Basename())))

    # ViewObject: VirtualFileSystem
    notification.Notify(
        token.username,
        rdf_objects.UserNotification.Type.TYPE_VFS_FILE_COLLECTED,
        "File fetch completed",
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.VFS_FILE,
            vfs_file=rdf_objects.VfsFileReference(
                client_id=client_id.Basename(),
                path_type=rdf_objects.PathInfo.PathType.OS,
                path_components=["proc", "10", "exe"])))

    gui_test_lib.CreateFileVersion(
        client_id,
        "fs/os/proc/10/exe",
        b"",
        timestamp=gui_test_lib.TIME_0,
        token=token)

    # ViewObject: Flow
    notification.Notify(
        token.username,
        rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_COMPLETED,
        "Fake view flow message",
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.FLOW,
            flow=rdf_objects.FlowReference(
                client_id=client_id.Basename(), flow_id=session_id)))

    # FlowError
    if data_store.RelationalDBFlowsEnabled():
      flow_base.TerminateFlow(client_id.Basename(), session_id,
                              "Fake flow error")
    else:
      with aff4.FACTORY.Open(
          client_id.Add("flows").Add(session_id), mode="rw",
          token=token) as flow_obj:
        flow_obj.GetRunner().Error("Fake flow error")

    return session_id

  def setUp(self):
    super(TestNotifications, self).setUp()

    # Have something for us to look at.
    self.client_id = self.SetupClient(0)
    self.session_id = self.GenerateNotifications(self.client_id, self.token)
    self.RequestAndGrantClientApproval(self.client_id)

  def testNotifications(self):
    """Test the notifications interface."""
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")

    # There should be 5 notifications, 4 that we generate + 1 about
    # approval. Those are:
    #
    # - Fake discovery message.
    # - File fetch completed.
    # - Fake view flow message.
    # - Fake flow error (shows up as "Flow <id> terminated due to error").
    # and the approval
    # - approver has granted you access to GRR client...
    self.WaitUntilEqual("5", self.GetText, "css=button[id=notification_button]")

    # Clicking on this should show the table
    self.Click("css=button[id=notification_button]")

    # This should clear the notifications.
    self.Click("css=button:contains('Close')")
    self.WaitUntilEqual("0", self.GetText, "css=button[id=notification_button]")

    # Notifications should be clear even after we reload the page.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.WaitUntilEqual("0", self.GetText, "css=button[id=notification_button]")

    # Clicking on this should show the table
    self.Click("css=button[id=notification_button]")

    # Select a ViewObject notification - should navigate to the object.
    self.Click("css=td:contains('File fetch completed')")
    self.WaitUntil(self.IsElementPresent, "css=li[id=_fs-os-proc-10]")

    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a[grrtarget='client.vfs']")

    # The tree is opened to the correct place
    self.WaitUntil(self.IsElementPresent, "css=li[id=_fs-os-proc-10]")

    # The stats pane shows the target file
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-file-details:contains('proc/10/exe')")

    # Now select a FlowStatus notification,
    # should navigate to the broken flow.
    self.Click("css=button[id=notification_button]")

    self.WaitUntilContains("terminated due to error", self.GetText,
                           "css=td:contains('error')")

    self.Click("css=td:contains('terminated due to error')")
    self.WaitUntil(self.IsTextPresent, "Flow Information")

    # The navigation bar should manage the flows
    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a[grrtarget='client.flows']")

    # The stats pane shows the relevant flow
    self.WaitUntilContains(self.session_id, self.GetText,
                           "css=grr-flow-overview")

  def testUserSettings(self):
    """Tests that user settings UI is working."""
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")

    mode_selector = "css=.form-group:has(label:contains('Mode')) select"

    # Open settings dialog and change mode from BASIC to ADVANCED
    self.Click("css=grr-user-settings-button")
    self.assertEqual("ADVANCED", self.GetSelectedLabel(mode_selector).strip())

    self.Select(mode_selector, "BASIC (default)")
    self.Click("css=button[name=Proceed]")

    # Check that the mode value was saved
    self.Click("css=grr-user-settings-button")
    self.assertEqual("BASIC (default)",
                     self.GetSelectedLabel(mode_selector).strip())

  def testServerErrorInApiShowsErrorButton(self):

    def MockRender(self, args, token):  # pylint: disable=unused-argument
      """Fake render method to force an exception."""
      raise RuntimeError("This is a another forced exception")

    with self.DisableHttpErrorChecks():
      # By mocking out Handle, we can force an exception.
      with utils.Stubber(ApiSearchClientsHandler, "Handle", MockRender):
        self.Open("/")
        self.Click("client_query_submit")

        # Open server error dialog.
        self.Click("css=button#show_backtrace")

        # Check if message and traceback are shown.
        self.WaitUntilContains("This is a another forced exception",
                               self.GetText, "css=div[name=ServerErrorDialog]")
        self.WaitUntilContains("Traceback (most recent call last):",
                               self.GetText, "css=div[name=ServerErrorDialog]")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
