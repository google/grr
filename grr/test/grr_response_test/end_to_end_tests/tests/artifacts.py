#!/usr/bin/env python
"""End to end tests for GRR artifacts."""

from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_test.end_to_end_tests import test_base


class TestRawFilesystemAccessUsesNtfsOnWindows(test_base.EndToEndTest):
  """Tests that use_raw_filesystem_access maps to NTFS on Windows OSes."""

  platforms = [
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ArtifactCollectorFlow")
    args.use_raw_filesystem_access = True
    args.artifact_list.append("WindowsEventLogApplication")
    args.artifact_list.append("WindowsEventLogSecurity")
    args.artifact_list.append("WindowsEventLogSystem")
    args.artifact_list.append("WindowsXMLEventLogApplication")
    args.artifact_list.append("WindowsXMLEventLogSecurity")
    args.artifact_list.append("WindowsXMLEventLogSystem")
    f = self.RunFlowAndWait("ArtifactCollectorFlow", args=args)

    results = list(f.ListResults())
    self.assertEqual(results[0].payload.pathspec.nested_path.pathtype,
                     rdf_paths.PathSpec.PathType.NTFS)


class TestRawFilesystemAccessUsesTskOnNonWindows(test_base.EndToEndTest):
  """Tests that use_raw_filesystem_access maps to TSK on non-Windows OSes."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
  ]

  def runTest(self):
    if self.os_release == "CentOS Linux":
      self.skipTest(
          "TSK is not supported on CentOS due to an xfs root filesystem.")

    args = self.grr_api.types.CreateFlowArgs("ArtifactCollectorFlow")
    args.use_raw_filesystem_access = True
    args.artifact_list.append("LinuxWtmp")
    f = self.RunFlowAndWait("ArtifactCollectorFlow", args=args)

    results = list(f.ListResults())
    self.assertEqual(results[0].payload.pathspec.nested_path.pathtype,
                     rdf_paths.PathSpec.PathType.TSK)


class TestParserDependency(test_base.EndToEndTest):
  """Test artifact collectors completes when artifact has dependencies."""

  platforms = [
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def _CollectArtifact(self, artifact_name):
    args = self.grr_api.types.CreateFlowArgs("ArtifactCollectorFlow")
    args.artifact_list.append(artifact_name)
    f = self.RunFlowAndWait("ArtifactCollectorFlow", args=args)
    return list(f.ListResults())

  def testWinEnvVariablePath(self):
    self._CollectArtifact("WindowsEnvironmentVariablePath")

  def testWinEnvVariableWinDir(self):
    self._CollectArtifact("WindowsEnvironmentVariableWinDir")

  def testWinUserShellFolder(self):
    # TODO - Re-enable once the artifact definition is fixed.
    #
    # Under RRG this test returns no results and does rightfully so as the
    # artifact definition is not correct. Once the artifact [fix][1] is merged
    # and the dependency is updated to the patched version, we can re-enable
    # this. More details on why the artifact definition is not correct are in
    # the pull request description.
    #
    # [1]: https://github.com/ForensicArtifacts/artifacts/pull/663
    self.skipTest("Invalid artifact definition")

    results = self._CollectArtifact("WindowsUserShellFolders")
    self.assertNotEmpty(results)


class TestWindowsRegistryCollector(test_base.EndToEndTest):
  """Test windows-registry based artifact."""

  platforms = [
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ArtifactCollectorFlow")
    args.artifact_list.append("WindowsExplorerNamespaceMyComputer")
    f = self.RunFlowAndWait("ArtifactCollectorFlow", args=args)

    for statentry in [r.payload for r in f.ListResults()]:
      self.assertTrue(statentry.HasField("pathspec"))
      self.assertIn("namespace", statentry.pathspec.path.lower())


class TestKnowledgeBaseInitializationFlow(test_base.EndToEndTest):
  """Test knowledge base initialization flow."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("KnowledgeBaseInitializationFlow")
    # Set what Interrogate flow normally sets when running this flow.
    args.require_complete = False
    f = self.RunFlowAndWait("KnowledgeBaseInitializationFlow", args=args)

    results = list(f.ListResults())
    self.assertLen(results, 1)

    kb = results[0].payload

    self.assertNotEmpty(kb.os)

    if self.platform == test_base.EndToEndTest.Platform.LINUX:
      # `os_major_version` and `os_minor_version` are currently only filled for
      # Linux.
      #
      # We are fine with versions like 14.0 and 0.23, so we do not assert on
      # individual parts but their sum should be non-zero (as 0.0 does not seem
      # like a legit system version).
      self.assertGreater(kb.os_major_version + kb.os_minor_version, 0)

    if self.platform == test_base.EndToEndTest.Platform.WINDOWS:
      # TODO - `time_zone`, `environ_path`, and `environ_temp` are
      # currently only implemented for Windows, move to common assertions once
      # available on other OSes.
      self.assertNotEmpty(kb.environ_path)
      self.assertNotEmpty(kb.environ_temp)
      self.assertNotEmpty(kb.environ_systemroot)
      self.assertNotEmpty(kb.environ_windir)
      self.assertNotEmpty(kb.code_page)
      self.assertNotEmpty(kb.current_control_set)
      self.assertNotEmpty(kb.environ_programfiles)
      self.assertNotEmpty(kb.environ_programfilesx86)
      self.assertNotEmpty(kb.environ_systemdrive)
      self.assertNotEmpty(kb.environ_allusersprofile)
      self.assertNotEmpty(kb.environ_allusersappdata)
      self.assertNotEmpty(kb.time_zone)
