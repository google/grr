#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test the fileview interface."""



from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
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


class TestFileView(FileViewTestBase):
  """Test the fileview interface."""

  def setUp(self):
    super(TestFileView, self).setUp()
    # Prepare our fixture.
    with self.ACLChecksDisabled():
      self.CreateFileVersions()
      self.RequestAndGrantClientApproval("C.0000000000000001")

      self.canary_override = test_lib.CanaryModeOverrider(
          self.token, target_canary_mode=True)
      self.canary_override.Start()

  def tearDown(self):
    super(TestFileView, self).tearDown()
    with self.ACLChecksDisabled():
      self.canary_override.Stop()

  @staticmethod
  def CreateFileVersions():
    """Add a new version for a file."""
    with test_lib.FakeTime(TIME_1):
      token = access_control.ACLToken(username="test")
      # This file already exists in the fixture at TIME_0, we write a later
      # version.
      fd = aff4.FACTORY.Create(
          "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
          "AFF4MemoryStream", mode="w", token=token)
      fd.Write("Hello World")
      fd.Close()

    # An another version, even later.
    with test_lib.FakeTime(TIME_2):
      fd = aff4.FACTORY.Create(
          "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
          "AFF4MemoryStream", mode="w", token=token)
      fd.Write("Goodbye World")
      fd.Close()

  def testVersionDropDownChangesFileContentAndDownloads(self):
    """Test the fileview interface."""

    # This is ugly :( Django gets confused when you import in the wrong order
    # though and fileview imports the Django http module so we have to delay
    # import until the Django server is properly set up.
    # pylint: disable=g-import-not-at-top
    from grr.gui.plugins import fileview
    # pylint: enable=g-import-not-at-top

    # Set up multiple version for an attribute on the client for tests.
    with self.ACLChecksDisabled():
      for fake_time, hostname in [(TIME_0, "HostnameV1"),
                                  (TIME_1, "HostnameV2"),
                                  (TIME_2, "HostnameV3")]:
        with test_lib.FakeTime(fake_time):
          client = aff4.FACTORY.Open(u"C.0000000000000001", mode="rw",
                                     token=self.token)
          client.Set(client.Schema.HOSTNAME(hostname))
          client.Close()

    self.Open("/")

    self.Type("client_query", "C.0000000000000001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

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

    # Verify that we have the latest version in the table by default.
    self.assertTrue(
        DateString(TIME_2) in self.GetText("css=tr:contains(\"a.txt\")"))

    # Click on the row.
    self.Click("css=tr:contains(\"a.txt\")")
    self.WaitUntilContains("a.txt", self.GetText,
                           "css=div#main_bottomPane h1")
    self.WaitUntilContains(DateString(TIME_2), self.GetText,
                           "css=.version-dropdown > option[selected]")

    # Check the data in this file.
    self.Click("css=li[heading=TextView]")
    self.WaitUntilContains("Goodbye World", self.GetText,
                           "css=div.monospace pre")

    downloaded_files = []

    def FakeDownload(unused_self, request, _):
      aff4_path = request.REQ.get("aff4_path")
      age = rdfvalue.RDFDatetime(request.REQ.get("age")) or aff4.NEWEST_TIME
      downloaded_files.append((aff4_path, age))

      return fileview.http.HttpResponse(
          content="<script>window.close()</script>")

    with utils.Stubber(fileview.DownloadView, "Download", FakeDownload):
      # Try to download the file.
      self.Click("css=li[heading=Download]")

      self.WaitUntil(self.IsTextPresent,
                     "As downloaded on %s" % DateTimeString(TIME_2))
      self.Click("css=button:contains(\"Download\")")

      # Select the previous version.
      self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
                 DateString(TIME_1))

      # Now we should have a different time.
      self.WaitUntil(self.IsTextPresent,
                     "As downloaded on %s" % DateTimeString(TIME_1))
      self.Click("css=button:contains(\"Download\")")

      self.WaitUntil(self.IsElementPresent, "css=li[heading=TextView]")

      self.WaitUntil(lambda: len(downloaded_files) == 2)

    # Both files should be the same...
    self.assertEqual(downloaded_files[0][0],
                     u"aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt")
    self.assertEqual(downloaded_files[1][0],
                     u"aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt")
    # But from different times. The downloaded file timestamp is only accurate
    # to the nearest second.
    self.assertAlmostEqual(downloaded_files[0][1], TIME_2,
                           delta=rdfvalue.Duration("1s"))
    self.assertAlmostEqual(downloaded_files[1][1], TIME_1,
                           delta=rdfvalue.Duration("1s"))

    self.Click("css=li[heading=TextView]")

    # Make sure the file content has changed. This version has "Hello World" in
    # it.
    self.WaitUntilContains("Hello World", self.GetText,
                           "css=div.monospace pre")

  def testUnicodeContentIsShownInTree(self):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView&t=_fs-os-c")

    # Test file versioning.
    self.WaitUntil(self.IsElementPresent, "css=#_fs-os-c-Downloads")
    self.Click("link=Downloads")

    # Some more unicode testing.
    self.Click(u"css=tr:contains(\"中.txt\")")
    self.Click("css=li[heading=Download]")

    self.WaitUntil(self.IsTextPresent, u"fs/os/c/Downloads/中国新闻网新闻中.txt")

    # Test the hex viewer.
    self.Click("css=#_fs-os-proc i.jstree-icon")
    self.Click("css=#_fs-os-proc-10 a")
    self.Click("css=td:contains(\"cmdline\")")
    self.Click("css=li[heading=HexView]")

    self.WaitUntilEqual("6c730068656c6c6f20776f726c6427002d6c", self.GetText,
                        "css=table.hex-area tr:first td")

    self.WaitUntilEqual("lshello world'-l", self.GetText,
                        "css=table.content-area tr:first td")

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
    self.Click("css=#_fs i.jstree-icon")
    self.Click("css=#_fs-os i.jstree-icon")
    self.Click("css=#_fs-os-Users i.jstree-icon")
    self.Click("css=#_fs-os-Users-Shared a")

    # Grab the root directory again - should produce an Interrogate flow.
    self.Click("css=button#refresh-dir")

    # Go to the flow management screen.
    self.Click("css=a:contains('Manage launched flows')")

    self.Click("css=grr-flows-list tr:visible:nth(1)")
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

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("css=#_fs i.jstree-icon")
    self.Click("css=#_fs-os i.jstree-icon")
    self.Click("link=c")

    # Ensure that refresh button is enabled
    self.WaitUntilNot(self.IsElementPresent,
                      "css=button[id^=refresh][disabled]")

    # Grab the root directory again - should produce an Interrogate flow.
    self.Click("css=button[id^=refresh]")

    # Check that the button got disabled
    self.WaitUntil(self.IsElementPresent,
                   "css=button[id^=refresh][disabled]")

    # Get the flows that should have been started and finish them.
    with self.ACLChecksDisabled():
      client_id = rdf_client.ClientURN("C.0000000000000001")

      fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      flows = list(fd.ListChildren())

      client_mock = action_mocks.ActionMock()
      for flow_urn in flows:
        for _ in test_lib.TestFlowHelper(
            flow_urn, client_mock, client_id=client_id, token=self.token,
            check_flow_errors=False):
          pass

    # Ensure that refresh button is enabled again.
    #
    # TODO(user): ideally, we should also check that something got
    # updated, not only that button got enabled back.
    self.WaitUntilNot(self.IsElementPresent,
                      "css=button[id^=refresh][disabled]")

  def testClickingOnTreeNodeRefrehsesChildrenFoldersList(self):
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")
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

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")
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
    self.Click("css=a:contains('Manage launched flows')")
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

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1 and go to 'Browse Virtual Filesystem'
    self.Click("css=td:contains('0001')")
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("link=fs")

    # Now click on "os" inside the table. Tree shouldn't get updated,
    self.Click("css=td:contains('os')")

    # Now double click on "os".
    self.DoubleClick("css=td:contains('os')")

    # Now we should be inside the folder, and the tree should open.
    self.WaitUntil(self.IsElementPresent,
                   "css=#_fs-os-c i.jstree-icon")
    # Check that breadcrumbs got updated.
    self.WaitUntil(self.IsElementPresent,
                   "css=#content_rightPane .breadcrumb li:contains('os')")


class TestHostInformation(FileViewTestBase):
  """Test the host information interface."""

  def setUp(self):
    super(TestHostInformation, self).setUp()
    self.client_id = "C.0000000000000001"

    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval(self.client_id)
      with aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token) as fd:
        fd.Set(fd.Schema.OS_VERSION, rdf_client.VersionString("6.1.7601"))

  def testClickingOnPlusOpensHistoricalAttributes(self):
    """Test the fileview interface."""

    self.Open("/#c=" + self.client_id)
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

    # 7601 is the latest so it should be visible.
    self.WaitUntil(self.IsTextPresent, "6.1.7601")

    # We click on '+' and should see the historical value.
    self.Click("css=td.attribute_opener[attribute=OS_VERSION]")
    self.WaitUntil(self.IsTextPresent, "6.1.7600")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
