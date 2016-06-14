#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the fileview interface."""



from grr.gui import api_call_handler_base
from grr.gui import runtests_test
from grr.gui.api_plugins import vfs as api_vfs

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.rdfvalues import client as rdf_client


class FileViewTestBase(test_lib.GRRSeleniumTest):
  pass

# A increasing sequence of times.
TIME_0 = test_lib.FIXTURE_TIME
TIME_1 = TIME_0 + rdfvalue.Duration("1d")
TIME_2 = TIME_1 + rdfvalue.Duration("1d")


def DateString(t):
  return t.Format("%Y-%m-%d")


def DateTimeString(t):
  return t.Format("%Y-%m-%d %H:%M:%S")


class TestLegacyFileView(FileViewTestBase):
  """Test the fileview interface."""

  def setUp(self):
    super(TestLegacyFileView, self).setUp()
    # Prepare our fixture.
    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")

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
    self.Click("css=button[name=RecursiveRefresh]")

    self.WaitUntil(self.IsTextPresent, "Recursive Refresh")
    self.WaitUntil(self.IsTextPresent, "Max depth")

    self.Type("css=label:contains('Max depth') ~ * input", "423")
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Refresh started successfully!")
    self.Click("css=button[name=Close]")

    # Go to "Manage Flows" tab and check that RecursiveListDirectory flow has
    # been created.
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('RecursiveListDirectory')")

    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains('/c')")
    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains(423)")


