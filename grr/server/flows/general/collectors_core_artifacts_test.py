#!/usr/bin/env python
"""Tests for grr.server.flows.general.collectors.

These tests ensure some key artifacts are working, particularly those used for
windows interrogate, which is the most complex platform for interrogate.
"""

import os


from grr import config
from grr.client.client_actions import standard
from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import aff4
from grr.server import artifact_registry
from grr.server import artifact_utils
from grr.server import client_fixture
from grr.server import flow
# TODO(user): remove the unused import.
# pylint: disable=unused-import
from grr.server.flows.general import artifact_fallbacks
# pylint: enable=unused-import
from grr.server.flows.general import collectors
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class TestArtifactCollectorsRealArtifacts(flow_test_lib.FlowTestsBaseclass):
  """Test the collection of real artifacts."""

  def setUp(self):
    """Add test artifacts to existing registry."""
    super(TestArtifactCollectorsRealArtifacts, self).setUp()
    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)
    self.SetupClients(1, system="Windows", os_version="6.2")

  def _CheckDriveAndRoot(self):
    client_mock = action_mocks.ActionMock(standard.StatFile,
                                          standard.ListDirectory)

    for s in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WindowsEnvironmentVariableSystemDrive"],
        token=self.token,
        client_id=self.client_id):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)
    self.assertEqual(len(fd), 1)
    self.assertEqual(str(fd[0]), "C:")

    for s in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WindowsEnvironmentVariableSystemRoot"],
        token=self.token,
        client_id=self.client_id):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)
    self.assertEqual(len(fd), 1)
    # Filesystem gives WINDOWS, registry gives Windows
    self.assertTrue(str(fd[0]) in [r"C:\Windows", r"C:\WINDOWS"])

  def testSystemDriveArtifact(self):
    self.SetupClients(1, system="Windows", os_version="6.2")

    class BrokenClientMock(action_mocks.ActionMock):

      def StatFile(self, _):
        raise IOError

      def ListDirectory(self, _):
        raise IOError

    # No registry, broken filesystem, this should just raise.
    with self.assertRaises(RuntimeError):
      for _ in flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          BrokenClientMock(),
          artifact_list=["WindowsEnvironmentVariableSystemDrive"],
          token=self.token,
          client_id=self.client_id):
        pass

    # No registry, so this should use the fallback flow
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.ClientVFSHandlerFixture):
      self._CheckDriveAndRoot()

    # Registry is present, so this should use the regular artifact collection
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      self._CheckDriveAndRoot()

  def testRunWMIComputerSystemProductArtifact(self):

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return client_fixture.WMI_CMP_SYS_PRD

    client_mock = WMIActionMock()
    for _ in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMIComputerSystemProduct"],
        token=self.token,
        client_id=self.client_id,
        dependencies=artifact_utils.ArtifactCollectorFlowArgs.Dependency.
        IGNORE_DEPS,
        store_results_in_aff4=True):
      pass

    client = aff4.FACTORY.Open(
        self.client_id,
        token=self.token,)
    hardware = client.Get(client.Schema.HARDWARE_INFO)
    self.assertTrue(isinstance(hardware, rdf_client.HardwareInfo))
    self.assertEqual(str(hardware.serial_number), "2RXYYZ1")
    self.assertEqual(str(hardware.system_manufacturer), "Dell Inc.")

  def testRunWMIArtifact(self):

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return client_fixture.WMI_SAMPLE

    client_mock = WMIActionMock()
    for _ in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMILogicalDisks"],
        token=self.token,
        client_id=self.client_id,
        dependencies=(
            artifact_utils.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS),
        store_results_in_aff4=True):
      pass

    # Test that we set the client VOLUMES attribute
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    volumes = client.Get(client.Schema.VOLUMES)
    self.assertEqual(len(volumes), 2)
    for result in volumes:
      self.assertTrue(isinstance(result, rdf_client.Volume))
      self.assertTrue(result.windowsvolume.drive_letter in ["Z:", "C:"])
      if result.windowsvolume.drive_letter == "C:":
        self.assertAlmostEqual(result.FreeSpacePercent(), 76.142, delta=0.001)
        self.assertEqual(result.Name(), "C:")
      elif result.windowsvolume.drive_letter == "Z:":
        self.assertEqual(result.Name(), "homefileshare$")
        self.assertAlmostEqual(result.FreeSpacePercent(), 58.823, delta=0.001)

  def testWMIBaseObject(self):

    class WMIActionMock(action_mocks.ActionMock):

      base_objects = []

      def WmiQuery(self, args):
        self.base_objects.append(args.base_object)
        return client_fixture.WMI_SAMPLE

    client_mock = WMIActionMock()
    for _ in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMIActiveScriptEventConsumer"],
        token=self.token,
        client_id=self.client_id,
        dependencies=(
            artifact_utils.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS)):
      pass

    # Make sure the artifact's base_object made it into the WmiQuery call.
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(
        "WMIActiveScriptEventConsumer")
    self.assertItemsEqual(WMIActionMock.base_objects,
                          [artifact_obj.sources[0].attributes["base_object"]])

  def testRetrieveDependencies(self):
    """Test getting an artifact without a KB using retrieve_depdendencies."""
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.ActionMock(standard.StatFile)

        artifact_list = ["WindowsEnvironmentVariableWinDir"]
        for s in flow_test_lib.TestFlowHelper(
            collectors.ArtifactCollectorFlow.__name__,
            client_mock,
            artifact_list=artifact_list,
            token=self.token,
            client_id=self.client_id,
            dependencies=(
                artifact_utils.ArtifactCollectorFlowArgs.Dependency.FETCH_NOW)):
          session_id = s

        output = flow.GRRFlow.ResultCollectionForFID(
            session_id, token=self.token)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0], r"C:\Windows")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
