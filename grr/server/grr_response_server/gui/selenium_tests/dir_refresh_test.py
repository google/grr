#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Test the vfs refreshing functionality."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from flaky import flaky

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import transfer
from grr_response_server.gui import gui_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class DirRefreshTest(gui_test_lib.GRRSeleniumTest):

  def setUp(self):
    super(DirRefreshTest, self).setUp()
    # Prepare our fixture.
    self.client_id = "C.0000000000000001"
    fixture_test_lib.ClientFixture(self.client_id)
    gui_test_lib.CreateFileVersions(self.client_id)
    self.RequestAndGrantClientApproval("C.0000000000000001")

  def _RunUpdateFlow(self, client_id):
    gui_test_lib.CreateFileVersion(
        client_id,
        "fs/os/c/a.txt",
        "Hello World".encode("utf-8"),
        timestamp=gui_test_lib.TIME_0)
    gui_test_lib.CreateFolder(
        client_id, "fs/os/c/TestFolder", timestamp=gui_test_lib.TIME_0)
    gui_test_lib.CreateFolder(
        client_id, "fs/os/c/bin/TestBinFolder", timestamp=gui_test_lib.TIME_0)

    flow_test_lib.FinishAllFlowsOnClient(
        client_id,
        client_mock=action_mocks.MultiGetFileClientMock(),
        check_flow_errors=False)

  # NOTE: sometimes with headless Chrome the dropdown version selection
  # doesn't get updated.
  @flaky
  def testRefreshFileStartsFlow(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/Downloads/")

    # Select a file and start a flow by requesting a newer version.
    self.Click("css=tr:contains(\"a.txt\")")
    self.Click("css=li[heading=Download]")
    self.Click("css=button:contains(\"Collect from the client\")")

    # Create a new file version (that would have been created by the flow
    # otherwise) and finish the flow.

    # Make sure that the flow has started (when button is clicked, the HTTP
    # API request is sent asynchronously).
    def MultiGetFileStarted():
      return compatibility.GetName(transfer.MultiGetFile) in [
          f.flow_class_name for f in data_store.REL_DB.ReadAllFlowObjects(
              client_id=self.client_id)
      ]

    self.WaitUntil(MultiGetFileStarted)

    flow_test_lib.FinishAllFlowsOnClient(
        self.client_id, check_flow_errors=False)

    time_in_future = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(
        1, rdfvalue.HOURS)
    # We have to make sure that the new version will not be within a second
    # from the current one, otherwise the previous one and the new one will
    # be indistinguishable in the UI (as it has a 1s precision when
    # displaying versions).
    gui_test_lib.CreateFileVersion(
        self.client_id,
        "fs/os/c/Downloads/a.txt",
        "The newest version!".encode("utf-8"),
        timestamp=time_in_future)

    # Once the flow has finished, the file view should update and add the
    # newly created, latest version of the file to the list. The selected
    # option should still be "HEAD".
    self.WaitUntilContains("HEAD", self.GetText,
                           "css=.version-dropdown > option[selected]")

    # The file table should also update and display the new timestamp.
    self.WaitUntilContains(
        gui_test_lib.DateTimeString(time_in_future), self.GetText,
        "css=.version-dropdown > option:nth(1)")

    # The file table should also update and display the new timestamp.
    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-file-table tbody > tr td:contains(\"%s\")" %
        (gui_test_lib.DateTimeString(time_in_future)))

    # Make sure the file content has changed.
    self.Click("css=li[heading=TextView]")
    self.WaitUntilContains("The newest version!", self.GetText,
                           "css=div.monospace pre")

    # Go to the flow management screen and check that there was a new flow.
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=grr-flows-list tr:contains('MultiGetFile')")
    self.WaitUntilContains(transfer.MultiGetFile.__name__, self.GetText,
                           "css=#main_bottomPane")

    self.WaitUntilContains(
        "c/Downloads/a.txt", self.GetText,
        "css=#main_bottomPane table > tbody td.proto_key:contains(\"Path\") "
        "~ td.proto_value")

  def testRefreshDirectoryStartsFlow(self):
    # Open VFS view for client 1.
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/Users/Shared/")

    # Grab the root directory again - should produce an Interrogate flow.
    self.Click("css=button#refresh-dir:not([disabled])")

    # Check that the button got disabled.
    self.WaitUntil(self.IsElementPresent,
                   "css=button[id=refresh-dir][disabled]")

    # Go to the flow management screen.
    self.Click("css=a[grrtarget='client.flows']")

    self.Click("css=grr-flows-list tr:contains('ListDirectory')")
    self.WaitUntilContains(filesystem.ListDirectory.__name__, self.GetText,
                           "css=#main_bottomPane")
    self.WaitUntilContains(
        "/Users/Shared", self.GetText,
        "css=#main_bottomPane table > tbody td.proto_key:contains(\"Path\") "
        "~ td.proto_value")

  # NOTE: sometimes with headless Chrome the button doesn't get
  # reenabled.
  @flaky
  def testRefreshButtonGetsDisabledWhileUpdateIsRunning(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")

    self.Click("css=button[id=refresh-dir]:not([disabled])")
    # Check that the button got disabled.
    self.WaitUntil(self.IsElementPresent,
                   "css=button[id=refresh-dir][disabled]")

    self._RunUpdateFlow(self.client_id)

    # Ensure that refresh button is enabled again.
    #
    self.WaitUntilNot(self.IsElementPresent,
                      "css=button[id=refresh-dir][disabled]")

  def testSwitchingFoldersWhileRefreshingEnablesRefreshButton(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")

    self.Click("css=button[id=refresh-dir]:not([disabled])")
    # Check that the button got disabled.
    self.WaitUntil(self.IsElementPresent,
                   "css=button[id=refresh-dir][disabled]")

    self.Click("css=#_fs-os-c-bin a")

    # Ensure that refresh button is enabled again.
    #
    self.WaitUntilNot(self.IsElementPresent,
                      "css=button[id=refresh-dir][disabled]")

  # NOTE: sometimes with headless Chrome the files list doesn't
  # get updated in time.
  @flaky
  def testTreeAndFileListRefreshedWhenRefreshCompletes(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")

    self.Click("css=button[id=refresh-dir]:not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[id=refresh-dir][disabled]")

    self._RunUpdateFlow(self.client_id)

    # The flow should be finished now, and file/tree lists update should
    # be triggered.
    # Ensure that the tree got updated as well as files list.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('TestFolder')")
    self.WaitUntil(self.IsElementPresent,
                   "css=#_fs-os-c-TestFolder i.jstree-icon")

  def testTreeAndFileListRefreshedWhenRefreshCompletesWhenSelectionChanged(
      self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.Click("css=button[id=refresh-dir]:not([disabled])")

    # Change the selection while the update is in progress.
    self.WaitUntil(self.IsElementPresent,
                   "css=button[id=refresh-dir][disabled]")

    self.Click("css=#_fs-os-c-bin a")

    self._RunUpdateFlow(self.client_id)

    # The flow should be finished now, and directory tree update should
    # be triggered, even though the selection has changed during the update.
    #
    # Ensure that the tree got updated as well as files list.
    self.WaitUntil(self.IsElementPresent,
                   "css=#_fs-os-c-TestFolder i.jstree-icon")

  def testClickingOnTreeNodeRefreshesChildrenFoldersList(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.WaitUntilNot(self.IsElementPresent, "link=foo")

    gui_test_lib.CreateFolder(
        self.client_id, "fs/os/c/foo", timestamp=gui_test_lib.TIME_0)

    self.Click("link=c")
    self.WaitUntil(self.IsElementPresent, "link=foo")

  def testClickingOnTreeNodeArrowRefreshesChildrenFoldersList(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.WaitUntil(self.IsElementPresent, "link=Downloads")
    self.WaitUntilNot(self.IsElementPresent, "link=foo")

    gui_test_lib.CreateFolder(
        self.client_id, "fs/os/c/foo", timestamp=gui_test_lib.TIME_0)

    # Click on the arrow icon, it should close the tree branch.
    self.Click("css=#_fs-os-c i.jstree-icon")
    self.WaitUntilNot(self.IsElementPresent, "link=Downloads")
    self.WaitUntilNot(self.IsElementPresent, "link=foo")

    # Click on the arrow icon again, it should reopen the tree
    # branch. It should be updated.
    self.Click("css=#_fs-os-c i.jstree-icon")
    self.WaitUntil(self.IsElementPresent, "link=Downloads")
    self.WaitUntil(self.IsElementPresent, "link=foo")


if __name__ == "__main__":
  app.run(test_lib.main)
