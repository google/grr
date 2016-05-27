#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the registry flows."""

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import collects
from grr.lib.flows.general import file_finder
# pylint: disable=unused-import
from grr.lib.flows.general import registry
# pylint: enable=unused-import
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class RegistryFlowTest(test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(RegistryFlowTest, self).setUp()
    self.vfs_overrider = test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY, test_lib.FakeRegistryVFSHandler)
    self.vfs_overrider.Start()

  def tearDown(self):
    super(RegistryFlowTest, self).tearDown()
    self.vfs_overrider.Stop()


class TestRegistryFinderFlow(RegistryFlowTest):
  """Tests for the RegistryFinder flow."""

  def setUp(self):
    super(TestRegistryFinderFlow, self).setUp()

    self.output_path = "analysis/file_finder"
    self.client_mock = action_mocks.ActionMock("Find", "TransferBuffer",
                                               "HashBuffer", "FingerprintFile",
                                               "FingerprintFile", "Grep",
                                               "StatFile")

  def RunFlow(self, keys_paths=None, conditions=None):
    if keys_paths is None:
      keys_paths = ["HKEY_USERS/S-1-5-20/Software/Microsoft/"
                    "Windows/CurrentVersion/Run/*"]
    if conditions is None:
      conditions = []

    for _ in test_lib.TestFlowHelper("RegistryFinder",
                                     self.client_mock,
                                     client_id=self.client_id,
                                     keys_paths=keys_paths,
                                     conditions=conditions,
                                     token=self.token,
                                     output=self.output_path):
      pass

  def AssertNoResults(self):
    self.assertRaises(aff4.InstantiationError,
                      aff4.FACTORY.Open,
                      self.client_id.Add(self.output_path),
                      aff4_type=collects.RDFValueCollection,
                      token=self.token)

  def GetResults(self):
    fd = aff4.FACTORY.Open(
        self.client_id.Add(self.output_path),
        aff4_type=collects.RDFValueCollection,
        token=self.token)
    return list(fd)

  def testFindsNothingIfNothingMatchesTheGlob(self):
    self.RunFlow(["HKEY_USERS/S-1-5-20/Software/Microsoft/"
                  "Windows/CurrentVersion/Run/NonMatch*"])
    self.AssertNoResults()

  def testFindsKeysWithSingleGlobWithoutConditions(self):
    self.RunFlow(["HKEY_USERS/S-1-5-20/Software/Microsoft/"
                  "Windows/CurrentVersion/Run/*"])

    results = self.GetResults()
    self.assertEqual(len(results), 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    self.assertTrue([r for r in results
                     if r.stat_entry.aff4path.Basename() == "Sidebar"])
    self.assertTrue([r for r in results
                     if r.stat_entry.aff4path.Basename() == "MctAdmin"])

  def testFindsKeysWithTwoGlobsWithoutConditions(self):
    self.RunFlow(["HKEY_USERS/S-1-5-20/Software/Microsoft/"
                  "Windows/CurrentVersion/Run/Side*",
                  "HKEY_USERS/S-1-5-20/Software/Microsoft/"
                  "Windows/CurrentVersion/Run/Mct*"])

    results = self.GetResults()
    self.assertEqual(len(results), 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    self.assertTrue([r for r in results
                     if r.stat_entry.aff4path.Basename() == "Sidebar"])
    self.assertTrue([r for r in results
                     if r.stat_entry.aff4path.Basename() == "MctAdmin"])

  def testFindsKeyWithInterpolatedGlobWithoutConditions(self):
    # Initialize client's knowledge base in order for the interpolation
    # to work.
    user = rdf_client.User(sid="S-1-5-21-2911950750-476812067-1487428992-1001")
    kb = rdf_client.KnowledgeBase(users=[user])

    with aff4.FACTORY.Open(self.client_id,
                           mode="rw",
                           token=self.token) as client:
      client.Set(client.Schema.KNOWLEDGE_BASE, kb)

    self.RunFlow(["HKEY_USERS/%%users.sid%%/Software/Microsoft/Windows/"
                  "CurrentVersion/*"])

    results = self.GetResults()
    self.assertEqual(len(results), 1)

    key = ("/HKEY_USERS/S-1-5-21-2911950750-476812067-1487428992-1001/"
           "Software/Microsoft/Windows/CurrentVersion/Explorer")

    self.assertEqual(results[0].stat_entry.aff4path,
                     "aff4:/C.1000000000000000/registry" + key)
    self.assertEqual(results[0].stat_entry.pathspec.path, key)
    self.assertEqual(results[0].stat_entry.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.REGISTRY)

  def testFindsNothingIfNothingMatchesLiteralMatchCondition(self):
    value_literal_match = file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10, bytes_after=10,
        literal="CanNotFindMe")

    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_LITERAL_MATCH,
            value_literal_match=value_literal_match)])
    self.AssertNoResults()

  def testFindsKeyIfItMatchesLiteralMatchCondition(self):
    value_literal_match = file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10,
        bytes_after=10,
        literal="Windows Sidebar\\Sidebar.exe")

    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_LITERAL_MATCH,
            value_literal_match=value_literal_match)])

    results = self.GetResults()
    self.assertEqual(len(results), 1)
    self.assertEqual(len(results[0].matches), 1)

    self.assertEqual(results[0].matches[0].offset, 15)
    self.assertEqual(results[0].matches[0].data,
                     "ramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun")

    self.assertEqual(results[0].stat_entry.aff4path,
                     "aff4:/C.1000000000000000/registry/HKEY_USERS/S-1-5-20/"
                     "Software/Microsoft/Windows/CurrentVersion/Run/Sidebar")
    self.assertEqual(results[0].stat_entry.pathspec.path,
                     "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                     "CurrentVersion/Run/Sidebar")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.REGISTRY)

  def testFindsNothingIfRegexMatchesNothing(self):
    value_regex_match = file_finder.FileFinderContentsRegexMatchCondition(
        bytes_before=10,
        bytes_after=10,
        regex=".*CanNotFindMe.*")

    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_REGEX_MATCH,
            value_regex_match=value_regex_match)])
    self.AssertNoResults()

  def testFindsKeyIfItMatchesRegexMatchCondition(self):
    value_regex_match = file_finder.FileFinderContentsRegexMatchCondition(
        bytes_before=10,
        bytes_after=10, regex="Windows.+\\.exe")

    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            VALUE_REGEX_MATCH,
            value_regex_match=value_regex_match)])

    results = self.GetResults()
    self.assertEqual(len(results), 1)
    self.assertEqual(len(results[0].matches), 1)

    self.assertEqual(results[0].matches[0].offset, 15)
    self.assertEqual(results[0].matches[0].data,
                     "ramFiles%\\Windows Sidebar\\Sidebar.exe /autoRun")

    self.assertEqual(results[0].stat_entry.aff4path,
                     "aff4:/C.1000000000000000/registry/HKEY_USERS/S-1-5-20/"
                     "Software/Microsoft/Windows/CurrentVersion/Run/Sidebar")
    self.assertEqual(results[0].stat_entry.pathspec.path,
                     "/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
                     "CurrentVersion/Run/Sidebar")
    self.assertEqual(results[0].stat_entry.pathspec.pathtype,
                     rdf_paths.PathSpec.PathType.REGISTRY)

  def testFindsNothingIfModiciationTimeConditionMatchesNothing(self):
    modification_time = file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        max_last_modified_time=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))

    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            MODIFICATION_TIME,
            modification_time=modification_time)])
    self.AssertNoResults()

  def testFindsKeysIfModificationTimeConditionMatches(self):
    modification_time = file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime().FromSecondsFromEpoch(
            1247546054 - 1),
        max_last_modified_time=rdfvalue.RDFDatetime().FromSecondsFromEpoch(
            1247546054 + 1))

    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            MODIFICATION_TIME,
            modification_time=modification_time)])

    results = self.GetResults()
    self.assertEqual(len(results), 2)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    self.assertTrue([r for r in results
                     if r.stat_entry.aff4path.Basename() == "Sidebar"])
    self.assertTrue([r for r in results
                     if r.stat_entry.aff4path.Basename() == "MctAdmin"])

  def testFindsKeyWithLiteralAndModificationTimeConditions(self):
    modification_time = file_finder.FileFinderModificationTimeCondition(
        min_last_modified_time=rdfvalue.RDFDatetime().FromSecondsFromEpoch(
            1247546054 - 1),
        max_last_modified_time=rdfvalue.RDFDatetime().FromSecondsFromEpoch(
            1247546054 + 1))

    value_literal_match = file_finder.FileFinderContentsLiteralMatchCondition(
        bytes_before=10,
        bytes_after=10,
        literal="Windows Sidebar\\Sidebar.exe")

    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.
            MODIFICATION_TIME,
            modification_time=modification_time),
         registry.RegistryFinderCondition(
             condition_type=registry.RegistryFinderCondition.Type.
             VALUE_LITERAL_MATCH,
             value_literal_match=value_literal_match)])

    results = self.GetResults()
    self.assertEqual(len(results), 1)
    # We expect Sidebar and MctAdmin keys here (see
    # test_data/client_fixture.py).
    self.assertEqual(results[0].stat_entry.aff4path,
                     "aff4:/C.1000000000000000/registry/HKEY_USERS/S-1-5-20/"
                     "Software/Microsoft/Windows/CurrentVersion/Run/Sidebar")

  def testSizeCondition(self):
    # There are two values, one is 20 bytes, the other 53.
    self.RunFlow(
        ["HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/CurrentVersion/Run/*"],
        [registry.RegistryFinderCondition(
            condition_type=registry.RegistryFinderCondition.Type.SIZE,
            size=file_finder.FileFinderSizeCondition(min_file_size=50))])
    results = self.GetResults()
    self.assertEqual(len(results), 1)
    self.assertGreater(results[0].stat_entry.st_size, 50)


