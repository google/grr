#!/usr/bin/env python
"""Test the webhistory flows."""
import os

from grr_response_client import client_utils
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import collectors
from grr.server.grr_response_server.flows.general import webhistory
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class WebHistoryFlowTest(flow_test_lib.FlowTestsBaseclass):

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


class TestWebHistory(WebHistoryFlowTest):
  """Test the browser history flows."""

  def setUp(self):
    super(TestWebHistory, self).setUp()
    # Set up client info
    self.client_id = self.SetupClient(0)
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    self.client.Set(self.client.Schema.SYSTEM("Linux"))

    kb = self.client.Get(self.client.Schema.KNOWLEDGE_BASE)
    kb.MergeOrAddUser(
        rdf_client.User(
            username="test",
            full_name="test user",
            homedir="/home/test/",
            last_logon=250))
    self.client.Set(kb)
    self.client.Close()

    self.client_mock = action_mocks.FileFinderClientMock()

  def tearDown(self):
    super(TestWebHistory, self).tearDown()

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

    # Check if the History file is created.
    output_path = self.client_id.Add("fs/tsk").Add(
        self.base_path.replace("\\", "/")).Add("test_img.dd").Add(
            fs_path.replace("\\", "/"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    self.assertTrue(fd.size > 20000)

    # Check for analysis file.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertGreater(len(fd), 50)
    self.assertIn("funnycats.exe",
                  "\n".join([utils.SmartStr(x) for x in fd.GenerateItems()]))

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
    # Check if the History file is created.
    output_path = self.client_id.Add("fs/tsk").Add("/".join(
        [self.base_path.replace("\\", "/"), "test_img.dd"])).Add(
            fs_path.replace("\\", "/"))
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    self.assertTrue(fd.size > 20000)
    self.assertEqual(fd.read(15), "SQLite format 3")

    # Check for analysis file.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertGreater(len(fd), 3)
    data = "\n".join([utils.SmartStr(x) for x in fd.GenerateItems()])
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
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    # There should be one hit.
    self.assertEqual(len(fd), 1)

    # Get the first hit.
    hits = list(fd)

    self.assertIsInstance(hits[0], rdf_client.StatEntry)

    self.assertEqual(hits[0].pathspec.last.path,
                     "/home/test/.config/google-chrome/Default/Cache/data_1")


class TestWebHistoryWithArtifacts(WebHistoryFlowTest):
  """Test the browser history flows."""

  def setUp(self):
    super(TestWebHistoryWithArtifacts, self).setUp()
    self.client_id = self.SetupClient(0, system="Linux", os_version="12.04")
    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    self.kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
    self.kb.users.Append(
        rdf_client.User(
            username="test",
            full_name="test user",
            homedir="/home/test/",
            last_logon=250))
    fd.AddAttribute(fd.Schema.KNOWLEDGE_BASE, self.kb)
    fd.Flush()

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

    return flow.GRRFlow.ResultCollectionForFID(session_id)

  def testChrome(self):
    """Check we can run WMI based artifacts."""
    with self.MockClientRawDevWithImage():

      fd = self.RunCollectorAndGetCollection(
          [webhistory.ChromeHistory.__name__],
          client_mock=self.client_mock,
          use_tsk=True,
          knowledge_base=self.kb)

    self.assertEqual(len(fd), 71)
    self.assertTrue(
        "/home/john/Downloads/funcats_scr.exe" in [d.download_path for d in fd])
    self.assertTrue("http://www.java.com/" in [d.url for d in fd])
    self.assertTrue(fd[0].source_urn.Path().endswith(
        "/home/test/.config/google-chrome/Default/History"))

  def testFirefox(self):
    """Check we can run WMI based artifacts."""
    with self.MockClientRawDevWithImage():
      fd = self.RunCollectorAndGetCollection(
          [webhistory.FirefoxHistory.__name__],
          client_mock=self.client_mock,
          use_tsk=True)

    self.assertEqual(len(fd), 5)
    self.assertEqual(fd[0].access_time.AsSecondsSinceEpoch(), 1340623334)
    self.assertTrue("http://sport.orf.at/" in [d.url for d in fd])
    self.assertTrue(fd[0].source_urn.Path().endswith(
        "/home/test/.mozilla/firefox/adts404t.default/places.sqlite"))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
