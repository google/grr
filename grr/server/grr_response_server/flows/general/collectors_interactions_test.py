#!/usr/bin/env python
"""Tests for grr.server.grr_response_server.flows.general.collectors.

These tests cover the interaction of artifacts. They test that collection of
good artifacts can still succeed if some bad artifacts are defined, and the
various ways of loading artifacts.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import transfer
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class TestArtifactCollectorsInteractions(flow_test_lib.FlowTestsBaseclass):
  """Test the collection of artifacts.

  This class loads both real and test artifacts to test the interaction of badly
  defined artifacts with real artifacts.
  """

  def setUp(self):
    super(TestArtifactCollectorsInteractions, self).setUp()

    self._patcher = artifact_test_lib.PatchDefaultArtifactRegistry()
    self._patcher.start()

    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

  def tearDown(self):
    self._patcher.stop()
    super(TestArtifactCollectorsInteractions, self).tearDown()

  def testNewArtifactLoaded(self):
    """Simulate a new artifact being loaded into the store via the UI."""
    cmd_artifact = """name: "TestCmdArtifact"
doc: "Test command artifact for dpkg."
sources:
- type: "COMMAND"
  attributes:
    cmd: "/usr/bin/dpkg"
    args: ["--list"]
labels: [ "Software" ]
supported_os: [ "Linux" ]
"""
    no_datastore_artifact = """name: "NotInDatastore"
doc: "Test command artifact for dpkg."
sources:
- type: "COMMAND"
  attributes:
    cmd: "/usr/bin/dpkg"
    args: ["--list"]
labels: [ "Software" ]
supported_os: [ "Linux" ]
"""
    test_registry = artifact_registry.ArtifactRegistry()
    test_registry.ClearRegistry()
    test_registry.AddDatastoreSource(rdfvalue.RDFURN("aff4:/artifact_store"))
    test_registry._dirty = False
    with utils.Stubber(artifact_registry, "REGISTRY", test_registry):
      with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
        artifact_registry.REGISTRY.GetArtifact("TestCmdArtifact")

      with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
        artifact_registry.REGISTRY.GetArtifact("NotInDatastore")

      # Add artifact to datastore but not registry
      artifact_coll = artifact_registry.ArtifactCollection(
          rdfvalue.RDFURN("aff4:/artifact_store"))
      with data_store.DB.GetMutationPool() as pool:
        for artifact_val in artifact_registry.REGISTRY.ArtifactsFromYaml(
            cmd_artifact):
          artifact_coll.Add(artifact_val, mutation_pool=pool)

      # Add artifact to registry but not datastore
      for artifact_val in artifact_registry.REGISTRY.ArtifactsFromYaml(
          no_datastore_artifact):
        artifact_registry.REGISTRY.RegisterArtifact(
            artifact_val, source="datastore", overwrite_if_exists=False)

      # We need to reload all artifacts from the data store before trying to get
      # the artifact.
      artifact_registry.REGISTRY.ReloadDatastoreArtifacts()
      self.assertTrue(artifact_registry.REGISTRY.GetArtifact("TestCmdArtifact"))

      # We registered this artifact with datastore source but didn't
      # write it into aff4. This simulates an artifact that was
      # uploaded in the UI then later deleted. We expect it to get
      # cleared when the artifacts are reloaded from the datastore.
      with self.assertRaises(rdf_artifacts.ArtifactNotRegisteredError):
        artifact_registry.REGISTRY.GetArtifact("NotInDatastore")

  @parser_test_lib.WithAllParsers
  def testProcessCollectedArtifacts(self):
    """Test downloading files from artifacts."""
    self.client_id = self.SetupClient(0, system="Windows", os_version="6.2")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        self._testProcessCollectedArtifacts()

  def _testProcessCollectedArtifacts(self):
    client_mock = action_mocks.FileFinderClientMock()

    # Get KB initialized
    session_id = flow_test_lib.TestFlowHelper(
        artifact.KnowledgeBaseInitializationFlow.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token)

    col = flow.GRRFlow.ResultCollectionForFID(session_id)
    with aff4.FACTORY.Open(
        self.client_id, mode="rw", token=self.token) as client:
      client.Set(client.Schema.KNOWLEDGE_BASE, list(col)[0])

    artifact_list = ["WindowsPersistenceMechanismFiles"]
    with test_lib.Instrument(transfer.MultiGetFileMixin,
                             "Start") as getfile_instrument:
      flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=artifact_list,
          token=self.token,
          client_id=self.client_id,
          split_output_by_artifact=True)

      # Check MultiGetFile got called for our runkey files
      # TODO(user): RunKeys for S-1-5-20 are not found because users.sid only
      # expands to users with profiles.
      pathspecs = getfile_instrument.args[0][0].args.pathspecs
      self.assertCountEqual([x.path for x in pathspecs],
                            [u"C:\\Windows\\TEMP\\A.exe"])

    artifact_list = ["BadPathspecArtifact"]
    with test_lib.Instrument(transfer.MultiGetFileMixin,
                             "Start") as getfile_instrument:
      flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          client_mock,
          artifact_list=artifact_list,
          token=self.token,
          client_id=self.client_id,
          split_output_by_artifact=True)

      self.assertFalse(getfile_instrument.args)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
