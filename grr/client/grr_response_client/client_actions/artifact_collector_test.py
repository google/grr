#!/usr/bin/env python
"""Tests the client artifactor collection."""
import os

from grr import config

from grr_response_client.client_actions import artifact_collector
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
    execute_response = list(
        list(collected_artifact.action_responses)[0].execute_response)[0]

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
    hostname = list(list(collected_artifact.action_responses)[0].hostname)[0]

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
        file_stat = list(
            list(collected_artifact.action_responses)[0].file_stat)[0]
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
    execute_response_1 = list(
        list(collected_artifacts[0].action_responses)[0].execute_response)[0]
    execute_response_2 = list(
        list(collected_artifacts[1].action_responses)[0].execute_response)[0]
    self.assertTrue(execute_response_1.time_used > 0)
    self.assertTrue(execute_response_2.time_used > 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