class TestFileView(FileViewTestBase):
  """Test the fileview interface."""

  def setUp(self):
    super(TestFileView, self).setUp()
    # Prepare our fixture.
    with self.ACLChecksDisabled():
      self._CreateFileVersions()
      self.RequestAndGrantClientApproval("C.0000000000000001")

      self.canary_override = test_lib.CanaryModeOverrider(
          self.token, target_canary_mode=True)
      self.canary_override.Start()

  def tearDown(self):
    super(TestFileView, self).tearDown()
    with self.ACLChecksDisabled():
      self.canary_override.Stop()

  def _CreateFileVersions(self):
    """Add new versions for a file."""
    # This file already exists in the fixture at TIME_0, we write a later
    # version.
    self._CreateFileVersion("aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
                            "Hello World",
                            timestamp=TIME_1,
                            token=self.token)
    self._CreateFileVersion("aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
                            "Goodbye World",
                            timestamp=TIME_2,
                            token=self.token)

  def _CreateFileVersion(self, path, content, timestamp, token=None):
    """Add a new version for a file."""
    with test_lib.FakeTime(timestamp):
      with aff4.FACTORY.Create(path,
                               aff4_type=aff4_grr.VFSFile,
                               mode="w",
                               token=token) as fd:
        fd.Write(content)
        fd.Set(fd.Schema.CONTENT_LAST, rdfvalue.RDFDatetime().Now())

  def testVersionDropDownChangesFileContentAndDownloads(self):
    """Test the fileview interface."""

    # Set up multiple version for an attribute on the client for tests.
    with self.ACLChecksDisabled():
      for fake_time, hostname in [(TIME_0, "HostnameV1"),
                                  (TIME_1, "HostnameV2"),
                                  (TIME_2, "HostnameV3")]:
        with test_lib.FakeTime(fake_time):
          client = aff4.FACTORY.Open(u"C.0000000000000001",
                                     mode="rw",
                                     token=self.token)
          client.Set(client.Schema.HOSTNAME(hostname))
          client.Close()

    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1.
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS.
    self.Click("css=a[grrtarget='client.vfs']")

    self.Click("css=#_fs i.jstree-icon")
    self.Click("css=#_fs-os i.jstree-icon")
    self.Click("css=#_fs-os-c i.jstree-icon")

    # Test file versioning.
    self.WaitUntil(self.IsElementPresent, "css=#_fs-os-c-Downloads")
    self.Click("link=Downloads")

    # Verify that we have the latest version in the table by default.
    self.assertTrue(
        DateString(TIME_2) in self.GetText("css=tr:contains(\"a.txt\")"))

    # Click on the row.
    self.Click("css=tr:contains(\"a.txt\")")
    self.WaitUntilContains("a.txt", self.GetText, "css=div#main_bottomPane h1")
    self.WaitUntilContains("HEAD", self.GetText,
                           "css=.version-dropdown > option[selected]")
    self.WaitUntilContains(
        DateString(TIME_2), self.GetText,
        "css=.version-dropdown > option:nth(1)")

    # Check the data in this file.
    self.Click("css=li[heading=TextView]")
    self.WaitUntilContains("Goodbye World", self.GetText,
                           "css=div.monospace pre")

    downloaded_files = []

    def FakeDownloadHandle(unused_self, args, token=None):
      _ = token  # Avoid unused variable linter warnings.
      aff4_path = args.client_id.Add(args.file_path)
      age = args.timestamp or aff4.NEWEST_TIME
      downloaded_files.append((aff4_path, age))

      return api_call_handler_base.ApiBinaryStream(
          filename=aff4_path.Basename(),
          content_generator=xrange(42))

    with utils.Stubber(api_vfs.ApiGetFileBlobHandler, "Handle",
                       FakeDownloadHandle):
      # Try to download the file.
      self.Click("css=li[heading=Download]")

      self.WaitUntilContains(
          DateTimeString(TIME_2), self.GetText, "css=grr-file-download-view")
      self.Click("css=button:contains(\"Download\")")

      # Select the previous version.
      self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
                 DateString(TIME_1))

      # Now we should have a different time.
      self.WaitUntilContains(
          DateTimeString(TIME_1), self.GetText, "css=grr-file-download-view")
      self.Click("css=button:contains(\"Download\")")

      self.WaitUntil(self.IsElementPresent, "css=li[heading=TextView]")

      # the FakeDownloadHandle method was actually called four times, since
      # a file download first sends a HEAD request to check user access.
      self.WaitUntil(lambda: len(downloaded_files) == 4)

    # Both files should be the same...
    self.assertEqual(downloaded_files[0][0],
                     u"aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt")
    self.assertEqual(downloaded_files[2][0],
                     u"aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt")
    # But from different times. The downloaded file timestamp is only accurate
    # to the nearest second. Also, the HEAD version of the file is downloaded
    # with age=NEWEST_TIME.
    self.assertEqual(downloaded_files[0][1], aff4.NEWEST_TIME)
    self.assertAlmostEqual(downloaded_files[2][1], TIME_1,
                           delta=rdfvalue.Duration("1s"))

    self.Click("css=li[heading=TextView]")

    # Make sure the file content has changed. This version has "Hello World" in
    # it.
    self.WaitUntilContains("Hello World", self.GetText, "css=div.monospace pre")

  def testRefreshFileStartsFlow(self):
    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1.
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS.
    self.Click("css=a:contains('Browse Virtual Filesystem')")

    self.Click("css=#_fs i.jstree-icon")
    self.Click("css=#_fs-os i.jstree-icon")
    self.Click("css=#_fs-os-c i.jstree-icon")

    # Test file versioning.
    self.WaitUntil(self.IsElementPresent, "css=#_fs-os-c-Downloads")
    self.Click("link=Downloads")

    # Select a file and start a flow by requesting a newer version.
    self.Click("css=tr:contains(\"a.txt\")")
    self.Click("css=li[heading=Download]")
    self.Click("css=button:contains(\"Get a new Version\")")

    # Create a new file version (that would have been created by the flow
    # otherwise) and finish the flow.
    with self.ACLChecksDisabled():
      client_id = rdf_client.ClientURN("C.0000000000000001")

      fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)

      # Make sure that the flow has started (when button is clicked, the HTTP
      # API request is sent asynchronously).
      def MultiGetFileStarted():
        return "MultiGetFile" in list(x.__class__.__name__
                                      for x in fd.OpenChildren())

      self.WaitUntil(MultiGetFileStarted)

      flows = list(fd.ListChildren())

      client_mock = action_mocks.ActionMock("StatFile", "HashFile",
                                            "FingerprintFile")
      for flow_urn in flows:
        for _ in test_lib.TestFlowHelper(flow_urn,
                                         client_mock,
                                         client_id=client_id,
                                         check_flow_errors=False,
                                         token=self.token):
          pass

      time_in_future = rdfvalue.RDFDatetime().Now() + rdfvalue.Duration("1h")
      # We have to make sure that the new version will not be within a second
      # from the current one, otherwise the previous one and the new one will
      # be indistinguishable in the UI (as it has a 1s precision when
      # displaying versions).
      with test_lib.FakeTime(time_in_future):
        with aff4.FACTORY.Open(
            "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
            aff4_type=aff4_grr.VFSFile,
            mode="rw",
            token=self.token) as fd:
          fd.Write("The newest version!")

    # Once the flow has finished, the file view should update and add the
    # newly created, latest version of the file to the list. The selected
    # option should still be "HEAD".
    self.WaitUntilContains("HEAD", self.GetText,
                           "css=.version-dropdown > option[selected]")
    self.WaitUntilContains(
        DateTimeString(time_in_future), self.GetText,
        "css=.version-dropdown > option:nth(1)")

    # The file table should also update and display the new timestamp.
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-file-table tbody > tr td:contains(\"%s\")" %
                   (DateTimeString(time_in_future)))

    # Make sure the file content has changed.
    self.Click("css=li[heading=TextView]")
    self.WaitUntilContains("The newest version!", self.GetText,
                           "css=div.monospace pre")

    # Go to the flow management screen and check that there was a new flow.
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=grr-flows-list tr:contains('MultiGetFile')")
    self.WaitUntilContains("MultiGetFile", self.GetText, "css=#main_bottomPane")
    self.WaitUntilContains(
        "c/Downloads/a.txt", self.GetText,
        "css=#main_bottomPane table > tbody td.proto_key:contains(\"Path\") "
        "~ td.proto_value")

  def testUnicodeContentIsShownInTree(self):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView&t=_fs-os-c")

    # Wait until the folder gets selected and its information displayed in
    # the details pane.
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs/os/c")

    # Click on the "Downloads" subfolder.
    self.Click("css=#_fs-os-c-Downloads a")

    # Some more unicode testing.
    self.Click(u"css=tr:contains(\"中.txt\")")
    self.Click("css=li[heading=Download]")

    self.WaitUntil(self.IsTextPresent, u"中国新闻网新闻中.txt")

    # Test the hex viewer.
    self.Click("css=#_fs-os-proc a")
    self.Click("css=li[heading=Stats]")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs/os/proc")

    self.Click("css=#_fs-os-proc-10 a")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs/os/proc/10")

    self.Click("css=td:contains(\"cmdline\")")
    self.Click("css=li[heading=HexView]:not(.disabled)")

    self.WaitUntilEqual("6c730068656c6c6f20776f726c6427002d6c", self.GetText,
                        "css=table.hex-area tr:first td")

    self.WaitUntilEqual("lshello world'-l", self.GetText,
                        "css=table.content-area tr:first td")

  def testFolderPathCanContainUnicodeCharacters(self):
    # Open VFS view for client 1 on a location containing unicode characters.
    self.Open("/#/clients/C.0000000000000001/vfs/fs/os/c/中国新闻网新闻中/")

    # Check that the correct file is listed.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains(\"bzcmp\")")

  def testUrlSensitiveCharactersAreShownInTree(self):
    with self.ACLChecksDisabled():
      self._CreateFileVersion(
          "aff4:/C.0000000000000001/fs/os/c/foo?bar&oh/a&=?b.txt",
          "Hello World",
          timestamp=TIME_1,
          token=self.token)

    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView&t=_fs-os-c")

    # Wait until the folder gets selected and its information displayed in
    # the details pane.
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs/os/c")

    # Click on the "foo?bar&oh" subfolder.
    self.Click("css=#_fs-os-c-foo_3Fbar_26oh a")

    # Some more unicode testing.
    self.Click(u"css=tr:contains(\"a&=?b.txt\")")
    self.Click("css=li[heading=Download]")

    self.WaitUntil(self.IsTextPresent, u"a&=?b.txt")

    # Test the text viewer.
    self.Click("css=li[heading=TextView]")
    self.WaitUntilContains("Hello World", self.GetText, "css=div.monospace pre")

  def testFolderPathCanContainUrlSensitiveCharacters(self):
    with self.ACLChecksDisabled():
      self._CreateFileVersion(
          "aff4:/C.0000000000000001/fs/os/c/foo?bar&oh/a&=?b.txt",
          "Hello World",
          timestamp=TIME_1,
          token=self.token)

    # Open VFS view for client 1 on a location containing unicode characters.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView&t=_fs-os-c"
              "-foo_3Fbar_26oh")

    # Check that the correct file is listed.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains(\"a&=?b.txt\")")

  def testSearchInputFiltersFileList(self):
    # Open VFS view for client 1.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView&t=_fs-os-c")

    # Navigate to the bin C.0000000000000001 directory
    self.Click("link=bin C.0000000000000001")

    # We need to await the initial file listing for the current directory,
    # since the infinite table will only issue one request at a time.
    # We could use WaitUntilNot to check that "Loading..." is not visible
    # anymore, but this could cause problems if "Loading..." is not shown yet.
    self.WaitUntilEqual("bash", self.GetText,
                        "css=table.file-list tr:nth(1) span")
    self.WaitUntilEqual("bsd-csh", self.GetText,
                        "css=table.file-list tr:nth(2) span")

    # Filter the table for bash (should match both bash and rbash)
    self.Type("css=input.file-search", "bash", end_with_enter=True)
    self.WaitUntilEqual("bash", self.GetText,
                        "css=table.file-list tr:nth(1) span")
    self.WaitUntilEqual("rbash", self.GetText,
                        "css=table.file-list tr:nth(2) span")
    self.WaitUntilEqual(2, self.GetCssCount,
                        "css=#content_rightPane table.file-list tbody > tr")

    # If we anchor cat at the start, we should only receive one result item.
    self.Type("css=input.file-search", "^cat", end_with_enter=True)
    self.WaitUntilEqual("cat", self.GetText,
                        "css=table.file-list tr:nth(1) span")
    self.assertEqual(
        1,
        self.GetCssCount("css=#content_rightPane table.file-list tbody > tr"))
    self.Click("css=tr:nth(1)")

    self.WaitUntilContains("cat", self.GetText, "css=#main_bottomPane h1")
    self.WaitUntil(self.IsTextPresent, "1026267")  # st_inode.

    # Lets download it.
    self.Click("css=li[heading=Download]")
    self.Click("css=button:contains(\"Get a new Version\")")

  def testRefreshDirectoryStartsFlow(self):
    # Open VFS view for client 1.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView")

    # Choose some directory with pathspec in the ClientFixture.
    self.Click("css=#_fs a")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs")

    self.Click("css=#_fs-os a")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs/os")

    self.Click("css=#_fs-os-Users a")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs/os/Users")

    self.Click("css=#_fs-os-Users-Shared a")
    self.WaitUntil(self.IsTextPresent, "C.0000000000000001/fs/os/Users/Shared")
    self.WaitUntil(self.IsTextPresent, "/Users/Shared")

    # Grab the root directory again - should produce an Interrogate flow.
    self.Click("css=button#refresh-dir")

    # Go to the flow management screen.
    self.Click("css=a[grrtarget='client.flows']")

    self.Click("css=grr-flows-list tr:contains('RecursiveListDirectory')")
    self.WaitUntilContains("RecursiveListDirectory", self.GetText,
                           "css=#main_bottomPane")
    self.WaitUntilContains(
        "/Users/Shared", self.GetText,
        "css=#main_bottomPane table > tbody td.proto_key:contains(\"Path\") "
        "~ td.proto_value")

  def testExportToolHintIsDisplayed(self):
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView")

    self.Click("css=li#_fs i.jstree-icon")
    self.Click("css=li#_fs-os i.jstree-icon")
    self.Click("css=li#_fs-os-c i.jstree-icon")
    self.Click("css=li#_fs-os-c-Downloads a")

    # Click on the row and on the Download tab.
    self.Click("css=tr:contains(\"a.txt\")")
    self.Click("css=li[heading=Download]")

    # Check that export tool download hint is displayed.
    self.WaitUntil(
        self.IsTextPresent, "/usr/bin/grr_export "
        "--username test file --path "
        "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt --output .")

  def testUpdateButton(self):
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

    # Ensure that refresh button is enabled
    self.WaitUntilNot(self.IsElementPresent,
                      "css=button[id^=refresh][disabled]")

    # Grab the root directory again - should produce an Interrogate flow.
    self.Click("css=button[id^=refresh]")

    # Check that the button got disabled
    # TODO(user): Implement this logic, so that the button is disabled not
    # globally, but on per-one-operation basis. See the comment in
    # file-table.html.
    # self.WaitUntil(self.IsElementPresent, "css=button[id^=refresh][disabled]")

    # Get the flows that should have been started and finish them.
    with self.ACLChecksDisabled():
      client_id = rdf_client.ClientURN("C.0000000000000001")

      fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      flows = list(fd.ListChildren())

      client_mock = action_mocks.ActionMock()
      for flow_urn in flows:
        for _ in test_lib.TestFlowHelper(flow_urn,
                                         client_mock,
                                         client_id=client_id,
                                         token=self.token,
                                         check_flow_errors=False):
          pass

    # Ensure that refresh button is enabled again.
    #
    # TODO(user): Implement this logic, so that the button is disabled not
    # globally, but on per-one-operation basis. See the comment in
    # file-table.html.
    # TODO(user): ideally, we should also check that something got
    # updated, not only that button got enabled back.
    # self.WaitUntilNot(self.IsElementPresent,
    #                   "css=button[id^=refresh][disabled]")

  def testClickingOnTreeNodeRefrehsesChildrenFoldersList(self):
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView")

    # Go to Browse VFS
    self.Click("css=a[grrtarget='client.vfs']")
    self.Click("css=#_fs i.jstree-icon")
    self.Click("css=#_fs-os i.jstree-icon")
    self.Click("link=c")

    self.WaitUntil(self.IsElementPresent, "link=Downloads")
    self.WaitUntil(self.IsElementPresent, "link=bin")

    with self.ACLChecksDisabled():
      aff4.FACTORY.Delete("aff4:/C.0000000000000001/fs/os/c/bin",
                          token=self.token)

    self.Click("link=c")
    self.WaitUntil(self.IsElementPresent, "link=Downloads")
    self.WaitUntilNot(self.IsElementPresent, "link=bin")

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
    self.Click("css=button[name=RecursiveRefresh]")

    self.WaitUntil(self.IsTextPresent, "Recursive Refresh")
    self.WaitUntil(self.IsTextPresent, "Max depth")

    self.Type("css=label:contains('Max depth') ~ * input", "423")
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Refresh started successfully!")
    self.Click("css=button[name=Close]")

    # Go to "Manage Flows" tab and check that RecursiveListDirectory flow has
    # been created.
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('RecursiveListDirectory')")

    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains('/c')")
    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains(423)")

  def testDoubleClickGoesInsideDirectory(self):
    """Tests that double click in FileTable goes inside the directory."""

    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001", self.GetText,
                        "css=span[type=subject]")

    # Choose client 1 and go to 'Browse Virtual Filesystem'
    self.Click("css=td:contains('0001')")
    self.Click("css=a[grrtarget='client.vfs']")
    self.Click("link=fs")

    # Now click on "os" inside the table. Tree shouldn't get updated,
    self.Click("css=td:contains('os')")

    # Now double click on "os".
    self.DoubleClick("css=td:contains('os')")

    # Now we should be inside the folder, and the tree should open.
    self.WaitUntil(self.IsElementPresent, "css=#_fs-os-c i.jstree-icon")
    # Check that breadcrumbs got updated.
    self.WaitUntil(self.IsElementPresent,
                   "css=#content_rightPane .breadcrumb li:contains('os')")


