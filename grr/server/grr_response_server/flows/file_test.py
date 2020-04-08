#!/usr/bin/env python
# Lint as: python3
"""Tests for file collection flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from absl import app

from grr_response_server.flows import file
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

EXPECTED_HASHES = {
    "auth.log": ("67b8fc07bd4b6efc3b2dce322e8ddf609b540805",
                 "264eb6ff97fc6c37c5dd4b150cb0a797",
                 "91c8d6287a095a6fa6437dac50ffe3fe5c5e0d06dff"
                 "3ae830eedfce515ad6451"),
    "dpkg.log": ("531b1cfdd337aa1663f7361b2fd1c8fe43137f4a",
                 "26973f265ce5ecc1f86bc413e65bfc1d",
                 "48303a1e7ceec679f6d417b819f42779575ffe8eabf"
                 "9c880d286a1ee074d8145"),
    "dpkg_false.log": ("a2c9cc03c613a44774ae97ed6d181fe77c13e01b",
                       "ab48f3548f311c77e75ac69ac4e696df",
                       "a35aface4b45e3f1a95b0df24efc50e14fbedcaa6a7"
                       "50ba32358eaaffe3c4fb0")
}


class TestCollectSingleFile(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.fixture_path = os.path.join(self.base_path, "searching")
    self.client_id = self.SetupClient(0)
    self.client_mock = action_mocks.FileFinderClientMockWithTimestamps()

  def testCollectSingleFileReturnsFile(self):
    path = os.path.join(self.fixture_path, "auth.log")

    flow_id = flow_test_lib.TestFlowHelper(
        file.CollectSingleFile.__name__,
        self.client_mock,
        client_id=self.client_id,
        path=path,
        token=self.token)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].stat.pathspec.path, path)
    self.assertEqual(results[0].stat.pathspec.pathtype, "OS")
    self.assertEqual(str(results[0].hash.sha1), EXPECTED_HASHES["auth.log"][0])
    self.assertEqual(str(results[0].hash.md5), EXPECTED_HASHES["auth.log"][1])
    self.assertEqual(
        str(results[0].hash.sha256), EXPECTED_HASHES["auth.log"][2])

  def testFileNotFoundRaisesError(self):
    with self.assertRaisesRegexp(RuntimeError, "Error while fetching file."):
      flow_test_lib.TestFlowHelper(
          file.CollectSingleFile.__name__,
          self.client_mock,
          client_id=self.client_id,
          path="/nonexistent",
          token=self.token)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
