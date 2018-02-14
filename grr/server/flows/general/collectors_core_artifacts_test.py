#!/usr/bin/env python
"""Tests for grr.server.flows.general.collectors.

These tests ensure some key artifacts are working, particularly those used for
windows interrogate, which is the most complex platform for interrogate.
"""

import os


from grr import config
from grr_response_client.client_actions import standard
from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
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

  def _CheckDriveAndRoot(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")
    client_mock = action_mocks.ActionMock(standard.StatFile,
                                          standard.ListDirectory)

    for s in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WindowsEnvironmentVariableSystemDrive"],
        token=self.token,
        client_id=client_id):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(fd), 1)
    self.assertEqual(str(fd[0]), "C:")

    for s in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WindowsEnvironmentVariableSystemRoot"],
        token=self.token,
        client_id=client_id):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(fd), 1)
    # Filesystem gives WINDOWS, registry gives Windows
    self.assertTrue(str(fd[0]) in [r"C:\Windows", r"C:\WINDOWS"])

  def testSystemDriveArtifact(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

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
          client_id=client_id):
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
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return [
            rdf_protodict.Dict({
                u"IdentifyingNumber": u"2RXYYZ1",
                u"Name": u"Latitude E7440",
                u"Vendor": u"Dell Inc.",
                u"Version": u"01",
                u"Caption": u"Computer System Product"
            })
        ]

    client_mock = WMIActionMock()
    for s in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMIComputerSystemProduct"],
        token=self.token,
        client_id=client_id,
        dependencies=artifact_utils.ArtifactCollectorFlowArgs.Dependency.
        IGNORE_DEPS):
      session_id = s

    results = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(results), 1)
    hardware = results[0]
    self.assertTrue(isinstance(hardware, rdf_client.HardwareInfo))
    self.assertEqual(str(hardware.serial_number), "2RXYYZ1")
    self.assertEqual(str(hardware.system_manufacturer), "Dell Inc.")

  def testRunWMIArtifact(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return client_fixture.WMI_SAMPLE

    client_mock = WMIActionMock()
    for s in flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMILogicalDisks"],
        token=self.token,
        client_id=client_id,
        dependencies=(
            artifact_utils.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS)):
      session_id = s

    results = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(results), 2)
    for result in results:
      self.assertTrue(isinstance(result, rdf_client.Volume))
      self.assertTrue(result.windowsvolume.drive_letter in ["Z:", "C:"])
      if result.windowsvolume.drive_letter == "C:":
        self.assertAlmostEqual(result.FreeSpacePercent(), 76.142, delta=0.001)
        self.assertEqual(result.Name(), "C:")
      elif result.windowsvolume.drive_letter == "Z:":
        self.assertEqual(result.Name(), "homefileshare$")
        self.assertAlmostEqual(result.FreeSpacePercent(), 58.823, delta=0.001)

  def testWMIBaseObject(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

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
        client_id=client_id,
        dependencies=(
            artifact_utils.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS)):
      pass

    # Make sure the artifact's base_object made it into the WmiQuery call.
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(
        "WMIActiveScriptEventConsumer")
    self.assertItemsEqual(WMIActionMock.base_objects,
                          [artifact_obj.sources[0].attributes["base_object"]])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
