#!/usr/bin/env python
"""Tests for the RegistryFinder flow."""

from absl import app

from grr_response_server.flows.general import registry_finder as flow_registry_finder
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class TestStubbedRegistryFinderFlow(flow_test_lib.FlowTestsBaseclass):
  """Test the RegistryFinder flow."""

  def setUp(self):
    super().setUp()
    registry_stubber = vfs_test_lib.RegistryVFSStubber()
    registry_stubber.Start()
    self.addCleanup(registry_stubber.Stop)

  def _RunRegistryFinder(self, paths=None):
    client_mock = action_mocks.ClientFileFinderWithVFS()

    client_id = self.SetupClient(0)

    session_id = flow_test_lib.StartAndRunFlow(
        flow_registry_finder.RegistryFinder,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        flow_args=flow_registry_finder.RegistryFinderArgs(
            keys_paths=paths,
            conditions=[],
        ),
    )

    return flow_test_lib.GetFlowResults(client_id, session_id)

  def testRegistryFinder(self):
    # Listing inside a key gives the values.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/*"]
    )
    self.assertLen(results, 2)
    self.assertCountEqual(
        [x.stat_entry.registry_data.GetValue() for x in results],
        ["Value1", "Value2"],
    )

    # This is a key so we should get back the default value.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"]
    )

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].stat_entry.registry_data.GetValue(), "DefaultValue"
    )

    # The same should work using a wildcard.
    results = self._RunRegistryFinder(["HKEY_LOCAL_MACHINE/SOFTWARE/*"])

    self.assertTrue(results)
    paths = [x.stat_entry.pathspec.path for x in results]
    expected_path = "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest"
    self.assertIn(expected_path, paths)
    idx = paths.index(expected_path)
    self.assertEqual(
        results[idx].stat_entry.registry_data.GetValue(), "DefaultValue"
    )

  def testListingRegistryKeysDoesYieldMTimes(self):
    # Just listing all keys does generate a full stat entry for each of
    # the results.
    results = self._RunRegistryFinder(
        ["HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/*"]
    )
    results = sorted(results, key=lambda x: x.stat_entry.pathspec.path)

    # We expect 2 results: Value1 and Value2.
    self.assertLen(results, 2)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value1",
    )
    self.assertEqual(results[0].stat_entry.st_mtime, 110)
    self.assertEqual(
        results[1].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value2",
    )
    self.assertEqual(results[1].stat_entry.st_mtime, 120)

    # Explicitly calling RegistryFinder on a value does that as well.
    results = self._RunRegistryFinder([
        "HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value1",
        "HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value2",
    ])
    results = sorted(results, key=lambda x: x.stat_entry.pathspec.path)

    # We expect 2 results: Value1 and Value2.
    self.assertLen(results, 2)
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value1",
    )
    self.assertEqual(results[0].stat_entry.st_mtime, 110)
    self.assertEqual(
        results[1].stat_entry.pathspec.path,
        "/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest/Value2",
    )
    self.assertEqual(results[1].stat_entry.st_mtime, 120)

  def testListingRegistryHivesRaises(self):
    with self.assertRaisesRegex(RuntimeError, "is not absolute"):
      self._RunRegistryFinder(["*"])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
