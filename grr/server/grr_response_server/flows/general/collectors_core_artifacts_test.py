#!/usr/bin/env python
"""Tests for grr.server.flows.general.collectors.

These tests ensure some key artifacts are working, particularly those used for
windows interrogate, which is the most complex platform for interrogate.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os


from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.parsers import windows_registry_parser
from grr_response_core.lib.parsers import wmi_parser
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import artifact_registry
from grr_response_server import client_fixture
from grr_response_server.flows.general import collectors
from grr.test_lib import action_mocks
from grr.test_lib import artifact_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


@db_test_lib.DualDBTest
class TestArtifactCollectorsRealArtifacts(flow_test_lib.FlowTestsBaseclass):
  """Test the collection of real artifacts."""

  def setUp(self):
    """Add test artifacts to existing registry."""
    super(TestArtifactCollectorsRealArtifacts, self).setUp()

    self._patcher = artifact_test_lib.PatchDefaultArtifactRegistry()
    self._patcher.start()

    test_artifacts_file = os.path.join(config.CONFIG["Test.data_dir"],
                                       "artifacts", "test_artifacts.json")
    artifact_registry.REGISTRY.AddFileSource(test_artifacts_file)

  def tearDown(self):
    self._patcher.stop()
    super(TestArtifactCollectorsRealArtifacts, self).tearDown()

  def _CheckDriveAndRoot(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")
    client_mock = action_mocks.ActionMock(standard.GetFileStat,
                                          standard.ListDirectory)

    session_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WindowsEnvironmentVariableSystemDrive"],
        token=self.token,
        client_id=client_id)

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
    self.assertEqual(str(results[0]), "C:")

    session_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WindowsEnvironmentVariableSystemRoot"],
        token=self.token,
        client_id=client_id)

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
    # Filesystem gives WINDOWS, registry gives Windows
    self.assertIn(str(results[0]), [r"C:\Windows", r"C:\WINDOWS"])

  @parser_test_lib.WithParser("WinSystemDrive",
                              windows_registry_parser.WinSystemDriveParser)
  @parser_test_lib.WithParser("WinSystemRoot",
                              windows_registry_parser.WinSystemRootParser)
  def testSystemDriveArtifact(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

    class BrokenClientMock(action_mocks.ActionMock):

      def StatFile(self, _):
        raise IOError

      def ListDirectory(self, _):
        raise IOError

    # No registry, broken filesystem, this should just raise.
    with self.assertRaises(RuntimeError):
      with test_lib.SuppressLogs():
        flow_test_lib.TestFlowHelper(
            collectors.ArtifactCollectorFlow.__name__,
            BrokenClientMock(),
            artifact_list=["WindowsEnvironmentVariableSystemDrive"],
            token=self.token,
            client_id=client_id)

    # No registry, so this should use the fallback flow
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.ClientVFSHandlerFixture):
      self._CheckDriveAndRoot()

    # Registry is present, so this should use the regular artifact collection
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      self._CheckDriveAndRoot()

  @parser_test_lib.WithParser("WmiComputerSystemProduct",
                              wmi_parser.WMIComputerSystemProductParser)
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
    session_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMIComputerSystemProduct"],
        token=self.token,
        client_id=client_id,
        dependencies=(
            rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS))

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 1)
    hardware = results[0]
    self.assertIsInstance(hardware, rdf_client.HardwareInfo)
    self.assertEqual(str(hardware.serial_number), "2RXYYZ1")
    self.assertEqual(str(hardware.system_manufacturer), "Dell Inc.")

  @parser_test_lib.WithParser("WmiLogicalDisks",
                              wmi_parser.WMILogicalDisksParser)
  def testRunWMIArtifact(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

    class WMIActionMock(action_mocks.ActionMock):

      def WmiQuery(self, _):
        return client_fixture.WMI_SAMPLE

    client_mock = WMIActionMock()
    session_id = flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMILogicalDisks"],
        token=self.token,
        client_id=client_id,
        dependencies=(
            rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS))

    results = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(results, 2)
    for result in results:
      self.assertIsInstance(result, rdf_client_fs.Volume)
      self.assertIn(result.windowsvolume.drive_letter, ["Z:", "C:"])
      if result.windowsvolume.drive_letter == "C:":
        self.assertAlmostEqual(result.FreeSpacePercent(), 76.142, delta=0.001)
        self.assertEqual(result.Name(), "C:")
      elif result.windowsvolume.drive_letter == "Z:":
        self.assertEqual(result.Name(), "homefileshare$")
        self.assertAlmostEqual(result.FreeSpacePercent(), 58.823, delta=0.001)

  @parser_test_lib.WithParser("WmiActiveScriptEventConsumer",
                              wmi_parser.WMIActiveScriptEventConsumerParser)
  def testWMIBaseObject(self):
    client_id = self.SetupClient(0, system="Windows", os_version="6.2")

    class WMIActionMock(action_mocks.ActionMock):

      base_objects = []

      def WmiQuery(self, args):
        self.base_objects.append(args.base_object)
        return client_fixture.WMI_SAMPLE

    client_mock = WMIActionMock()
    flow_test_lib.TestFlowHelper(
        collectors.ArtifactCollectorFlow.__name__,
        client_mock,
        artifact_list=["WMIActiveScriptEventConsumer"],
        token=self.token,
        client_id=client_id,
        dependencies=(
            rdf_artifacts.ArtifactCollectorFlowArgs.Dependency.IGNORE_DEPS))

    # Make sure the artifact's base_object made it into the WmiQuery call.
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(
        "WMIActiveScriptEventConsumer")
    self.assertCountEqual(WMIActionMock.base_objects,
                          [artifact_obj.sources[0].attributes["base_object"]])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
