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


class TestFileView(test_lib.GRRSeleniumTest):
  """Test the fileview interface."""

  def setUp(self):
    super(TestFileView, self).setUp()
    # Prepare our fixture.
    with self.ACLChecksDisabled():
      self.CreateFileVersions()
      self.GrantClientApproval("C.0000000000000001")

  @staticmethod
  def CreateFileVersions():
    """Add a new version for a file."""
    with test_lib.FakeTime(1333788833):
      token = access_control.ACLToken(username="test")
      # This file already exists in the fixture, and we overwrite it with a new
      # version at 2012-04-07 08:53:53.
      fd = aff4.FACTORY.Create(
          "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
          "AFF4MemoryStream", mode="w", token=token)
      fd.Write("Hello World")
      fd.Close()

    # Create another version of this file at 2012-04-09 16:27:13.
    with test_lib.FakeTime(1333988833):
      fd = aff4.FACTORY.Create(
          "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt",
          "AFF4MemoryStream", mode="w", token=token)
      fd.Write("Goodbye World")
      fd.Close()

  def testFileView(self):
    """Test the fileview interface."""

    # This is ugly :( Django gets confused when you import in the wrong order
    # though and fileview imports the Django http module so we have to delay
    # import until the Django server is properly set up.
    # pylint: disable=g-import-not-at-top
    from grr.gui.plugins import fileview
    # pylint: enable=g-import-not-at-top

    # Set up multiple version for an attribute on the client for tests.
    with self.ACLChecksDisabled():
      for fake_time, hostname in [(1333788833, "HostnameV1"),
                                  (1333888833, "HostnameV2"),
                                  (1333988833, "HostnameV3")]:
        with test_lib.FakeTime(fake_time):
          client = aff4.FACTORY.Open(u"C.0000000000000001", mode="rw",
                                     token=self.token)
          client.Set(client.Schema.HOSTNAME(hostname))
          client.Close()

    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")

    # Test the historical view for AFF4 elements.
    self.Click("css=*[attribute=HOSTNAME] > ins")
    self.WaitUntil(self.AllTextsPresent,
                   ["HostnameV1", "HostnameV2", "HostnameV3"])

    self.Click("css=*[attribute=HOSTNAME] > ins")
    self.WaitUntilNot(self.IsTextPresent, "HostnameV1")
    self.WaitUntilNot(self.IsTextPresent, "HostnameV2")

    self.Click("css=#_fs ins.jstree-icon")
    self.Click("css=#_fs-os ins.jstree-icon")
    self.Click("css=#_fs-os-c ins.jstree-icon")

    # Test file versioning.
    self.WaitUntil(self.IsElementPresent, "css=#_fs-os-c-Downloads")
    self.Click("link=Downloads")

    # Verify that we have the latest version in the table by default
    self.assertTrue(
        "2012-04-09 16:27:13" in self.GetText("css=tr:contains(\"a.txt\")"))

    # Click on the row.
    self.Click("css=tr:contains(\"a.txt\")")
    self.WaitUntilContains("a.txt @ 2012-04-09", self.GetText,
                           "css=div#main_rightBottomPane h3")

    # Check the data in this file.
    self.Click("css=#TextView")
    self.WaitUntilContains("Goodbye World", self.GetText,
                           "css=div#text_viewer_data_content")

    downloaded_files = []

    def FakeDownload(unused_self, request, _):
      aff4_path = request.REQ.get("aff4_path")
      age = rdfvalue.RDFDatetime(request.REQ.get("age")) or aff4.NEWEST_TIME
      downloaded_files.append((aff4_path, age))

      return fileview.http.HttpResponse(
          content="<script>window.close()</script>")

    with utils.Stubber(fileview.DownloadView, "Download", FakeDownload):
      # Try to download the file.
      self.Click("css=#Download")

      self.WaitUntil(self.IsTextPresent, "As downloaded on 2012-04-09 16:27:13")
      self.Click("css=button:contains(\"Download\")")

      # Click on the version selector.
      self.Click("css=tr:contains(\"a.txt\") img.version-selector")
      self.WaitUntilContains("Versions of", self.GetText,
                             "css=.version-selector-dialog h4")

      # Select the previous version.
      self.Click("css=td:contains(\"2012-04-07\")")

      # Now we should have a different time.
      self.WaitUntil(self.IsTextPresent, "As downloaded on 2012-04-07 08:53:53")
      self.Click("css=button:contains(\"Download\")")

    self.WaitUntil(self.IsElementPresent, "css=#TextView")

    self.WaitUntil(lambda: len(downloaded_files) == 2)

    # Both files should be the same...
    self.assertEqual(downloaded_files[0][0],
                     u"aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt")
    self.assertEqual(downloaded_files[1][0],
                     u"aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt")
    # But from different times.
    self.assertEqual(downloaded_files[0][1], 1333988833000000)
    self.assertEqual(downloaded_files[1][1], 1333788833000000)

    self.Click("css=#TextView")

    # Make sure the file content has changed. This version has "Hello World" in
    # it.
    self.WaitUntilContains("Hello World", self.GetText,
                           "css=div#text_viewer_data_content")

    # Some more unicode testing.
    self.Click(u"css=tr:contains(\"中.txt\")")
    self.Click("css=#Download")

    self.WaitUntil(self.IsTextPresent, u"fs/os/c/Downloads/中国新闻网新闻中.txt")

    # Test the hex viewer.
    self.Click("css=#_fs-os-proc ins.jstree-icon")
    self.Click("css=#_fs-os-proc-10 a")
    self.Click("css=span[type=subject]:contains(\"cmdline\")")
    target_aff4_path = "aff4:/C.0000000000000001/fs/os/proc/10/cmdline"
    self.Click("css=[state-aff4_path='%s'] > li > #HexView" % target_aff4_path)

    for i, value in enumerate(
        "6c 73 00 68 65 6c 6c 6f 20 77 6f 72 6c 64 27 00 2d 6c".split(" ")):
      self.WaitUntilEqual(value, self.GetText,
                          "css=#hex_area tr:first td:nth(%d)" % i)

    for i, value in enumerate(
        "l s . h e l l o  w o r l d ' . - l".split(" ")):
      self.WaitUntilEqual(value, self.GetText,
                          "css=#data_area tr:first td:nth(%d)" % i)

    self.Click("css=a[renderer=\"AFF4Stats\"]")

    # Navigate to the bin C.0000000000000001 directory
    self.Click("link=bin C.0000000000000001")

    # Filter the table for bash (should match both bash and rbash)
    self.WaitUntil(self.IsElementPresent, "css=td:contains('bash')")
    self.Click("css=th:contains('Name') img")

    self.Type("css=.sort-dialog input[type=text]", "bash", end_with_enter=True)
    self.WaitUntilEqual("rbash", self.GetText, "css=tr:nth(2) span")
    self.assertEqual(
        2, self.GetCssCount("css=#main_rightTopPane  tbody > tr"))
    self.assertEqual("bash", self.GetText("css=tr:nth(1) span"))
    self.assertEqual("rbash", self.GetText("css=tr:nth(2) span"))

    # Check that the previous search test is still available in the form.
    self.Click("css=th:contains('Name') img")
    self.assertEqual("bash", self.GetValue("css=.sort-dialog input"))

    # If we anchor cat at the start should only filter one.
    self.Type("css=.sort-dialog input[type=text]", "^cat", end_with_enter=True)

    self.WaitUntilEqual("cat", self.GetText, "css=tr:nth(1) span")
    self.assertEqual(
        1, self.GetCssCount("css=#main_rightTopPane  tbody > tr"))
    self.Click("css=tr:nth(1)")

    self.WaitUntilContains(
        "aff4:/C.0000000000000001/fs/os/c/bin C.0000000000000001/cat",
        self.GetText, "css=.tab-content h3")
    self.WaitUntil(self.IsTextPresent, "1026267")  ## st_inode.

    # Lets download it.
    self.Click("Download")
    self.Click("css=button:contains(\"Get a new Version\")")

    self.Click("path_0")

    self.WaitUntilEqual("fs", self.GetText, "css=tr td span:contains(fs)")

    self.Click("Stats")
    self.WaitUntilContains(
        "aff4:/C.0000000000000001", self.GetText, "css=.tab-content h3")

    # Grab the root directory again - should produce an Interrogate flow.
    self.Click("css=button[id^=refresh]")

    # Go to the flow management screen.
    self.Click("css=a:contains('Manage launched flows')")

    # For the client update, 2 flows have to be issued: UpdateVFSFile and
    # Interrogate. UpdateVFSFile triggers VFSGRRClient.Update() method which
    # triggers Interrogate.
    self.WaitUntilEqual("Interrogate", self.GetText,
                        "//table/tbody/tr[1]/td[3]")
    self.WaitUntilEqual("UpdateVFSFile", self.GetText,
                        "//table/tbody/tr[2]/td[3]")
    self.Click("//table/tbody/tr[2]/td[3]")
    self.WaitUntilEqual(
        "aff4:/C.0000000000000001", self.GetText,
        "css=table > tbody td.proto_key:contains(\"Vfs file urn\") "
        "~ td.proto_value")

    # Check that UpdateVFSFile is called for the cat file.
    # During the test this file is VFSMemoryFile, so its' Update method does
    # nothing, therefore UpdateVFSFile won't issue any other flows.
    self.WaitUntilEqual("UpdateVFSFile", self.GetText,
                        "//table/tbody/tr[3]/td[3]")
    self.Click("//table/tbody/tr[3]/td[3]")
    self.WaitUntilContains(
        "cat", self.GetText,
        "css=table > tbody td.proto_key:contains(\"Vfs file urn\") "
        "~ td.proto_value")

  def testExportToolHintIsDisplayed(self):
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView")

    self.Click("css=li[path='/fs'] > a")
    self.Click("css=li[path='/fs/os'] > a")
    self.Click("css=li[path='/fs/os/c'] > a")
    self.Click("css=li[path='/fs/os/c/Downloads'] > a")

    # Click on the row and on the Download tab.
    self.Click("css=tr:contains(\"a.txt\")")
    self.Click("css=#Download")

    # Check that export tool download hint is displayed.
    self.WaitUntil(
        self.IsTextPresent, "/usr/bin/grr_export "
        "--username test --reason 'Running tests' file --path "
        "aff4:/C.0000000000000001/fs/os/c/Downloads/a.txt --output .")

  def testUpdateButton(self):
    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("css=#_fs ins.jstree-icon")
    self.Click("css=#_fs-os ins.jstree-icon")
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
      client_id = rdfvalue.ClientURN("C.0000000000000001")

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

  def testRecursiveListDirectory(self):
    """Tests that Recursive Refresh button triggers correct flow."""
    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1
    self.Click("css=td:contains('0001')")

    # Go to Browse VFS
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("css=#_fs ins.jstree-icon")
    self.Click("css=#_fs-os ins.jstree-icon")
    self.Click("link=c")

    # Perform recursive refresh
    self.Click("css=button[id^=recursive_refresh]")

    self.WaitUntil(self.IsTextPresent, "Recursive Refresh")
    self.WaitUntil(self.IsTextPresent, "Max depth")

    self.Type("css=input[id=v_-max_depth]", "423")
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Refresh started successfully!")
    self.Click("css=button[name=Cancel]")

    # Go to "Manage Flows" tab and check that RecursiveListDirectory flow has
    # been created.
    self.Click("css=a:contains('Manage launched flows')")
    self.Click("css=td:contains('RecursiveListDirectory')")

    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains('/c')")
    self.WaitUntil(self.IsElementPresent,
                   "css=.tab-content td.proto_value:contains(423)")

  def testFileViewHasResultsTabForRDFValueCollection(self):
    collection_urn = "aff4:/C.0000000000000001/analysis/SomeFlow/results"
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(
          collection_urn, "RDFValueCollection", token=self.token) as fd:
        fd.Add(rdfvalue.StatEntry(aff4path="aff4:/some/unique/path"))

      self.GrantClientApproval("C.0000000000000001")

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("css=li[path='/analysis'] > a")
    self.Click("css=li[path='/analysis/SomeFlow'] > a")
    self.Click("css=tr:contains('results')")

    # The Results tab should appear and there should be no HexView and TextView
    # and Download tabs.
    self.WaitUntil(self.IsElementPresent, "css=#Results")
    self.WaitUntilNot(self.IsElementPresent, "css=#DownloadView")
    self.WaitUntilNot(self.IsElementPresent, "css=#FileTextViewer")
    self.WaitUntilNot(self.IsElementPresent, "css=#FileHexViewer")

    # Click on the Results tab and check that the StatEntry we added before is
    # there.
    self.Click("css=#Results")
    self.WaitUntil(self.IsTextPresent, "aff4:/some/unique/path")

  def testFileViewDoesNotHaveExportTabWhenCollectionHasNoFiles(self):
    collection_urn = "aff4:/C.0000000000000001/analysis/SomeFlow/results"
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(
          collection_urn, "RDFValueCollection", token=self.token) as fd:
        fd.Add(rdfvalue.NetworkConnection(pid=42))

      self.GrantClientApproval("C.0000000000000001")

    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("css=li[path='/analysis'] > a")
    self.Click("css=li[path='/analysis/SomeFlow'] > a")
    self.Click("css=tr:contains('results')")

    # The Results tab should appear, but the "Export" tab should be
    # disabled since we only display export hint when we have collections of
    # StatEntries or FileFinderResults.
    self.WaitUntil(self.IsElementPresent, "css=#Export.disabled")

  def CheckExportTabIsPresent(self):
    self.Open("/#c=C.0000000000000001")
    self.Click("css=a:contains('Browse Virtual Filesystem')")
    self.Click("css=li[path='/analysis'] > a")
    self.Click("css=li[path='/analysis/SomeFlow'] > a")
    self.Click("css=tr:contains('results')")

    # 'Export' tab should be there, since we're dealing with StatEntries.
    self.Click("css=#Export")
    self.WaitUntil(self.IsTextPresent,
                   "--username test --reason 'Running tests' collection_files "
                   "--path aff4:/C.0000000000000001/analysis/SomeFlow/results")

  def testFileViewHasExportTabWhenCollectionHasStatEntries(self):
    collection_urn = "aff4:/C.0000000000000001/analysis/SomeFlow/results"
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(
          collection_urn, "RDFValueCollection", token=self.token) as fd:
        fd.Add(rdfvalue.StatEntry(aff4path="aff4:/some/unique/path"))

      self.GrantClientApproval("C.0000000000000001")

    self.CheckExportTabIsPresent()

  def testFileViewHasExportTabWhenCollectionHasFileFinderResults(self):
    collection_urn = "aff4:/C.0000000000000001/analysis/SomeFlow/results"
    with self.ACLChecksDisabled():
      with aff4.FACTORY.Create(
          collection_urn, "RDFValueCollection", token=self.token) as fd:
        fd.Add(rdfvalue.FileFinderResult(
            stat_entry=rdfvalue.StatEntry(aff4path="aff4:/some/unique/path")))

      self.GrantClientApproval("C.0000000000000001")

    self.CheckExportTabIsPresent()

  def testDoubleClickGoesInsideDirectory(self):
    """Tests that double click in FileTable goes inside the directory."""

    self.Open("/")

    self.Type("client_query", "0001")
    self.Click("client_query_submit")

    self.WaitUntilEqual(u"C.0000000000000001",
                        self.GetText, "css=span[type=subject]")

    # Choose client 1 and go to 'Browse Virtual Filesystem'
    self.Click("css=td:contains('0001')")
    self.Click("css=a:contains('Browse Virtual Filesystem')")

    # Now click on "/fs" inside the table. Tree shouldn't get updated,
    # so click on "/registry".
    self.Click("css=td:contains('/fs')")
    self.Click("css=td:contains('/registry')")

    # Now double click on "/fs".
    self.DoubleClick("css=td:contains('/fs')")

    # Now we should be inside the folder, and the tree should open.
    self.WaitUntil(self.IsElementPresent,
                   "css=#_fs-os ins.jstree-icon")
    # Check that breadcrumbs got updated.
    self.WaitUntil(self.IsElementPresent,
                   "css=#main_rightTopPane .breadcrumb li:contains('fs')")


class TestHostInformation(test_lib.GRRSeleniumTest):
  """Test the host information interface."""

  def setUp(self):
    super(TestHostInformation, self).setUp()
    self.client_id = "C.0000000000000001"

    with self.ACLChecksDisabled():
      self.GrantClientApproval(self.client_id)
      with aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token) as fd:
        fd.Set(fd.Schema.USER, rdfvalue.Users())

  def testClickingOnPlusOpensHistoricalAttributes(self):
    """Test the fileview interface."""

    self.Open("/#c=" + self.client_id)
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

    # We removed all the users, so no 'Eric Jacobson' should be visible.
    self.WaitUntilNot(self.IsTextPresent, "Eric Jacobson")

    # We click on '+' in USER cell and should see historical values of the
    # USER attribute. "Eric Jacobson" was full name of the user that we've
    # deleted.
    self.Click("css=td.attribute_opener[attribute=USER]")
    self.WaitUntil(self.IsTextPresent, "Eric Jacobson")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
