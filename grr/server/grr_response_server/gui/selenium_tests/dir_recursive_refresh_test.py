#!/usr/bin/env python
"""Test the vfs recursive refreshing functionality."""

from absl import app

from grr_response_server.gui import gui_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class DirRecursiveRefreshTest(gui_test_lib.GRRSeleniumTest):

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

    flow_test_lib.FinishAllFlowsOnClient(client_id)

  def setUp(self):
    super().setUp()
    # Prepare our fixture.
    self.client_id = "C.0000000000000001"
    fixture_test_lib.ClientFixture(self.client_id)
    gui_test_lib.CreateFileVersions(self.client_id)
    self.RequestAndGrantClientApproval(self.client_id)

  def testRecursiveRefreshButtonGetsDisabledWhileUpdateIsRunning(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.Click("css=button[name=RecursiveRefresh]:not([disabled])")

    self.Click("css=button[name=Proceed]")
    # Wait until the dialog is automatically closed.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.modal-header:contains('Recursive Directory Refresh')")

    # Check that the button got disabled
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RecursiveRefresh][disabled]")

    self._RunUpdateFlow(self.client_id)

    # Ensure that refresh button is enabled again.
    #
    self.WaitUntilNot(self.IsElementPresent,
                      "css=button[name=RecursiveRefresh][disabled]")

  def testRecursiveRefreshButtonGetsReenabledWhenUpdateEnds(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.Click("css=button[name=RecursiveRefresh]:not([disabled])")

    self.Click("css=button[name=Proceed]")
    # Wait until the dialog is automatically closed.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.modal-header:contains('Recursive Directory Refresh')")

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RecursiveRefresh][disabled]")

    self._RunUpdateFlow(self.client_id)

    # Check that the button got enabled again.
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RecursiveRefresh]:not([disabled])")

  def testSwitchingFoldersReEnablesRecursiveRefreshButton(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.Click("css=button[name=RecursiveRefresh]:not([disabled])")

    self.Click("css=button[name=Proceed]")
    # Wait until the dialog is automatically closed.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.modal-header:contains('Recursive Directory Refresh')")

    self.Click("css=#_fs-os-c-bin a")

    # Ensure that refresh button is enabled again.
    #
    self.WaitUntilNot(self.IsElementPresent,
                      "css=button[name=RecursiveRefresh][disabled]")

  def testTreeAndFileListRefreshedWhenRecursiveRefreshCompletes(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.Click("css=button[name=RecursiveRefresh]:not([disabled])")

    self.Click("css=button[name=Proceed]")
    # Wait until the dialog is automatically closed.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.modal-header:contains('Recursive Directory Refresh')")

    self._RunUpdateFlow(self.client_id)

    # The flow should be finished now, and file/tree lists update should
    # be triggered.
    # Ensure that the tree got updated as well as files list.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('TestFolder')")
    self.WaitUntil(self.IsElementPresent,
                   "css=#_fs-os-c-TestFolder i.jstree-icon")

  def testViewUpdatedWhenRecursiveUpdateCompletesAfterSelectionChange(self):
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/")
    self.Click("css=button[name=RecursiveRefresh]:not([disabled])")

    self.Click("css=button[name=Proceed]")
    # Wait until the dialog is automatically closed.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.modal-header:contains('Recursive Directory Refresh')")

    # Change the selection while the update is in progress.
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RecursiveRefresh][disabled]")
    self.Click("css=#_fs-os-c-bin a")

    self._RunUpdateFlow(self.client_id)

    # The flow should be finished now, and directory tree update should
    # be triggered, even though the selection has changed during the update.
    #
    # Ensure that the tree got updated as well as files list.
    self.WaitUntil(self.IsElementPresent,
                   "css=#_fs-os-c-TestFolder i.jstree-icon")
    self.WaitUntil(self.IsElementPresent,
                   "css=#_fs-os-c-bin-TestBinFolder i.jstree-icon")

  def testRecursiveListDirectory(self):
    """Tests that Recursive Refresh button triggers correct flow."""
    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a[grrtarget='client.vfs']")
    self.Click("css=#_fs i.jstree-icon")
    self.Click("css=#_fs-os i.jstree-icon")
    self.Click("link=c")

    # Perform recursive refresh
    self.Click("css=button[name=RecursiveRefresh]:not([disabled])")

    self.WaitUntil(self.IsTextPresent, "Recursive Directory Refresh")
    self.WaitUntil(self.IsTextPresent, "Max depth")

    self.Type("css=label:contains('Max depth') ~ * input", "423")
    self.Click("css=button[name=Proceed]")

    # Wait until the dialog is automatically closed.
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=.modal-header:contains('Recursive Directory Refresh')")

    # Go to "Manage Flows" tab and check that RecursiveListDirectory flow has
    # been created.
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('RecursiveListDirectory')")

    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains('/c')")
    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains(423)")


if __name__ == "__main__":
  app.run(test_lib.main)
