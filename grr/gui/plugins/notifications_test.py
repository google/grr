#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Test the fileview interface."""


from grr.gui import runtests_test
from grr.gui.api_plugins.client import ApiSearchClientsHandler

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.flows.general import discovery


class TestNotifications(test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  @classmethod
  def GenerateNotifications(cls):
    """Generates fake notifications of different notification types."""
    token = access_control.ACLToken(username="test", reason="test fixture")
    session_id = flow.GRRFlow.StartFlow(
        client_id="aff4:/C.0000000000000001",
        flow_name=discovery.Interrogate.__name__,
        token=token)

    with aff4.FACTORY.Open(session_id, mode="rw", token=token) as flow_obj:
      # Discovery
      flow_obj.Notify("Discovery", "aff4:/C.0000000000000001",
                      "Fake discovery message")

      # ViewObject: VirtualFileSystem
      flow_obj.Notify("ViewObject",
                      "aff4:/C.0000000000000001/fs/os/proc/10/exe",
                      "File fetch completed")

      # ViewObject: Flow
      flow_obj.Notify("ViewObject", flow_obj.urn, "Fake view flow message")

      # FlowError
      flow_obj.GetRunner().Error("Fake flow error")

      # Generate temp file and notification
      file_urn = "aff4:/tmp/foo/bar"
      with aff4.FACTORY.Create(file_urn,
                               aff4.AFF4MemoryStream,
                               token=token) as fd:
        fd.Write("hello")

      flow_obj.Notify("DownloadFile", file_urn, "Fake file download message.")

    return session_id

  def setUp(self):
    super(TestNotifications, self).setUp()

    # Have something for us to look at.
    with self.ACLChecksDisabled():
      self.session_id = self.GenerateNotifications()
      self.RequestAndGrantClientApproval("C.0000000000000001")

  def testNotifications(self):
    """Test the notifications interface."""
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")

    # There should be 6 notifications ready (5 that we generate + 1 about
    # approval).
    self.WaitUntilEqual("6", self.GetText, "css=button[id=notification_button]")

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
    self.ClickUntil("css=td:contains('File fetch completed')",
                    self.IsElementPresent, "css=li[id=_fs-os-proc-10]")

    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a[grrtarget='client.vfs']")

    # The tree is opened to the correct place
    self.WaitUntil(self.IsElementPresent, "css=li[id=_fs-os-proc-10]")

    # TODO(user): We should not need to click on the file here again. This
    # is only required since we need to support both legacy and Angular VFS
    # implementation. Once we deprecated the legacy implementation, this line
    # can be removed.
    self.Click("css=td:contains(exe)")

    # The stats pane shows the target file
    self.WaitUntilContains("aff4:/C.0000000000000001/fs/os/proc/10/exe",
                           self.GetText, "css=.tab-content h3")

    # Now select a FlowStatus notification,
    # should navigate to the broken flow.
    self.Click("css=button[id=notification_button]")

    self.WaitUntilContains("terminated due to error", self.GetText,
                           "css=td:contains('error')")

    self.ClickUntil("css=td:contains('terminated due to error')",
                    self.IsTextPresent, "Flow Information")

    # The navigation bar should manage the flows
    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a[grrtarget='client.flows']")

    # The stats pane shows the relevant flow
    self.WaitUntilContains(self.session_id, self.GetText, "css=.tab-content h3")

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

  def testClickOnDownloadFileNotificationLeadsToImmediateFileDownload(self):
    file_urn = "aff4:/tmp/foo/bar"
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(file_urn,
                               aff4.AFF4MemoryStream,
                               token=self.token) as fd:
        fd.Write("hello")

      self._SendNotification(notification_type="DownloadFile",
                             subject=file_urn,
                             message="Here is your file, sir.")

    self.Open("/")
    self.Click("css=button[id=notification_button]")

    self.Click("css=td:contains('Here is your file, sir.')")
    self.WaitUntil(self.FileWasDownloaded)

  def testServerErrorShowsErrorButton(self):

    # This is ugly :( Django gets confused when you import in the wrong order
    # though and fileview imports the Django http module so we have to delay
    # import until the Django server is properly set up.
    # pylint: disable=g-import-not-at-top
    from grr.gui.plugins.configuration_view import ConfigFileTableToolbar

    # pylint: enable=g-import-not-at-top

    # pylint: disable=unused-argument
    def MockLayout(self, request, response):
      """Fake layout method to force an exception."""
      raise RuntimeError("This is a forced exception")

    # By mocking out Layout, we can force an exception.
    with self.ACLChecksDisabled():
      with utils.Stubber(ConfigFileTableToolbar, "Layout", MockLayout):
        self.Open("/")

        #  Go to Manage Binaries, which throws an exception (see _FakeLayout).
        self.Click("css=a:contains('Manage Binaries')")

        # Open server error dialog.
        self.Click("css=button#show_backtrace")

        # Check if message and traceback are shown.
        self.WaitUntilContains("This is a forced exception", self.GetText,
                               "css=div[name=ServerErrorDialog]")
        self.WaitUntilContains("Traceback (most recent call last):",
                               self.GetText, "css=div[name=ServerErrorDialog]")

  def testServerErrorInApiShowsErrorButton(self):

    # pylint: disable=unused-argument
    def MockRender(self, args, token):
      """Fake render method to force an exception."""
      raise RuntimeError("This is a another forced exception")

    # By mocking out Handle, we can force an exception.
    with utils.Stubber(ApiSearchClientsHandler, "Handle", MockRender):
      self.Open("/")
      self.Click("client_query_submit")

      # Open server error dialog.
      self.Click("css=button#show_backtrace")

      # Check if message and traceback are shown.
      self.WaitUntilContains("This is a another forced exception", self.GetText,
                             "css=div[name=ServerErrorDialog]")
      self.WaitUntilContains("Traceback (most recent call last):", self.GetText,
                             "css=div[name=ServerErrorDialog]")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
