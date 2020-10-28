#!/usr/bin/env python
# Lint as: python3
# python3
"""Test the webhistory flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from absl import app

import mock

from grr_response_client import client_utils
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import chrome_history
from grr_response_core.lib.parsers import firefox3_history
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import webhistory
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib


class WebHistoryFlowTestMixin(flow_test_lib.FlowTestsBaseclass):

  def MockClientRawDevWithImage(self):
    """Mock the client to run off a test image.

    Returns:
        A context manager which ensures that client actions are served off the
        test image.
    """

    def MockGetRawdevice(path):
      return rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.OS,
          path=os.path.join(self.base_path, "test_img.dd"),
          mount_point="/"), path

    return utils.Stubber(client_utils, "GetRawDevice", MockGetRawdevice)


class TestWebHistory(WebHistoryFlowTestMixin):
  """Test the browser history flows."""

  def setUp(self):
    super(TestWebHistory, self).setUp()
    # Set up client info
    users = [
        rdf_client.User(
            username="test",
            full_name="test user",
            homedir="/home/test/",
            last_logon=250)
    ]
    self.client_id = self.SetupClient(0, system="Linux", users=users)

    self.client_mock = action_mocks.FileFinderClientMock()

  def testChromeHistoryFetch(self):
    """Test that downloading the Chrome history works."""
    with self.MockClientRawDevWithImage():
      # Run the flow in the simulated way
      session_id = flow_test_lib.TestFlowHelper(
          webhistory.ChromeHistory.__name__,
          self.client_mock,
          check_flow_errors=False,
          client_id=self.client_id,
          username="test",
          token=self.token,
          pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Now check that the right files were downloaded.
    fs_path = "/home/test/.config/google-chrome/Default/History"

    components = list(filter(bool, self.base_path.split(os.path.sep)))
    components.append("test_img.dd")
    components.extend(filter(bool, fs_path.split(os.path.sep)))

    # Check if the History file is created.
    cp = db.ClientPath.TSK(self.client_id, tuple(components))
    fd = file_store.OpenFile(cp)
    self.assertGreater(len(fd.read()), 20000)

    # Check for analysis file.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    self.assertGreater(len(results), 50)
    self.assertIn("funnycats.exe", "\n".join(map(str, results)))

  def testFirefoxHistoryFetch(self):
    """Test that downloading the Firefox history works."""
    with self.MockClientRawDevWithImage():
      # Run the flow in the simulated way
      session_id = flow_test_lib.TestFlowHelper(
          webhistory.FirefoxHistory.__name__,
          self.client_mock,
          check_flow_errors=False,
          client_id=self.client_id,
          username="test",
          token=self.token,
          # This has to be TSK, since test_img.dd is an EXT3 file system.
          pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Now check that the right files were downloaded.
    fs_path = "/home/test/.mozilla/firefox/adts404t.default/places.sqlite"

    components = list(filter(bool, self.base_path.split(os.path.sep)))
    components.append("test_img.dd")
    components.extend(filter(bool, fs_path.split(os.path.sep)))

    # Check if the History file is created.
    cp = db.ClientPath.TSK(self.client_id, tuple(components))
    rel_fd = file_store.OpenFile(cp)
    self.assertEqual(rel_fd.read(15), b"SQLite format 3")

    # Check for analysis file.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    self.assertGreater(len(results), 3)
    data = "\n".join(map(str, results))
    self.assertNotEqual(data.find("Welcome to Firefox"), -1)
    self.assertNotEqual(data.find("sport.orf.at"), -1)

  def testCacheGrep(self):
    """Test the Cache Grep plugin."""
    with self.MockClientRawDevWithImage():
      # Run the flow in the simulated way
      session_id = flow_test_lib.TestFlowHelper(
          webhistory.CacheGrep.__name__,
          self.client_mock,
          check_flow_errors=False,
          client_id=self.client_id,
          grep_users=["test"],
          data_regex=b"ENIAC",
          pathtype=rdf_paths.PathSpec.PathType.TSK,
          token=self.token)

    # Check if the collection file was created.
    hits = flow_test_lib.GetFlowResults(self.client_id, session_id)
    # There should be one hit.
    self.assertLen(hits, 1)

    # Get the first hit.
    self.assertIsInstance(hits[0], rdf_client_fs.StatEntry)
    self.assertEqual(hits[0].pathspec.last.path,
                     "/home/test/.config/google-chrome/Default/Cache/data_1")


class TestWebHistoryWithArtifacts(WebHistoryFlowTestMixin):
  """Test the browser history flows."""

  def setUp(self):
    super(TestWebHistoryWithArtifacts, self).setUp()
    users = [
        rdf_client.User(
            username="test",
            full_name="test user",
            homedir="/home/test/",
            last_logon=250)
    ]
    self.client_id = self.SetupClient(
        0, system="Linux", os_version="12.04", users=users)
    self.client_mock = action_mocks.FileFinderClientMock()

  def RunCollectorAndGetCollection(self, artifact_list, client_mock=None, **kw):
    """Helper to handle running the collector flow."""
    if client_mock is None:
      client_mock = self.MockClient(client_id=self.client_id)

    # This has to be TSK, since test_img.dd is an EXT3 file system.
    with test_lib.ConfigOverrider(
        {"Server.raw_filesystem_access_pathtype": "TSK"}):

      session_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock=client_mock,
          client_id=self.client_id,
          artifact_list=artifact_list,
          token=self.token,
          **kw)

      return flow_test_lib.GetFlowResults(self.client_id, session_id)

  @parser_test_lib.WithParser("Chrome", chrome_history.ChromeHistoryParser)
  def testChrome(self):
    """Check we can run WMI based artifacts."""
    with self.MockClientRawDevWithImage():

      fd = self.RunCollectorAndGetCollection(
          [webhistory.ChromeHistory.__name__],
          client_mock=self.client_mock,
          use_raw_filesystem_access=True)

    self.assertLen(fd, 71)
    self.assertIn("/home/john/Downloads/funcats_scr.exe",
                  [d.download_path for d in fd])
    self.assertIn("http://www.java.com/", [d.url for d in fd])
    self.assertEndsWith(fd[0].source_path,
                        "/home/test/.config/google-chrome/Default/History")

  @parser_test_lib.WithParser("Firefox", firefox3_history.FirefoxHistoryParser)
  def testFirefox(self):
    """Check we can run WMI based artifacts."""
    with self.MockClientRawDevWithImage():
      fd = self.RunCollectorAndGetCollection(
          [webhistory.FirefoxHistory.__name__],
          client_mock=self.client_mock,
          use_raw_filesystem_access=True)

    self.assertLen(fd, 5)
    self.assertEqual(fd[0].access_time.AsSecondsSinceEpoch(), 1340623334)
    self.assertIn("http://sport.orf.at/", [d.url for d in fd])
    self.assertEndsWith(
        fd[0].source_path,
        "/home/test/.mozilla/firefox/adts404t.default/places.sqlite")


class MockArtifactCollectorFlow(collectors.ArtifactCollectorFlow):

  def Start(self):
    for artifact_name in self.args.artifact_list:
      self.SendReply(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(
                  path=f"/home/foo/{artifact_name}")))


class MockArtifactCollectorFlowWithDuplicatesAndExtensions(
    collectors.ArtifactCollectorFlow):
  """Mock artifact collector flow for archive mapping tests."""

  def Start(self):
    for artifact_name in self.args.artifact_list:
      self.SendReply(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(
                  path=f"/home/foo/{artifact_name}.tmp")))
      self.SendReply(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec.OS(
                  path=f"/home/bar/{artifact_name}.tmp")))


class CollectBrowserHistoryTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def _RunCollectBrowserHistory(self, **kwargs):
    flow_args = webhistory.CollectBrowserHistoryArgs(**kwargs)
    flow_id = flow_test_lib.StartAndRunFlow(
        webhistory.CollectBrowserHistory,
        creator=self.token.username,
        client_mock=action_mocks.ActionMock(),
        client_id=self.client_id,
        flow_args=flow_args)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    return flow_id, results, progress

  def _CheckProgressNotSetExceptForOne(self, progress, browser):
    self.assertLen(progress.browsers, 1)
    self.assertEqual(progress.browsers[0].browser, browser)
    self.assertEqual(progress.browsers[0].status,
                     webhistory.BrowserProgress.Status.SUCCESS)

  def testCollectsChromeArtifacts(self):
    with mock.patch.object(collectors, "ArtifactCollectorFlow",
                           MockArtifactCollectorFlow):
      flow_id, results, progress = self._RunCollectBrowserHistory(
          browsers=[webhistory.Browser.CHROME])

    self.assertLen(results, 1)
    self.assertEqual(results[0].browser, webhistory.Browser.CHROME)
    self.assertEqual(["/home/foo/ChromeHistory"],
                     [r.stat_entry.pathspec.path for r in results])
    self.assertEqual(
        list(flow_test_lib.GetFlowResultsByTag(self.client_id, flow_id).keys()),
        ["CHROME"])

    self.assertLen(progress.browsers, 1)
    self.assertEqual(progress.browsers[0].browser, webhistory.Browser.CHROME)
    self.assertEqual(progress.browsers[0].status,
                     webhistory.BrowserProgress.Status.SUCCESS)
    self.assertEqual(progress.browsers[0].num_collected_files, 1)

  def testCollectsChromeInternetExplorerAndSafariArtifacts(self):
    with mock.patch.object(collectors, "ArtifactCollectorFlow",
                           MockArtifactCollectorFlow):
      flow_id, results, progress = self._RunCollectBrowserHistory(browsers=[
          webhistory.Browser.CHROME, webhistory.Browser.INTERNET_EXPLORER,
          webhistory.Browser.SAFARI
      ])

    # MockArtifactCollectorFlow will produce a single stat entry with a
    # pathspec /home/foo/<artifact name> for each artifact scheduled for
    # collection. Hence, by looking at results we can make sure that
    # all artifacts were scheduled for collection.
    pathspecs = [r.stat_entry.pathspec for r in results]
    self.assertCountEqual(
        ["ChromeHistory", "InternetExplorerHistory", "SafariHistory"],
        [p.Basename() for p in pathspecs])
    # Check that tags for all browsers are present in the results set.
    self.assertCountEqual(
        flow_test_lib.GetFlowResultsByTag(self.client_id, flow_id).keys(),
        ["CHROME", "INTERNET_EXPLORER", "SAFARI"])

    self.assertLen(progress.browsers, 3)
    self.assertCountEqual([
        webhistory.Browser.CHROME, webhistory.Browser.INTERNET_EXPLORER,
        webhistory.Browser.SAFARI
    ], [bp.browser for bp in progress.browsers])
    for bp in progress.browsers:
      self.assertEqual(bp.status, webhistory.BrowserProgress.Status.SUCCESS)
      self.assertEqual(bp.num_collected_files, 1)

  def testCorrectlyGeneratesArchiveMappings(self):
    with mock.patch.object(collectors, "ArtifactCollectorFlow",
                           MockArtifactCollectorFlow):
      flow_id, _, _ = self._RunCollectBrowserHistory(browsers=[
          webhistory.Browser.CHROME,
          webhistory.Browser.SAFARI,
      ])
      flow = flow_base.FlowBase.CreateFlowInstance(
          flow_test_lib.GetFlowObj(self.client_id, flow_id))
      results = flow_test_lib.GetRawFlowResults(self.client_id, flow_id)

      mappings = flow.GetFilesArchiveMappings(results)

    self.assertCountEqual(mappings, [
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id, ("home", "foo", "ChromeHistory")),
            "chrome/ChromeHistory",
        ),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id, ("home", "foo", "SafariHistory")),
            "safari/SafariHistory",
        ),
    ])

  def testCorrectlyGeneratesArchiveMappingsForDuplicateFiles(self):
    with mock.patch.object(
        collectors, "ArtifactCollectorFlow",
        MockArtifactCollectorFlowWithDuplicatesAndExtensions):
      flow_id, _, _ = self._RunCollectBrowserHistory(browsers=[
          webhistory.Browser.CHROME,
          webhistory.Browser.SAFARI,
      ])
      flow = flow_base.FlowBase.CreateFlowInstance(
          flow_test_lib.GetFlowObj(self.client_id, flow_id))
      results = flow_test_lib.GetRawFlowResults(self.client_id, flow_id)

      mappings = flow.GetFilesArchiveMappings(results)

    self.assertCountEqual(mappings, [
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             ("home", "foo", "ChromeHistory.tmp")),
            "chrome/ChromeHistory.tmp",
        ),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             ("home", "bar", "ChromeHistory.tmp")),
            "chrome/ChromeHistory_1.tmp",
        ),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             ("home", "foo", "SafariHistory.tmp")),
            "safari/SafariHistory.tmp",
        ),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             ("home", "bar", "SafariHistory.tmp")),
            "safari/SafariHistory_1.tmp",
        ),
    ])

  def testFailsForEmptyBrowsersList(self):
    with self.assertRaisesRegex(
        RuntimeError, "Need to collect at least one type of history."):
      self._RunCollectBrowserHistory()


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
