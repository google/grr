#!/usr/bin/env python
"""Test the webhistory flows."""

import os
import time

from grr.client import client_utils_linux
from grr.client import client_utils_osx
from grr.client.client_actions import standard
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import collects
# pylint: disable=unused-import
from grr.lib.flows.general import webhistory
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class WebHistoryFlowTest(test_lib.FlowTestsBaseclass):
  pass


class TestWebHistory(WebHistoryFlowTest):
  """Test the browser history flows."""

  def setUp(self):
    super(TestWebHistory, self).setUp()
    # Set up client info
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    self.client.Set(self.client.Schema.SYSTEM("Linux"))

    kb = self.client.Get(self.client.Schema.KNOWLEDGE_BASE)
    kb.MergeOrAddUser(rdf_client.User(username="test",
                                      full_name="test user",
                                      homedir="/home/test/",
                                      last_logon=250))
    self.client.Set(kb)
    self.client.Close()

    self.client_mock = action_mocks.ActionMock("ReadBuffer", "FingerprintFile",
                                               "HashBuffer", "TransferBuffer",
                                               "StatFile", "Find",
                                               "ListDirectory", "Grep")

    # Mock the client to make it look like the root partition is mounted off the
    # test image. This will force all flow access to come off the image.
    def MockGetMountpoints():
      return {"/": (os.path.join(self.base_path, "test_img.dd"), "ext2")}

    self.orig_linux_mp = client_utils_linux.GetMountpoints
    self.orig_osx_mp = client_utils_osx.GetMountpoints
    client_utils_linux.GetMountpoints = MockGetMountpoints
    client_utils_osx.GetMountpoints = MockGetMountpoints

    # We wiped the data_store so we have to retransmit all blobs.
    standard.HASH_CACHE = utils.FastStore(100)

  def tearDown(self):
    super(TestWebHistory, self).tearDown()
    client_utils_linux.GetMountpoints = self.orig_linux_mp
    client_utils_osx.GetMountpoints = self.orig_osx_mp

  def testChromeHistoryFetch(self):
    """Test that downloading the Chrome history works."""
    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("ChromeHistory",
                                     self.client_mock,
                                     check_flow_errors=False,
                                     client_id=self.client_id,
                                     username="test",
                                     token=self.token,
                                     output="analysis/testfoo",
                                     pathtype=rdf_paths.PathSpec.PathType.TSK):
      pass

    # Now check that the right files were downloaded.
    fs_path = "/home/test/.config/google-chrome/Default/History"

    # Check if the History file is created.
    output_path = self.client_id.Add("fs/tsk").Add(self.base_path.replace(
        "\\", "/")).Add("test_img.dd").Add(fs_path.replace("\\", "/"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    self.assertTrue(fd.size > 20000)

    # Check for analysis file.
    output_path = self.client_id.Add("analysis/testfoo")
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    self.assertTrue(fd.size > 20000)
    self.assertTrue(fd.Read(5000).find("funnycats.exe") != -1)

  def testFirefoxHistoryFetch(self):
    """Test that downloading the Firefox history works."""
    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("FirefoxHistory",
                                     self.client_mock,
                                     check_flow_errors=False,
                                     client_id=self.client_id,
                                     username="test",
                                     token=self.token,
                                     output="analysis/ff_out",
                                     pathtype=rdf_paths.PathSpec.PathType.TSK):
      pass

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
    output_path = self.client_id.Add("analysis/ff_out")
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    self.assertTrue(fd.size > 400)
    data = fd.Read(1000)
    self.assertTrue(data.find("Welcome to Firefox") != -1)
    self.assertTrue(data.find("sport.orf.at") != -1)

  def testCacheGrep(self):
    """Test the Cache Grep plugin."""
    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("CacheGrep",
                                     self.client_mock,
                                     check_flow_errors=False,
                                     client_id=self.client_id,
                                     grep_users=["test"],
                                     data_regex="ENIAC",
                                     output="analysis/cachegrep/{u}",
                                     pathtype=rdf_paths.PathSpec.PathType.TSK,
                                     token=self.token):
      pass

    # Check if the collection file was created.
    output_path = self.client_id.Add("analysis/cachegrep").Add("test")

    fd = aff4.FACTORY.Open(output_path,
                           aff4_type=collects.RDFValueCollection,
                           token=self.token)

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
    self.SetupClients(1, system="Linux", os_version="12.04")
    fd = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    self.kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
    self.kb.users.Append(rdf_client.User(username="test",
                                         full_name="test user",
                                         homedir="/home/test/",
                                         last_logon=250))
    fd.AddAttribute(fd.Schema.KNOWLEDGE_BASE, self.kb)
    fd.Flush()

    self.client_mock = action_mocks.ActionMock("ReadBuffer", "FingerprintFile",
                                               "HashBuffer", "HashFile",
                                               "TransferBuffer", "StatFile",
                                               "Find", "ListDirectory")

  def MockClientMountPointsWithImage(self, image_path, fs_type="ext2"):
    """Mock the client to run off a test image.

    Args:
       image_path: The path to the image file.
       fs_type: The filesystem in the image.

    Returns:
        A context manager which ensures that client actions are served off the
        test image.
    """

    def MockGetMountpoints():
      return {"/": (image_path, fs_type)}

    return utils.MultiStubber(
        (client_utils_linux, "GetMountpoints", MockGetMountpoints),
        (client_utils_osx, "GetMountpoints", MockGetMountpoints),
        (standard, "HASH_CACHE", utils.FastStore(100)))

  def RunCollectorAndGetCollection(self, artifact_list, client_mock=None, **kw):
    """Helper to handle running the collector flow."""
    if client_mock is None:
      client_mock = self.MockClient(client_id=self.client_id)

    output_name = "/analysis/output/%s" % int(time.time())

    for _ in test_lib.TestFlowHelper("ArtifactCollectorFlow",
                                     client_mock=client_mock,
                                     output=output_name,
                                     client_id=self.client_id,
                                     artifact_list=artifact_list,
                                     token=self.token,
                                     **kw):
      pass

    output_urn = self.client_id.Add(output_name)
    return aff4.FACTORY.Open(output_urn,
                             aff4_type=collects.RDFValueCollection,
                             token=self.token)

  def testChrome(self):
    """Check we can run WMI based artifacts."""
    with self.MockClientMountPointsWithImage(os.path.join(self.base_path,
                                                          "test_img.dd")):

      fd = self.RunCollectorAndGetCollection(
          ["ChromeHistory"],
          client_mock=self.client_mock,
          use_tsk=True,
          knowledge_base=self.kb)

    self.assertEqual(len(fd), 71)
    self.assertTrue("/home/john/Downloads/funcats_scr.exe" in [d.download_path
                                                               for d in fd])
    self.assertTrue("http://www.java.com/" in [d.url for d in fd])
    self.assertTrue(fd[0].source_urn.Path().endswith(
        "/home/test/.config/google-chrome/Default/History"))

  def testFirefox(self):
    """Check we can run WMI based artifacts."""
    with self.MockClientMountPointsWithImage(os.path.join(self.base_path,
                                                          "test_img.dd")):
      fd = self.RunCollectorAndGetCollection(
          ["FirefoxHistory"],
          client_mock=self.client_mock,
          use_tsk=True)

    self.assertEqual(len(fd), 5)
    self.assertEqual(fd[0].access_time.AsSecondsFromEpoch(), 1340623334)
    self.assertTrue("http://sport.orf.at/" in [d.url for d in fd])
    self.assertTrue(fd[0].source_urn.Path().endswith(
        "/home/test/.mozilla/firefox/adts404t.default/places.sqlite"))


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
