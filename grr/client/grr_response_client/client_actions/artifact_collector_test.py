#!/usr/bin/env python
"""Tests the client artifactor collection."""
import os

import mock

from grr_response_client.client_actions import artifact_collector

from grr.core.grr_response_core import config
from grr.core.grr_response_core.lib import flags
from grr.core.grr_response_core.lib.rdfvalues import artifacts as rdf_artifact
from grr.core.grr_response_core.lib.rdfvalues import client as rdf_client
from grr.core.grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import artifact_test_lib
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class ArtifactCollectorTest(client_test_lib.EmptyActionTest):

  def setUp(self):
    super(ArtifactCollectorTest, self).setUp()
    self.test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                            "artifacts", "test_artifacts.json")

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testCommandArtifact(self, registry):
    """Test the basic ExecuteCommand action."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestCmdArtifact")
    ext_src = rdf_artifact.ExtendedSource(base_source=list(artifact.sources)[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=list(ext_src))
    request = rdf_artifact.ClientArtifactCollectorArgs(artifacts=list(ext_art))
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifact = list(result.collected_artifacts)[0]
    execute_response = list(collected_artifact.action_results)[0].value

    self.assertEqual(collected_artifact.name, "TestCmdArtifact")
    self.assertTrue(execute_response.time_used > 0)

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testGRRClientActionArtifact(self, registry):
    """Test the GetHostname action."""
    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestOSAgnostic")
    ext_src = rdf_artifact.ExtendedSource(base_source=list(artifact.sources)[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=list(ext_src))
    request = rdf_artifact.ClientArtifactCollectorArgs(artifacts=list(ext_art))
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifact = list(result.collected_artifacts)[0]
    hostname = list(collected_artifact.action_results)[0].value

    self.assertEqual(collected_artifact.name, "TestOSAgnostic")
    self.assertTrue(hostname.string)

  def testRegistryValueArtifact(self):
    """Test the basic Registry Value collection."""
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        source = rdf_artifact.ArtifactSource(
            type=rdf_artifact.ArtifactSource.SourceType.REGISTRY_VALUE,
            attributes={
                "key_value_pairs": [{
                    "key": (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet"
                            r"\Control\Session Manager"),
                    "value":
                        "BootExecute"
                }]
            })
        ext_src = rdf_artifact.ExtendedSource(base_source=source)
        ext_art = rdf_artifact.ExtendedArtifact(
            name="FakeRegistryValue", sources=list(ext_src))
        request = rdf_artifact.ClientArtifactCollectorArgs(
            artifacts=list(ext_art))
        result = self.RunAction(artifact_collector.ArtifactCollector,
                                request)[0]
        collected_artifact = list(result.collected_artifacts)[0]
        file_stat = list(collected_artifact.action_results)[0].value
        self.assertTrue(isinstance(file_stat, rdf_client.StatEntry))
        urn = file_stat.pathspec.AFF4Path(self.SetupClient(0))
        self.assertTrue(str(urn).endswith("BootExecute"))

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testMultipleArtifacts(self, registry):
    """Test collecting multiple artifacts."""

    client_test_lib.Command("/usr/bin/dpkg", args=["--list"], system="Linux")

    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("TestCmdArtifact")
    ext_src = rdf_artifact.ExtendedSource(base_source=list(artifact.sources)[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=list(ext_src))
    request = rdf_artifact.ClientArtifactCollectorArgs(artifacts=list(ext_art))
    request.artifacts.append(ext_art)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    collected_artifacts = list(result.collected_artifacts)
    self.assertEqual(len(collected_artifacts), 2)
    self.assertEqual(collected_artifacts[0].name, "TestCmdArtifact")
    self.assertEqual(collected_artifacts[1].name, "TestCmdArtifact")
    execute_response_1 = list(collected_artifacts[0].action_results)[0].value
    execute_response_2 = list(collected_artifacts[1].action_results)[0].value
    self.assertGreater(execute_response_1.time_used, 0)
    self.assertGreater(execute_response_2.time_used, 0)


class WindowsArtifactCollectorTests(client_test_lib.OSSpecificClientTests):

  def setUp(self):
    super(WindowsArtifactCollectorTests, self).setUp()
    self.test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                            "artifacts", "test_artifacts.json")

    modules = {
        ("grr_response_client.client_actions"
         ".windows"):
            mock.MagicMock()
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    # TODO(user): Find a way to move the import statement to the top of the
    # file.
    # pylint: disable= g-import-not-at-top
    from grr_response_client.client_actions.windows import windows
    # pylint: enable=g-import-not-at-top

    self.action = windows.WmiQuery

  def tearDown(self):
    super(WindowsArtifactCollectorTests, self).tearDown()
    self.module_patcher.stop()

  @artifact_test_lib.PatchCleanArtifactRegistry
  def testWMIArtifact(self, registry):
    registry.AddFileSource(self.test_artifacts_file)
    artifact = registry.GetArtifact("WMIActiveScriptEventConsumer")

    ext_src = rdf_artifact.ExtendedSource(base_source=artifact.sources[0])
    ext_art = rdf_artifact.ExtendedArtifact(
        name=artifact.name, sources=list(ext_src))
    request = rdf_artifact.ClientArtifactCollectorArgs(
        artifacts=list(ext_art),
        knowledge_base=None,
        ignore_interpolation_errors=True)
    result = self.RunAction(artifact_collector.ArtifactCollector, request)[0]
    self.assertIsInstance(result, rdf_artifact.ClientArtifactCollectorResult)

    coll = artifact_collector.ArtifactCollector()
    coll.knowledge_base = None
    coll.ignore_interpolation_errors = True

    expected = rdf_client.WMIRequest(
        query="SELECT * FROM ActiveScriptEventConsumer",
        base_object="winmgmts:\\root\\subscription")

    for action, request in coll._ProcessWmiSource(ext_src):
      self.assertEqual(request, expected)
      self.assertEqual(action, self.action)
      self.action.Start.assert_called_with(request)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
