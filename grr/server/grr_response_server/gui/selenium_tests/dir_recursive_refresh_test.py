#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the vfs recursive refreshing functionality."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class DirRecursiveRefreshTest(gui_test_lib.GRRSeleniumTest):

  def _RunUpdateFlow(self, client_id):
    gui_test_lib.CreateFileVersion(
        client_id,
        "fs/os/c/a.txt",
        "Hello World".encode("utf-8"),
        timestamp=gui_test_lib.TIME_0,
        token=self.token)
    gui_test_lib.CreateFolder(
        client_id,
        "fs/os/c/TestFolder",
        timestamp=gui_test_lib.TIME_0,
        token=self.token)
    gui_test_lib.CreateFolder(
        client_id,
        "fs/os/c/bin/TestBinFolder",
        timestamp=gui_test_lib.TIME_0,
        token=self.token)

    flow_test_lib.FinishAllFlowsOnClient(client_id)

  def setUp(self):
    super(DirRecursiveRefreshTest, self).setUp()
    # Prepare our fixture.
    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    fixture_test_lib.ClientFixture(self.client_id, self.token)
    gui_test_lib.CreateFileVersions(self.client_id, self.token)
    self.RequestAndGrantClientApproval("C.0000000000000001")

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

    client_id = rdf_client.ClientURN("C.0000000000000001")
    self._RunUpdateFlow(client_id)

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

    client_id = rdf_client.ClientURN("C.0000000000000001")
    self._RunUpdateFlow(client_id)

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

    client_id = rdf_client.ClientURN("C.0000000000000001")
    self._RunUpdateFlow(client_id)

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

    client_id = rdf_client.ClientURN("C.0000000000000001")
    self._RunUpdateFlow(client_id)

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
  flags.StartMain(test_lib.main)
