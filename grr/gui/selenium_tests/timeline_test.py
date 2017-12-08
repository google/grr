#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the timeline view."""


import mock
import unittest
from grr.gui import api_call_router_with_approval_checks
from grr.gui import gui_test_lib
from grr.gui.api_plugins import vfs as api_vfs

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server.aff4_objects import aff4_grr
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


class TestTimeline(gui_test_lib.GRRSeleniumTest):
  """Test the timeline view interface."""

  TIMELINE_ITEMS_PER_FILE = 3

  def setUp(self):
    super(TestTimeline, self).setUp()
    # Prepare our fixture.
    fixture_test_lib.ClientFixture("C.0000000000000001", token=self.token)
    self.CreateFileWithTimeline(
        "aff4:/C.0000000000000001/fs/os/c/proc/changed.txt", self.token)
    self.CreateFileWithTimeline(
        "aff4:/C.0000000000000001/fs/os/c/proc/other.txt", self.token)
    self.RequestAndGrantClientApproval("C.0000000000000001")

  @staticmethod
  def CreateFileWithTimeline(file_path, token):
    """Add a file with timeline."""

    # Add a version of the file at gui_test_lib.TIME_0. Since we write all MAC
    # times, this will result in three timeline items.
    with test_lib.FakeTime(gui_test_lib.TIME_0):
      with aff4.FACTORY.Create(
          file_path, aff4_grr.VFSFile, mode="w", token=token) as fd:
        stats = rdf_client.StatEntry(
            st_atime=gui_test_lib.TIME_0.AsSecondsFromEpoch() + 1000,
            st_mtime=gui_test_lib.TIME_0.AsSecondsFromEpoch(),
            st_ctime=gui_test_lib.TIME_0.AsSecondsFromEpoch() - 1000)
        fd.Set(fd.Schema.STAT, stats)

    # Add a version with a stat entry, but without timestamps.
    with test_lib.FakeTime(gui_test_lib.TIME_1):
      with aff4.FACTORY.Create(
          file_path, aff4_grr.VFSFile, mode="w", token=token) as fd:
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
        gui_test_lib.DateString(gui_test_lib.TIME_1), self.GetText,
        "css=.version-dropdown > option[selected]")

    # The last timeline item for changed.txt has a timestamp before
    # gui_test_lib.TIME_0, which is the first available file version.
    self.Click("css=grr-file-timeline table tr "
               "td:contains('changed.txt'):last")
    self.WaitUntilContains("changed.txt", self.GetText,
                           "css=div#main_bottomPane h1")
    self.WaitUntilContains(
        gui_test_lib.DateString(gui_test_lib.TIME_0), self.GetText,
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

  def testClickingOnTreeNodeRefreshesTimeline(self):
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
    self.CreateFileWithTimeline(
        "aff4:/C.0000000000000001/fs/os/c/proc/newly_added.txt",
        token=self.token)

    # Click on tree again.
    self.Click("link=proc")

    # Wait until the UI finished loading.
    self.WaitUntilEqual(3 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-file-timeline td:contains('newly_added.txt')")

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetVfsTimelineAsCsv")
  def testClickingOnDownloadTimelineButtonInitiatesDownload(self, mock_method):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    self.Click("css=button[name=timelineDropdown]:not([disabled])")
    self.Click("css=a[name=downloadTimeline]")
    self.WaitUntilEqual(1, lambda: mock_method.call_count)
    mock_method.assert_called_once_with(
        api_vfs.ApiGetVfsTimelineAsCsvArgs(
            client_id="C.0000000000000001", file_path="fs/os/c/proc"),
        token=mock.ANY)


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
