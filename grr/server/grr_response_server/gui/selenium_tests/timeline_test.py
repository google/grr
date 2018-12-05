#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the timeline view."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import mock

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths

from grr_response_server.flows.general import filesystem
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr.test_lib import db_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestTimeline(gui_test_lib.GRRSeleniumTest):
  """Test the timeline view interface."""

  TIMELINE_ITEMS_PER_FILE = 3

  def setUp(self):
    super(TestTimeline, self).setUp()
    # Prepare our fixture.
    fixture_test_lib.ClientFixture(u"C.0000000000000001", token=self.token)
    self.CreateFileWithTimeline(
        rdf_client.ClientURN(u"C.0000000000000001"), "c/proc/changed.txt",
        rdf_paths.PathSpec.PathType.OS, self.token)
    self.CreateFileWithTimeline(
        rdf_client.ClientURN(u"C.0000000000000001"), "c/proc/other.txt",
        rdf_paths.PathSpec.PathType.OS, self.token)
    self.RequestAndGrantClientApproval(u"C.0000000000000001")

  @staticmethod
  def CreateFileWithTimeline(client_id, path, path_type, token):
    """Add a file with timeline."""

    # Add a version of the file at gui_test_lib.TIME_0. Since we write all MAC
    # times, this will result in three timeline items.
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = path
    stat_entry.pathspec.pathtype = path_type
    stat_entry.st_atime = gui_test_lib.TIME_0.AsSecondsSinceEpoch() + 1000
    stat_entry.st_mtime = gui_test_lib.TIME_0.AsSecondsSinceEpoch()
    stat_entry.st_ctime = gui_test_lib.TIME_0.AsSecondsSinceEpoch() - 1000

    with test_lib.FakeTime(gui_test_lib.TIME_0):
      filesystem.WriteStatEntries([stat_entry],
                                  client_id.Basename(),
                                  mutation_pool=None,
                                  token=token)

    # Add a version with a stat entry, but without timestamps.
    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = path
    stat_entry.pathspec.pathtype = path_type
    stat_entry.st_ino = 99

    with test_lib.FakeTime(gui_test_lib.TIME_1):
      filesystem.WriteStatEntries([stat_entry],
                                  client_id.Basename(),
                                  mutation_pool=None,
                                  token=token)

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
        rdf_client.ClientURN("C.0000000000000001"), "c/proc/newly_added.txt",
        rdf_paths.PathSpec.PathType.OS, self.token)

    # Click on tree again.
    self.Click("link=proc")

    # Wait until the UI finished loading.
    self.WaitUntilEqual(3 * self.TIMELINE_ITEMS_PER_FILE, self.GetCssCount,
                        "css=grr-file-timeline tbody tr")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-file-timeline td:contains('newly_added.txt')")

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetVfsTimelineAsCsv",
      return_value=api_vfs.ApiGetVfsTimelineAsCsvHandler())
  def testClickingOnDownloadTimelineInGrrFormatButtonInitiatesDownload(
      self, mock_method):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    self.Click("css=button[name=timelineDropdown]:not([disabled])")
    self.Click("css=a[name=downloadTimelineGrrFormat]")

    self.WaitUntil(lambda: mock_method.call_count)
    # Mock method will be called twice: once for HEAD request (to check
    # permissions) and once for GET request.
    mock_method.assert_called_with(
        api_vfs.ApiGetVfsTimelineAsCsvArgs(
            client_id=u"C.0000000000000001",
            file_path="fs/os/c/proc",
            format=api_vfs.ApiGetVfsTimelineAsCsvArgs.Format.GRR),
        token=mock.ANY)

  @mock.patch.object(
      api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks,
      "GetVfsTimelineAsCsv",
      return_value=api_vfs.ApiGetVfsTimelineAsCsvHandler())
  def testClickingOnDownloadTimelineInBodyFormatButtonInitiatesDownload(
      self, mock_method):
    # Open VFS view for client 1 on a specific location.
    self.Open("/#c=C.0000000000000001&main=VirtualFileSystemView"
              "&t=_fs-os-c-proc")

    self.Click("css=button[name=timelineDropdown]:not([disabled])")
    self.Click("css=a[name=downloadTimelineBodyFormat]")

    self.WaitUntil(lambda: mock_method.call_count > 0)
    # Mock method will be called twice: once for HEAD request (to check
    # permissions) and once for GET request.
    mock_method.assert_called_with(
        api_vfs.ApiGetVfsTimelineAsCsvArgs(
            client_id=u"C.0000000000000001",
            file_path="fs/os/c/proc",
            format=api_vfs.ApiGetVfsTimelineAsCsvArgs.Format.BODY),
        token=mock.ANY)


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
