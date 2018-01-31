#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the fileview interface."""


import unittest
from grr.gui import api_call_handler_base
from grr.gui import gui_test_lib
from grr.gui.api_plugins import vfs as api_vfs

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server.aff4_objects import aff4_grr
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


class TestFileView(gui_test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  def setUp(self):
    super(TestFileView, self).setUp()
    # Prepare our fixture.
    self.client_id = rdf_client.ClientURN("C.0000000000000001")
    fixture_test_lib.ClientFixture(self.client_id, self.token)
    gui_test_lib.CreateFileVersions(self.token)
    self.RequestAndGrantClientApproval("C.0000000000000001")

  def testOpeningVfsOfUnapprovedClientRedirectsToHostInfoPage(self):
    self.Open("/#/clients/C.0000000000000002/vfs/")

    # As we don't have an approval for C.0000000000000002, we should be
    # redirected to the host info page.
    self.WaitUntilEqual("/#/clients/C.0000000000000002/host-info",
                        self.GetCurrentUrlPath)
    self.WaitUntil(self.IsTextPresent,
                   "You do not have an approval for this client.")

  def testPageTitleChangesAccordingToSelectedFile(self):
    self.Open("/#/clients/C.0000000000000001/vfs/")
    self.WaitUntilEqual("GRR | C.0000000000000001 | /", self.GetPageTitle)

    # Select a folder in the tree.
    self.Click("css=#_fs i.jstree-icon")
    self.Click("css=#_fs-os i.jstree-icon")
    self.Click("css=#_fs-os-c i.jstree-icon")
    self.Click("link=Downloads")
    self.WaitUntilEqual("GRR | C.0000000000000001 | /fs/os/c/Downloads/",
                        self.GetPageTitle)

    # Select a file from the table.
    self.Click("css=tr:contains(\"a.txt\")")
    self.WaitUntilEqual("GRR | C.0000000000000001 | /fs/os/c/Downloads/a.txt",
                        self.GetPageTitle)

  def testSwitchingBetweenFilesRefreshesFileHashes(self):
    # Create 2 files and set their HASH attributes to different values.
    # Note that a string passed to fd.Schema.HASH constructor will be
    # printed as a hexademical bytestring. Thus "111" will become "313131"
    # and "222" will become "323232".
    urn_a = rdfvalue.RDFURN("C.0000000000000001/fs/os/c/Downloads/a.txt")
    with aff4.FACTORY.Open(urn_a, mode="rw") as fd:
      fd.Set(fd.Schema.HASH(sha256="111"))

    urn_b = rdfvalue.RDFURN("C.0000000000000001/fs/os/c/Downloads/b.txt")
    with aff4.FACTORY.Open(urn_b, mode="rw") as fd:
      fd.Set(fd.Schema.HASH(sha256="222"))

    # Open a URL pointing to file "a".
    self.Open(
        "/#/clients/C.0000000000000001/vfs/fs/os/c/Downloads/a.txt?tab=download"
    )
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('Sha256') td:contains('313131')")

    # Click on a file table row with file "b". Information in the download
    # tab should get rerendered and we should see Sha256 value corresponding
    # to file "b".
    self.Click("css=tr:contains(\"b.txt\")")
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('Sha256') td:contains('323232')")

  def testSwitchingBetweenFileVersionsRefreshesDownloadTab(self):
    urn_a = rdfvalue.RDFURN("C.0000000000000001/fs/os/c/Downloads/a.txt")

    # Test files are set up using self.CreateFileVersions call in test's
    # setUp method. Amend created file versions by adding different
    # hashes to versions corresponding to different times.
    # Note that a string passed to fd.Schema.HASH constructor will be
    # printed as a hexademical bytestring. Thus "111" will become "313131"
    # and "222" will become "323232".
    with test_lib.FakeTime(gui_test_lib.TIME_0):
      with aff4.FACTORY.Create(
          urn_a,
          aff4_type=aff4_grr.VFSFile,
          force_new_version=False,
          object_exists=True) as fd:
        fd.Set(fd.Schema.HASH(sha256="111"))

    with test_lib.FakeTime(gui_test_lib.TIME_1):
      with aff4.FACTORY.Create(
          urn_a,
          aff4_type=aff4_grr.VFSFile,
          force_new_version=False,
          object_exists=True) as fd:
        fd.Set(fd.Schema.HASH(sha256="222"))

    # Open a URL corresponding to a HEAD version of the file.
    self.Open(
        "/#/clients/C.0000000000000001/vfs/fs/os/c/Downloads/a.txt?tab=download"
    )
    # Make sure displayed hash value is correct.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('Sha256') td:contains('323232')")

    # Select the previous file version.
    self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
               gui_test_lib.DateString(gui_test_lib.TIME_0))
    # Make sure displayed hash value gets updated.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('Sha256') td:contains('313131')")

  def testVersionDropDownChangesFileContentAndDownloads(self):
    """Test the fileview interface."""

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
        gui_test_lib.DateString(gui_test_lib.TIME_2) in self.GetText(
            "css=tr:contains(\"a.txt\")"))

    # Click on the row.
    self.Click("css=tr:contains(\"a.txt\")")
    self.WaitUntilContains("a.txt", self.GetText, "css=div#main_bottomPane h1")
    self.WaitUntilContains("HEAD", self.GetText,
                           "css=.version-dropdown > option[selected]")
    self.WaitUntilContains(
        gui_test_lib.DateString(gui_test_lib.TIME_2), self.GetText,
        "css=.version-dropdown > option:nth(1)")

    # Check the data in this file.
    self.Click("css=li[heading=TextView]")
    self.WaitUntilContains("Goodbye World", self.GetText,
                           "css=div.monospace pre")

    downloaded_files = []

    def FakeDownloadHandle(unused_self, args, token=None):
      _ = token  # Avoid unused variable linter warnings.
      aff4_path = args.client_id.ToClientURN().Add(args.file_path)
      age = args.timestamp or aff4.NEWEST_TIME
      downloaded_files.append((aff4_path, age))

      return api_call_handler_base.ApiBinaryStream(
          filename=aff4_path.Basename(), content_generator=xrange(42))

    with utils.Stubber(api_vfs.ApiGetFileBlobHandler, "Handle",
                       FakeDownloadHandle):
      # Try to download the file.
      self.Click("css=li[heading=Download]")

      self.WaitUntilContains(
          gui_test_lib.DateTimeString(gui_test_lib.TIME_2), self.GetText,
          "css=grr-file-download-view")
      self.Click("css=button:contains(\"Download\")")

      # Select the previous version.
      self.Click("css=select.version-dropdown > option:contains(\"%s\")" %
                 gui_test_lib.DateString(gui_test_lib.TIME_1))

      # Now we should have a different time.
      self.WaitUntilContains(
          gui_test_lib.DateTimeString(gui_test_lib.TIME_1), self.GetText,
          "css=grr-file-download-view")
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
    self.assertAlmostEqual(
        downloaded_files[2][1],
        gui_test_lib.TIME_1,
        delta=rdfvalue.Duration("1s"))

    self.Click("css=li[heading=TextView]")

    # Make sure the file content has changed. This version has "Hello World" in
    # it.
    self.WaitUntilContains("Hello World", self.GetText, "css=div.monospace pre")

  def testHexViewer(self):
    self.Open("/#clients/C.0000000000000001/vfs/fs/os/proc/10/")

    self.Click("css=td:contains(\"cmdline\")")
    self.Click("css=li[heading=HexView]:not(.disabled)")

    self.WaitUntilEqual("6c730068656c6c6f20776f726c6427002d6c", self.GetText,
                        "css=table.hex-area tr:first td")

    # The string inside the file is null-character-delimited. The way
    # a null character is displayed depends on Angular
    # version. I.e. it was ignored in version 1.6.5 and is displayed
    # as a square in version 1.6.6. Making the checks in a
    # null-character-presentation-independent way.
    self.WaitUntil(self.IsElementPresent,
                   "css=table.content-area td.data:contains('ls')")
    self.WaitUntil(self.IsElementPresent,
                   "css=table.content-area td.data:contains('hello world')")
    self.WaitUntil(self.IsElementPresent,
                   "css=table.content-area td.data:contains('-l')")

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
    self.Click("css=button:contains(\"Collect from the client\")")

  def testExportToolHintIsDisplayed(self):
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView")

    self.Click("css=li#_fs i.jstree-icon")
    self.Click("css=li#_fs-os i.jstree-icon")
    self.Click("css=li#_fs-os-c i.jstree-icon")
    self.Click("css=li#_fs-os-c-Downloads i.jstree-themeicon")

    # Click on the row and on the Download tab.
    self.Click("css=tr:contains(\"a.txt\")")
    self.Click("css=li[heading=Download]:not(:disabled)")

    # Check that export tool download hint is displayed.
    self.WaitUntil(self.IsTextPresent, "/usr/bin/grr_api_shell "
                   "'http://localhost:8000/' "
                   "--exec_code 'grrapi.Client(\"C.0000000000000001\")."
                   "File(r\"\"\"fs/os/c/Downloads/a.txt\"\"\").GetBlob()."
                   "WriteToFile(\"./a.txt\")'")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
