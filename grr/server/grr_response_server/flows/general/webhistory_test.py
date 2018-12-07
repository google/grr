#!/usr/bin/env python
"""Test the webhistory flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from grr_response_client import client_utils
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import chrome_history
from grr_response_core.lib.parsers import firefox3_history
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import webhistory
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
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


@db_test_lib.DualDBTest
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

    output_path = self.client_id.Add("fs/tsk").Add(
        self.base_path.replace("\\", "/")).Add("test_img.dd").Add(
            fs_path.replace("\\", "/"))

    # Check if the History file is created.
    if data_store.RelationalDBReadEnabled("filestore"):
      cp = db.ClientPath.TSK(self.client_id.Basename(),
                             tuple(output_path.Split()[3:]))
      fd = file_store.OpenFile(cp)
      self.assertGreater(len(fd.read()), 20000)
    else:
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      self.assertGreater(fd.size, 20000)

    # Check for analysis file.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    self.assertGreater(len(results), 50)
    self.assertIn("funnycats.exe", "\n".join(map(unicode, results)))

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
          pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Now check that the right files were downloaded.
    fs_path = "/home/test/.mozilla/firefox/adts404t.default/places.sqlite"

    output_path = self.client_id.Add("fs/tsk").Add("/".join(
        [self.base_path.replace("\\", "/"), "test_img.dd"])).Add(
            fs_path.replace("\\", "/"))

    # Check if the History file is created.
    if data_store.RelationalDBReadEnabled("filestore"):
      cp = db.ClientPath.TSK(self.client_id.Basename(),
                             tuple(output_path.Split()[3:]))
      rel_fd = file_store.OpenFile(cp)
      self.assertEqual(rel_fd.read(15), "SQLite format 3")
    else:
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      self.assertGreater(fd.size, 20000)
      self.assertEqual(fd.read(15), "SQLite format 3")

    # Check for analysis file.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    self.assertGreater(len(results), 3)
    data = "\n".join(map(unicode, results))
    self.assertTrue(data.find("Welcome to Firefox") != -1)
    self.assertTrue(data.find("sport.orf.at") != -1)

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
          data_regex="ENIAC",
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


@db_test_lib.DualDBTest
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
          use_tsk=True)

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
          use_tsk=True)

    self.assertLen(fd, 5)
    self.assertEqual(fd[0].access_time.AsSecondsSinceEpoch(), 1340623334)
    self.assertIn("http://sport.orf.at/", [d.url for d in fd])
    self.assertEndsWith(
        fd[0].source_path,
        "/home/test/.mozilla/firefox/adts404t.default/places.sqlite")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
