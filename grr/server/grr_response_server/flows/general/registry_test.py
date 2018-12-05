#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the registry flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import aff4_flows
from grr_response_server import artifact
from grr_response_server import data_store
from grr_response_server.flows.general import registry
from grr_response_server.flows.general import transfer
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
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


@db_test_lib.DualDBTest
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

  def testFindsNothingIfNothingMatchesTheGlob(self):
    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/NonMatch*"
    ])
    self.assertFalse(flow_test_lib.GetFlowResults(client_id, session_id))

  def testFindsKeysWithSingleGlobWithoutConditions(self):
    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/*"
    ])

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    basenames = [os.path.basename(r.stat_entry.pathspec.path) for r in results]
    self.assertCountEqual(basenames, ["Sidebar", "MctAdmin"])

  def testFindsKeysWithTwoGlobsWithoutConditions(self):
    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/Side*",
        "HKEY_USERS/S-1-5-20/Software/Microsoft/"
        "Windows/CurrentVersion/Run/Mct*"
    ])

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    basenames = [os.path.basename(r.stat_entry.pathspec.path) for r in results]
    self.assertCountEqual(basenames, ["Sidebar", "MctAdmin"])

  def testFindsKeyWithInterpolatedGlobWithoutConditions(self):
    user = rdf_client.User(sid="S-1-5-20")
    client_id = self.SetupClient(0, users=[user])

    session_id = self.RunFlow(client_id, [
        "HKEY_USERS/%%users.sid%%/Software/Microsoft/Windows/"
        "CurrentVersion/*"
    ])

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)

    key = ("/HKEY_USERS/S-1-5-20/"
           "Software/Microsoft/Windows/CurrentVersion/Run")

    self.assertEqual(results[0].stat_entry.AFF4Path(client_id),
                     "aff4:/C.1000000000000000/registry" + key)
    self.assertEqual(results[0].stat_entry.pathspec.path, key)
    self.assertEqual(results[0].stat_entry.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.REGISTRY)

  def testFindsNothingIfNothingMatchesLiteralMatchCondition(self):
    vlm = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10, bytes_after=10, literal=b"CanNotFindMe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type
            .VALUE_LITERAL_MATCH,
            value_literal_match=vlm)
    ])
    self.assertFalse(flow_test_lib.GetFlowResults(client_id, session_id))

  def testFindsKeyIfItMatchesLiteralMatchCondition(self):
    vlm = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10,
        bytes_after=10,
        literal=b"Windows Sidebar\\Sidebar.exe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type
            .VALUE_LITERAL_MATCH,
            value_literal_match=vlm)
    ])

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
    self.assertLen(results[0].matches, 1)

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
            condition_type=registry.RegistryFinderCondition.Type
            .VALUE_REGEX_MATCH,
            value_regex_match=value_regex_match)
    ])
    self.assertFalse(flow_test_lib.GetFlowResults(client_id, session_id))

  def testFindsKeyIfItMatchesRegexMatchCondition(self):
    value_regex_match = rdf_file_finder.FileFinderContentsRegexMatchCondition(
        bytes_before=10, bytes_after=10, regex="Windows.+\\.exe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type
            .VALUE_REGEX_MATCH,
            value_regex_match=value_regex_match)
    ])

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
    self.assertLen(results[0].matches, 1)

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
            condition_type=registry.RegistryFinderCondition.Type
            .MODIFICATION_TIME,
            modification_time=modification_time)
    ])
    self.assertFalse(flow_test_lib.GetFlowResults(client_id, session_id))

  def testFindsKeysIfModificationTimeConditionMatches(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 - 1),
        max_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 + 1))

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type
            .MODIFICATION_TIME,
            modification_time=modification_time)
    ])

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    basenames = [os.path.basename(r.stat_entry.pathspec.path) for r in results]
    self.assertCountEqual(basenames, ["Sidebar", "MctAdmin"])

  def testFindsKeyWithLiteralAndModificationTimeConditions(self):
    modification_time = rdf_file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 - 1),
        max_last_modified_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            1247546054 + 1))

    vlm = rdf_file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10,
        bytes_after=10,
        literal=b"Windows Sidebar\\Sidebar.exe")

    client_id = self.SetupClient(0)
    session_id = self.RunFlow(client_id, [self.runkey], [
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type
            .MODIFICATION_TIME,
            modification_time=modification_time),
        registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type
            .VALUE_LITERAL_MATCH,
            value_literal_match=vlm)
    ])

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
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
    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
    self.assertGreater(results[0].stat_entry.st_size, 50)


@db_test_lib.DualDBTest
class TestRegistryFlows(RegistryFlowTest):
  """Test the Run Key registry flows."""

  @parser_test_lib.WithAllParsers
  def testCollectRunKeyBinaries(self):
    """Read Run key from the client_fixtures to test parsing and storage."""
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

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

      kb = flow_test_lib.GetFlowResults(client_id, session_id)[0]

      if data_store.RelationalDBReadEnabled():
        client = data_store.REL_DB.ReadClientSnapshot(client_id.Basename())
        client.knowledge_base = kb
        data_store.REL_DB.WriteClientSnapshot(client)
      else:
        with aff4.FACTORY.Open(
            client_id, token=self.token, mode="rw") as client:
          client.Set(client.Schema.KNOWLEDGE_BASE, kb)

      if data_store.RelationalDBFlowsEnabled():
        flow_cls = transfer.MultiGetFile
      else:
        flow_cls = aff4_flows.MultiGetFile

      with test_lib.Instrument(flow_cls, "Start") as getfile_instrument:
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