class TestRegistryFlows(RegistryFlowTest):
  """Test the Run Key and MRU registry flows."""

  def testRegistryMRU(self):
    """Test that the MRU discovery flow. Flow is a work in Progress."""
    # Mock out the Find client action.
    client_mock = action_mocks.ActionMock("Find")

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
    kb.users.Append(rdf_client.User(username="testing",
                                    userdomain="testing-PC",
                                    homedir=r"C:\Users\testing",
                                    sid="S-1-5-21-2911950750-476812067-"
                                    "1487428992-1001"))
    fd.Set(kb)
    fd.Close()

    # Run the flow in the emulated way.
    for _ in test_lib.TestFlowHelper("GetMRU",
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    # Check that the key was read.
    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add(
            "registry/HKEY_USERS/S-1-5-21-2911950750-476812067-1487428992-1001/"
            "Software/Microsoft/Windows/CurrentVersion/Explorer/"
            "ComDlg32/OpenSavePidlMRU/dd/0"),
        token=self.token)

    self.assertEqual(fd.__class__.__name__, "VFSFile")
    s = fd.Get(fd.Schema.STAT)
    # TODO(user): Make this test better when the MRU flow is complete.
    self.assertTrue(s.registry_data)

  def testCollectRunKeyBinaries(self):
    """Read Run key from the client_fixtures to test parsing and storage."""
    test_lib.ClientFixture(self.client_id, token=self.token)

    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()

    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                               test_lib.FakeFullVFSHandler):

      client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                            "Find", "HashBuffer",
                                            "FingerprintFile", "ListDirectory")

      # Get KB initialized
      for _ in test_lib.TestFlowHelper("KnowledgeBaseInitializationFlow",
                                       client_mock,
                                       client_id=self.client_id,
                                       token=self.token):
        pass

      with test_lib.Instrument(transfer.MultiGetFile,
                               "Start") as getfile_instrument:
        # Run the flow in the emulated way.
        for _ in test_lib.TestFlowHelper("CollectRunKeyBinaries",
                                         client_mock,
                                         client_id=self.client_id,
                                         token=self.token):
          pass

        # Check MultiGetFile got called for our runkey file
        download_requested = False
        for pathspec in getfile_instrument.args[0][0].args.pathspecs:
          if pathspec.path == u"C:\\Windows\\TEMP\\A.exe":
            download_requested = True
        self.assertTrue(download_requested)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
