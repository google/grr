#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the registry flows."""

import os

from grr import config
from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import artifact
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import registry
from grr.server.grr_response_server.flows.general import transfer
from grr.test_lib import action_mocks
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class RegistryFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(RegistryFlowTest, self).setUp()
    self.vfs_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler)
    self.vfs_overrider.Start()

  def tearDown(self):
    super(RegistryFlowTest, self).tearDown()
    self.vfs_overrider.Stop()


class TestFakeRegistryFinderFlow(RegistryFlowTest):
  """Tests for the RegistryFinder flow."""

  runkey = "HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"

  def RunFlow(self, client_id, keys_paths=None, conditions=None):
    if keys_paths is None:
      keys_paths = [
          "HKEY_USERS/S-1-5-20/Software/Microsoft/"
          "Windows/CurrentVersion/Run/*"
      ]
    if conditions is None:
      conditions = []

    client_mock = action_mocks.ActionMock(
        searching.Find,
        searching.Grep,
    )

    session_id = flow_test_lib.TestFlowHelper(
        registry.RegistryFinder.__name__,
        client_mock,
        client_id=client_id,
        keys_paths=keys_paths,
        conditions=conditions,
        token=self.token)

    return session_id

  def AssertNoResults(self, session_id):
    res = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(res), 0)

  def GetResults(self, session_id):
    return list(flow.GRRFlow.ResultCollectionForFID(session_id))

  def testFindsNothingIfNothingMatchesTheGlob(self):
    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/NonMatch*"
    ])
    self.AssertNoResults(session_id)

  def testFindsKeysWithSingleGlobWithoutConditions(self):
    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/*"
    ])

    results = self.GetResults(session_id)
    self.assertEqual(len(results), 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    basenames = [os.path.basename(r.stat_entry.pathspec.path) for r in results]
    self.assertItemsEqual(basenames, ["Sidebar", "MctAdmin"])

  def testFindsKeysWithTwoGlobsWithoutConditions(self):
    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/Side*",
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/Mct*"
    ])

    results = self.GetResults(session_id)
    self.assertEqual(len(results), 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    basenames = [os.path.basename(r.stat_entry.pathspec.path) for r in results]
    self.assertItemsEqual(basenames, ["Sidebar", "MctAdmin"])

  def testFindsKeyWithInterpolatedGlobWithoutConditions(self):
    # Initialize client's knowledge base in order for the interpolation
    # to work.
    user = rdf_client.User(sid="S-1-5-20")
    kb = rdf_client.KnowledgeBase(users=[user])
    client_id = self.SetupClient(0)

    with aff4.FACTORY.Open(client_id, mode="rw", token=self.token) as client:
      client.Set(client.Schema.KNOWLEDGE_BASE, kb)

    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/%%users.sid%%/Software/Microsoft/Windows/"
        "CurrentVersion/*"
    ])

    results = self.GetResults(session_id)
    self.assertEqual(len(results), 1)

    key = ("/HKEY_USERS/S-1-5-20/"
           "Software/Microsoft/Windows/CurrentVersion/Run")

    self.assertEqual(results[0].stat_entry.AFF4Path(client_id),
                     "aff4:/C.1000000000000000/registry" + key)
    self.assertEqual(results[0].stat_entry.pathspec.path, key)
    self.assertEqual(results[0].stat_entry.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.REGISTRY)

  def testFindsNothingIfNothingMatchesLiteralMatchCondition(self):
    vlm = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10, bytes_after=10, literal="CanNotFindMe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_LITERAL_MATCH,
            value_literal_match=vlm)
    ])
    self.AssertNoResults(session_id)

  def testFindsKeyIfItMatchesLiteralMatchCondition(self):
    vlm = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10, bytes_after=10, literal="Windows Sidebar\\Sidebar.exe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_LITERAL_MATCH,
            value_literal_match=vlm)
    ])

    results = self.GetResults(session_id)
    self.assertEqual(len(results), 1)
    self.assertEqual(len(results[0].matches), 1)

    self.assertEqual(results[0].matches[0].offset, 15)
    self.assertEqual(results[0].matches[0].data,
                     "ramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun")

    self.assertEqual(
        results[0].stat_entry.AFF4Path(client_id),
        "aff4:/C.1000000000000000/registry/HKEY_USERS/S-1-5-20/"
        "Software/Microsoft/Windows/CurrentVersion/Run/Sidebar")
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
        "CurrentVersion/Run/Sidebar")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.REGISTRY)

  def testFindsNothingIfRegexMatchesNothing(self):
    value_regex_match = rdf_file_finder.FileFinderContentsRegexMatchCondition(
        bytes_before=10, bytes_after=10, regex=".*CanNotFindMe.*")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_REGEX_MATCH,
            value_regex_match=value_regex_match)
    ])
    self.AssertNoResults(session_id)

  def testFindsKeyIfItMatchesRegexMatchCondition(self):
    value_regex_match = rdf_file_finder.FileFinderContentsRegexMatchCondition(
        bytes_before=10, bytes_after=10, regex="Windows.+\\.exe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_REGEX_MATCH,
            value_regex_match=value_regex_match)
    ])

    results = self.GetResults(session_id)
    self.assertEqual(len(results), 1)
    self.assertEqual(len(results[0].matches), 1)

    self.assertEqual(results[0].matches[0].offset, 15)
    self.assertEqual(results[0].matches[0].data,
                     "ramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun")

    self.assertEqual(
        results[0].stat_entry.AFF4Path(client_id),
        "aff4:/C.1000000000000000/registry/HKEY_USERS/S-1-5-20/"
        "Software/Microsoft/Windows/CurrentVersion/Run/Sidebar")
    self.assertEqual(
        results[0].stat_entry.pathspec.path,
        "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
        "CurrentVersion/Run/Sidebar")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.REGISTRY)

  def testFindsNothingIfModiciationTimeConditionMatchesNothing(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0),
        max_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            MODIFICATION_TIME,
            modification_time=modification_time)
    ])
    self.AssertNoResults(session_id)

  def testFindsKeysIfModificationTimeConditionMatches(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 - 1),
        max_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 + 1))

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            MODIFICATION_TIME,
            modification_time=modification_time)
    ])

    results = self.GetResults(session_id)
    self.assertEqual(len(results), 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    basenames = [os.path.basename(r.stat_entry.pathspec.path) for r in results]
    self.assertItemsEqual(basenames, ["Sidebar", "MctAdmin"])

  def testFindsKeyWithLiteralAndModificationTimeConditions(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 - 1),
        max_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 + 1))

    vlm = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10, bytes_after=10, literal="Windows Sidebar\\Sidebar.exe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            MODIFICATION_TIME,
            modification_time=modification_time),
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_LITERAL_MATCH,
            value_literal_match=vlm)
    ])

    results = self.GetResults(session_id)
    self.assertEqual(len(results), 1)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    self.assertEqual(
        results[0].stat_entry.AFF4Path(client_id),
        "aff4:/C.1000000000000000/registry/HKEY_USERS/S-1-5-20/"
        "Software/Microsoft/Windows/CurrentVersion/Run/Sidebar")

  def testSizeCondition(self):
    client_id = self.SetupClient(0)
    # There are two values, one is 20 bytes, the other 53.
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.SIZE,
            size=rdf_file_finder.FileFinderSizeCondition(min_file_size=50))
    ])
    results = self.GetResults(session_id)
    self.assertEqual(len(results), 1)
    self.assertGreater(results[0].stat_entry.st_size, 50)


class TestRegistryFlows(RegistryFlowTest):
  """Test the Run Key registry flows."""

  def testCollectRunKeyBinaries(self):
    """Read Run key from the client_fixtures to test parsing and storage."""
    client_id = self.SetupClient(0)
    fixture_test_lib.ClientFixture(client_id, token=self.token)

    client = aff4.FACTORY.Open(client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))

    client_info = client.Get(client.Schema.CLIENT_INFO)
    client_info.client_version = config.CONFIG["Source.version_numeric"]
    client.Set(client.Schema.CLIENT_INFO, client_info)

    client.Flush()

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.FakeFullVFSHandler):

      client_mock = action_mocks.ActionMock(
          file_fingerprint.FingerprintFile,
          searching.Find,
          standard.GetFileStat,
      )

      # Get KB initialized
      session_id = flow_test_lib.TestFlowHelper(
          artifact.KnowledgeBaseInitializationFlow.__name__,
          client_mock,
          client_id=client_id,
          token=self.token)

      col = flow.GRRFlow.ResultCollectionForFID(session_id)
      client.Set(client.Schema.KNOWLEDGE_BASE, list(col)[0])
      client.Flush()

      with test_lib.Instrument(transfer.MultiGetFile,
                               "Start") as getfile_instrument:
        # Run the flow in the emulated way.
        flow_test_lib.TestFlowHelper(
            registry.CollectRunKeyBinaries.__name__,
            client_mock,
            client_id=client_id,
            token=self.token)

        # Check MultiGetFile got called for our runkey file
        download_requested = False
        for pathspec in getfile_instrument.args[0][0].args.pathspecs:
          if pathspec.path == u"C:\\Windows\\TEMP\\A.exe":
            download_requested = True
        self.assertTrue(download_requested)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
