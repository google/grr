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

  kb_attributes = ["os", "os_major_version", "os_minor_version"]

  # TODO(user): time_zone, environ_path, and environ_temp are currently only
  # implemented for Windows, move to kb_attributes once available on other OSes.
  kb_win_attributes = [
      "time_zone", "environ_path", "environ_temp", "environ_systemroot",
      "environ_windir", "environ_programfiles", "environ_programfilesx86",
      "environ_systemdrive", "environ_allusersprofile",
      "environ_allusersappdata", "current_control_set", "code_page"
  ]

  def _CheckAttributes(self, attributes, v):
    for attribute in attributes:
      value = getattr(v, attribute)
      self.assertTrue(value is not None, "Attribute %s is None." % attribute)
      self.assertTrue(str(value), "str(%s) is empty" % attribute)

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("KnowledgeBaseInitializationFlow")
    # Set what Interrogate flow normally sets when running this flow.
    args.require_complete = False
    f = self.RunFlowAndWait("KnowledgeBaseInitializationFlow", args=args)

    results = list(f.ListResults())
    self.assertLen(results, 1)

    kb = results[0].payload

    self._CheckAttributes(self.kb_attributes, kb)
    if self.platform == test_base.EndToEndTest.Platform.WINDOWS:
      self._CheckAttributes(self.kb_win_attributes, kb)
