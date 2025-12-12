#!/usr/bin/env python
import os

from absl import app

from grr_response_client.client_actions import read_low_level as read_low_level_actions
from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.flows.general import read_low_level
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# pylint:mode=test


class ReadLowLevelFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the ReadLowLevel Flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testReadsAndCreatesFile(self):
    """Test that the ReadLowLevel flow works."""

    path = os.path.join(self.base_path, "test_img.dd")
    test_len = 3
    test_offset = 1

    flow_id = flow_test_lib.StartAndRunFlow(
        read_low_level.ReadLowLevel,
        action_mocks.ActionMock(read_low_level_actions.ReadLowLevel),
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=rdf_read_low_level.ReadLowLevelArgs(
            path=path, length=test_len, offset=test_offset
        ),
    )

    with open(path, "rb") as fd2:
      fd2.seek(test_offset)
      expected_data = fd2.read(test_len)

      tmp_filename_str = self._generateFilename(flow_id, path)
      cp = db.ClientPath.Temp(self.client_id, [tmp_filename_str])
      fd_rel_db = file_store.OpenFile(cp)

      received_data = fd_rel_db.Read()

      self.assertEqual(test_len, len(received_data))
      self.assertEqual(expected_data, received_data)

      results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
      self.assertLen(results, 1)
      self.assertEqual(tmp_filename_str, results[0].path)

  def testReadsMultipleBlobs(self):
    """Test that the ReadLowLevel flow works."""

    path = os.path.join(self.base_path, "test_img.dd")
    # This image has ~12B, and blob sizes are set to ~4MB
    test_len = 10 * 1024 * 1024
    test_offset = 42

    flow_id = flow_test_lib.StartAndRunFlow(
        read_low_level.ReadLowLevel,
        action_mocks.ActionMock(read_low_level_actions.ReadLowLevel),
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=rdf_read_low_level.ReadLowLevelArgs(
            path=path, length=test_len, offset=test_offset
        ),
    )

    with open(path, "rb") as fd2:
      fd2.seek(test_offset)
      expected_data = fd2.read(test_len)

      tmp_filename_str = self._generateFilename(flow_id, path)
      cp = db.ClientPath.Temp(self.client_id, [tmp_filename_str])
      fd_rel_db = file_store.OpenFile(cp)
      fd_rel_db._max_unbound_read = test_len

      received_data = fd_rel_db.Read()

      self.assertEqual(test_len, len(received_data))
      self.assertEqual(expected_data, received_data)

      results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
      self.assertLen(results, 1)
      self.assertEqual(tmp_filename_str, results[0].path)

  def testFailsWithNoPath(self):
    """Test that the ReadLowLevel flow works."""

    with self.assertRaisesRegex(ValueError, "No path provided"):
      flow_test_lib.StartAndRunFlow(
          read_low_level.ReadLowLevel,
          action_mocks.ActionMock(read_low_level_actions.ReadLowLevel),
          creator=self.test_username,
          client_id=self.client_id,
      )

  def testFailsWithNegativeLen(self):
    """Test that the ReadLowLevel flow works."""

    path = os.path.join(self.base_path, "test_img.dd")
    test_len = -123

    with self.assertRaisesRegex(ValueError, r"Negative length \(-123 B\)"):
      flow_test_lib.StartAndRunFlow(
          read_low_level.ReadLowLevel,
          action_mocks.ActionMock(read_low_level_actions.ReadLowLevel),
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=rdf_read_low_level.ReadLowLevelArgs(
              path=path, length=test_len
          ),
      )

  def _generateFilename(self, flow_id: str, path: str) -> str:
    alphanumeric_only = "".join(c for c in path if c.isalnum())
    return f"{self.client_id}_{flow_id}_{alphanumeric_only}"


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