class TestTimeline(FileViewTestBase):
  """Test the timeline view interface."""

  TIMELINE_ITEMS_PER_FILE = 3

  def setUp(self):
    super(TestTimeline, self).setUp()
    # Prepare our fixture.
    with self.ACLChecksDisabled():
      self.CreateFileWithTimeline(
          "aff4:/C.0000000000000001/fs/os/c/proc/changed.txt")
      self.CreateFileWithTimeline(
          "aff4:/C.0000000000000001/fs/os/c/proc/other.txt")
      self.RequestAndGrantClientApproval("C.0000000000000001")

      self.canary_override = test_lib.CanaryModeOverrider(
          self.token, target_canary_mode=True)
      self.canary_override.Start()

  def tearDown(self):
    super(TestTimeline, self).tearDown()
    with self.ACLChecksDisabled():
      self.canary_override.Stop()

  @staticmethod
  def CreateFileWithTimeline(file_path):
    """Add a file with timeline."""
    token = access_control.ACLToken(username="test")

    # Add a version of the file at TIME_0. Since we write all MAC times,
    # this will result in three timeline items.
    with test_lib.FakeTime(TIME_0):
      with aff4.FACTORY.Create(file_path,
                               aff4_grr.VFSAnalysisFile,
                               mode="w",
                               token=token) as fd:
        stats = rdf_client.StatEntry(
            st_atime=TIME_0.AsSecondsFromEpoch() + 1000,
            st_mtime=TIME_0.AsSecondsFromEpoch(),
            st_ctime=TIME_0.AsSecondsFromEpoch() - 1000)
        fd.Set(fd.Schema.STAT, stats)

    # Add a version with a stat entry, but without timestamps.
    with test_lib.FakeTime(TIME_1):
      with aff4.FACTORY.Create(file_path,
                               aff4_grr.VFSAnalysisFile,
                               mode="w",
                               token=token) as fd:
        stats = rdf_client.StatEntry(st_ino=99)
        fd.Set(fd.Schema.STAT, stats)

  def testTimelineContainsAllChangesForDirectory(self):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    # We have to wait until the "proc" node gets highlighted in the tree,
    # as the tree expansion may take time and happen in multiple steps.
    # On every expansion step, the view mode will be switched to "file list",
    # even if "timeline" mode was previously active.
    self.WaitUntil(self.IsElementPresent,
                   "css=a.jstree-clicked:contains('proc')")
    self.WaitUntilEqual(2, self.GetCssCount, "css=.file-list tbody tr")

    self.Click("css=.btn:contains('Timeline')")

    # We need to have one entry per timestamp per file.
    self.WaitUntilEqual(2 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")

  def testTimelineShowsClosestFileVersionOnFileSelection(self):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    # We have to wait until the "proc" node gets highlighted in the tree,
    # as the tree expansion may take time and happen in multiple steps.
    # On every expansion step, the view mode will be switched to "file list",
    # even if "timeline" mode was previously active.
    self.WaitUntil(self.IsElementPresent,
                   "css=a.jstree-clicked:contains('proc')")
    self.WaitUntilEqual(2, self.GetCssCount, "css=.file-list tbody tr")

    self.Click("css=.btn:contains('Timeline')")

    # The first item has the latest time, so the version dropdown should not
    # show a hint.
    self.Click("css=grr-file-timeline table td:contains('changed.txt'):first")
    self.WaitUntilContains("changed.txt", self.GetText,
                           "css=div#main_bottomPane h1")
    self.WaitUntilContains(
        DateString(TIME_1), self.GetText,
        "css=.version-dropdown > option[selected]")

    # The last timeline item for changed.txt has a timestamp before TIME_0,
    # which is the first available file version.
    self.Click("css=grr-file-timeline table tr "
               "td:contains('changed.txt'):last")
    self.WaitUntilContains("changed.txt", self.GetText,
                           "css=div#main_bottomPane h1")
    self.WaitUntilContains(
        DateString(TIME_0), self.GetText,
        "css=.version-dropdown > option[selected]")
    self.WaitUntilContains("Newer Version available.", self.GetText,
                           "css=grr-file-details")

  def testSearchInputFiltersTimeline(self):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    # We have to wait until the "proc" node gets highlighted in the tree,
    # as the tree expansion may take time and happen in multiple steps.
    # On every expansion step, the view mode will be switched to "file list",
    # even if "timeline" mode was previously active.
    self.WaitUntil(self.IsElementPresent,
                   "css=a.jstree-clicked:contains('proc')")
    self.WaitUntilEqual(2, self.GetCssCount, "css=.file-list tbody tr")

    self.Click("css=.btn:contains('Timeline')")

    # Wait until the UI finished loading.
    self.WaitUntilEqual(2 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")

    # Search for one file.
    self.Type("css=input.file-search", "changed.txt", end_with_enter=True)
    self.WaitUntilEqual(self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")

    # Search both files.
    self.Type("css=input.file-search", ".txt", end_with_enter=True)
    self.WaitUntilEqual(2 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")

  def testSearchInputAllowsFilteringTimelineByActionType(self):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    # We have to wait until the "proc" node gets highlighted in the tree,
    # as the tree expansion may take time and happen in multiple steps.
    # On every expansion step, the view mode will be switched to "file list",
    # even if "timeline" mode was previously active.
    self.WaitUntil(self.IsElementPresent,
                   "css=a.jstree-clicked:contains('proc')")
    self.WaitUntilEqual(2, self.GetCssCount, "css=.file-list tbody tr")

    self.Click("css=.btn:contains('Timeline')")

    # Wait until the UI finished loading.
    self.WaitUntilEqual(2 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")

    # Search for "changed" will return timeline items for files having "changed"
    # in their names (i.e. all items for changed.txt) plus any items with a
    # methadata change action (i.e. one action on other.txt).
    self.Type("css=input.file-search", "changed", end_with_enter=True)
    self.WaitUntilEqual(self.TIMELINE_ITEMS_PER_FILE + 1, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")

    # Search for items with file modifications, i.e. one for each file.
    self.Type("css=input.file-search", "modif", end_with_enter=True)
    self.WaitUntilEqual(2, self.GetCssCount, "css=grr-file-timeline tbody tr")

  def testClickingOnTreeNodeRefrehsesTimeline(self):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    # We have to wait until the "proc" node gets highlighted in the tree,
    # as the tree expansion may take time and happen in multiple steps.
    # On every expansion step, the view mode will be switched to "file list",
    # even if "timeline" mode was previously active.
    self.WaitUntil(self.IsElementPresent,
                   "css=a.jstree-clicked:contains('proc')")
    self.WaitUntilEqual(2, self.GetCssCount, "css=.file-list tbody tr")

    self.Click("css=.btn:contains('Timeline')")

    # Wait until the UI finished loading.
    self.WaitUntilEqual(2 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")

    # Add a new file with several versions.
    with self.ACLChecksDisabled():
      self.CreateFileWithTimeline(
          "aff4:/C.0000000000000001/fs/os/c/proc/newly_added.txt")

    # Click on tree again.
    self.Click("link=proc")

    # Wait until the UI finished loading.
    self.WaitUntilEqual(3 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-file-timeline td:contains('newly_added.txt')")


class TestHostInformation(FileViewTestBase):
  """Test the host information interface."""

  def setUp(self):
    super(TestHostInformation, self).setUp()
    self.client_id = "C.0000000000000001"

    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval(self.client_id)

      with test_lib.FakeTime(TIME_0):
        with aff4.FACTORY.Open(self.client_id,
                               mode="rw",
                               token=self.token) as fd:
          fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString("6.1.7000"))
          fd.Set(fd.Schema.HOSTNAME("Hostname T0"))

      with test_lib.FakeTime(TIME_1):
        with aff4.FACTORY.Open(self.client_id,
                               mode="rw",
                               token=self.token) as fd:
          fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString("6.1.8000"))
          fd.Set(fd.Schema.HOSTNAME("Hostname T1"))

      with test_lib.FakeTime(TIME_2):
        with aff4.FACTORY.Open(self.client_id,
                               mode="rw",
                               token=self.token) as fd:
          fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString("7.0.0000"))
          fd.Set(fd.Schema.HOSTNAME("Hostname T2"))

  def testClickingOnInterrogateStartsInterrogateFlow(self):
    self.Open("/#c=" + self.client_id)

    # A click on the Interrogate button starts a flow, disables the button and
    # shows a loading icon within the button.
    self.Click("css=button:contains('Interrogate')")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Interrogate')[disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button:contains('Interrogate') i")

    # Get the started flow and finish it, this will re-enable the button.
    with self.ACLChecksDisabled():
      client_id = rdf_client.ClientURN(self.client_id)

      fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      flows = list(fd.ListChildren())

      client_mock = action_mocks.ActionMock()
      for flow_urn in flows:
        for _ in test_lib.TestFlowHelper(flow_urn,
                                         client_mock,
                                         client_id=client_id,
                                         token=self.token,
                                         check_flow_errors=False):
          pass

    self.WaitUntilNot(self.IsElementPresent,
                      "css=button:contains('Interrogate')[disabled]")

    # Check if an Interrogate flow was started.
    self.Click("css=a[grrtarget='client.flows']")
    self.Click("css=td:contains('Interrogate')")
    self.WaitUntilContains("Interrogate", self.GetText,
                           "css=table td.proto_key:contains('Flow name') "
                           "~ td.proto_value")

  def testChangingVersionDropdownChangesClientInformation(self):
    self.Open("/#c=" + self.client_id)

    # Check that the newest version is selected.
    self.WaitUntilContains(
        DateString(TIME_2), self.GetText,
        "css=.version-dropdown > option[selected]")
    self.WaitUntil(self.IsTextPresent, "Hostname T2")

    self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
               DateString(TIME_1))
    self.WaitUntil(self.IsTextPresent, "Hostname T1")
    self.WaitUntil(self.IsTextPresent, "6.1.8000")
    self.WaitUntil(self.IsTextPresent, "Newer Version available")

    # Also the details show the selected version.
    self.Click("css=label:contains('Full details')")
    self.WaitUntil(self.IsTextPresent, "Hostname T1")
    self.WaitUntil(self.IsTextPresent, "6.1.8000")

    # Check that changing the version does not change the view, i.e. that
    # we are still in the full details view.
    self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
               DateString(TIME_0))
    self.WaitUntil(self.IsTextPresent, "Hostname T0")
    self.WaitUntil(self.IsTextPresent, "6.1.7000")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
