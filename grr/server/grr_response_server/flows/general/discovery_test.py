#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for Interrogate."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import socket

from absl import app
import mock

from grr_response_client.client_actions import admin
from grr_response_core import config
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import fleetspeak_utils
from grr_response_server.flows.general import discovery
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class DiscoveryTestEventListener(events.EventListener):
  """A test listener to receive new client discoveries."""

  EVENTS = ["Discovery"]

  # For this test we just write the event as a class attribute.
  event = None

  def ProcessMessages(self, msgs=None, token=None):
    DiscoveryTestEventListener.event = msgs[0]


class TestClientInterrogate(acl_test_lib.AclTestMixin,
                            notification_test_lib.NotificationTestMixin,
                            flow_test_lib.FlowTestsBaseclass,
                            stats_test_lib.StatsTestMixin):
  """Test the interrogate flow."""

  def _OpenClient(self, client_id):
    return data_store.REL_DB.ReadClientSnapshot(client_id)

  def _CheckUsers(self, client, expected_users):
    self.assertCountEqual(
        [user.username for user in client.knowledge_base.users], expected_users)

  def _CheckBasicInfo(self, client, fqdn, system, install_date):
    self.assertEqual(client.knowledge_base.fqdn, fqdn)
    self.assertEqual(client.knowledge_base.os, system)
    self.assertEqual(client.install_time, install_date)

  def _CheckClientInfo(self, client):
    info = client.startup_info.client_info
    self.assertEqual(info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(info.client_version,
                     int(config.CONFIG["Source.version_numeric"]))
    self.assertEqual(info.build_time, config.CONFIG["Client.build_time"])

  def _CheckGRRConfig(self, client):
    config_dict = {item.key: item.value for item in client.grr_configuration}

    # Config is stored in a string map so everything gets converted.
    self.assertEqual(config_dict["Client.server_urls"],
                     str(["http://localhost:8001/"]))
    self.assertEqual(config_dict["Client.poll_min"], str(1.0))

  def _CheckClientKwIndex(self, keywords, expected_count):
    # Tests that the client index has expected_count results when
    # searched for keywords.
    index = client_index.ClientIndex()
    self.assertLen(index.LookupClients(keywords), expected_count)

  def _CheckNotificationsCreated(self, username, client_id):
    notifications = self.GetUserNotifications(username)

    self.assertLen(notifications, 1)
    notification = notifications[0]
    self.assertEqual(notification.reference.client.client_id, client_id)

  def _CheckClientSummary(self,
                          client_id,
                          summary,
                          osname,
                          version,
                          kernel="3.13.0-39-generic",
                          release="5"):
    self.assertEqual(summary.client_info.client_name,
                     config.CONFIG["Client.name"])
    self.assertEqual(summary.client_info.client_version,
                     int(config.CONFIG["Source.version_numeric"]))
    self.assertEqual(summary.client_info.build_time,
                     config.CONFIG["Client.build_time"])

    self.assertEqual(summary.system_info.system, osname)
    self.assertEqual(summary.system_info.fqdn, "test_node.test")
    self.assertEqual(summary.system_info.release, release)
    self.assertEqual(summary.system_info.version, version)
    self.assertEqual(summary.system_info.machine, "i386")
    self.assertEqual(summary.system_info.kernel, kernel)

    self.assertLen(summary.interfaces, 1)
    self.assertEqual(summary.interfaces[0].mac_address, b"123456")

    # Check that the client summary was published to the event listener.
    self.assertEqual(DiscoveryTestEventListener.event.client_id, client_id)
    self.assertEqual(DiscoveryTestEventListener.event.interfaces[0].mac_address,
                     b"123456")
    self.assertTrue(DiscoveryTestEventListener.event.timestamp)
    self.assertTrue(DiscoveryTestEventListener.event.last_ping)

  def _CheckNetworkInfo(self, client):
    self.assertEqual(client.interfaces[0].mac_address, b"123456")
    self.assertEqual(client.interfaces[0].addresses[0].human_readable_address,
                     "100.100.100.1")
    self.assertEqual(
        socket.inet_ntop(socket.AF_INET,
                         client.interfaces[0].addresses[0].packed_bytes),
        "100.100.100.1")

  def _CheckLabels(self, client_id):
    expected_labels = ["GRRLabel1", "Label2"]

    labels = data_store.REL_DB.ReadClientLabels(client_id)
    self.assertEqual([label.name for label in labels], expected_labels)

  def _CheckLabelIndex(self, client_id):
    """Check that label indexes are updated."""
    self.assertCountEqual(
        client_index.ClientIndex().LookupClients(["label:Label2"]), [client_id])

  def _CheckWindowsDiskInfo(self, client):
    self.assertLen(client.volumes, 2)
    for result in client.volumes:
      self.assertIsInstance(result, rdf_client_fs.Volume)
      self.assertIn(result.windowsvolume.drive_letter, ["Z:", "C:"])

  def _CheckRelease(self, client, desired_release, desired_version):
    release = client.knowledge_base.os_release
    version = client.os_version

    self.assertEqual(release, desired_release)
    self.assertEqual(version, desired_version)

  def _CheckClientLibraries(self, client):
    versions = client.library_versions
    keys = [item.key for item in versions]

    self.assertCountEqual(keys, admin.GetLibraryVersions.library_map.keys())

    error_str = admin.GetLibraryVersions.error_str
    # Strip off the exception itself.
    error_str = error_str[:error_str.find("%s")]

    values = [item.value for item in versions]
    for v in values:
      self.assertNotStartsWith(v, error_str)

  def _CheckMemory(self, client):
    self.assertTrue(client.memory_size)

  def _CheckCloudMetadata(self, client):
    self.assertTrue(client.cloud_instance)
    self.assertEqual(client.cloud_instance.google.instance_id, "instance_id")
    self.assertEqual(client.cloud_instance.google.project_id, "project_id")
    self.assertEqual(client.cloud_instance.google.zone, "zone")
    self.assertEqual(client.cloud_instance.google.unique_id,
                     "zone/project_id/instance_id")

  def setUp(self):
    super(TestClientInterrogate, self).setUp()
    # This test checks for notifications so we can't use a system user.
    self.token.username = "discovery_test_user"
    self.CreateUser(self.token.username)

  def _SetupMinimalClient(self):
    client_id = "C.0000000000000000"

    data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    return client_id

  @parser_test_lib.WithAllParsers
  def testInterrogateCloudMetadataLinux(self):
    """Check google cloud metadata on linux."""
    client_id = self._SetupMinimalClient()
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.FakeTestDataVFSHandler):
      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": [
              "LinuxWtmp", "NetgroupConfiguration", "LinuxReleaseInfo"
          ],
          "Artifacts.netgroup_filter_regexes": [r"^login$"]
      }):
        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient()
        with test_lib.SuppressLogs():
          flow_test_lib.TestFlowHelper(
              discovery.Interrogate.__name__,
              client_mock,
              token=self.token,
              client_id=client_id)

    client = self._OpenClient(client_id)
    self._CheckCloudMetadata(client)

  @parser_test_lib.WithAllParsers
  def testInterrogateCloudMetadataWindows(self):
    """Check google cloud metadata on windows."""
    client_id = self._SetupMinimalClient()
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(
            system="Windows", version="6.1.7600", kernel="6.1.7601")
        with mock.patch.object(platform, "system", return_value="Windows"):
          flow_test_lib.TestFlowHelper(
              discovery.Interrogate.__name__,
              client_mock,
              token=self.token,
              client_id=client_id)

    client = self._OpenClient(client_id)
    self._CheckCloudMetadata(client)

  @parser_test_lib.WithAllParsers
  def testInterrogateLinuxWithWtmp(self):
    """Test the Interrogate flow."""
    client_id = self._SetupMinimalClient()
    with vfs_test_lib.FakeTestDataVFSOverrider():
      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": [
              "LinuxWtmp", "NetgroupConfiguration", "LinuxReleaseInfo"
          ],
          "Artifacts.netgroup_filter_regexes": [r"^login$"]
      }):
        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(version="14.4", release="Ubuntu")

        with test_lib.SuppressLogs():
          flow_test_lib.TestFlowHelper(
              discovery.Interrogate.__name__,
              client_mock,
              token=self.token,
              client_id=client_id)

    client = self._OpenClient(client_id)
    self._CheckBasicInfo(client, "test_node.test", "Linux", 100 * 1000000)
    self._CheckClientInfo(client)
    self._CheckGRRConfig(client)
    self._CheckNotificationsCreated(self.token.username, client_id)
    self._CheckClientSummary(
        client_id,
        client.GetSummary(),
        "Linux",
        "14.4",
        release="Ubuntu",
        kernel="3.13.0-39-generic")
    self._CheckRelease(client, "Ubuntu", "14.4")

    # users 1,2,3 from wtmp, users yagharek, isaac from netgroup
    self._CheckUsers(client, ["yagharek", "isaac", "user1", "user2", "user3"])
    self._CheckNetworkInfo(client)
    # No VFS test when running on the relational db.
    self._CheckLabels(client_id)
    self._CheckLabelIndex(client_id)
    self._CheckClientKwIndex(["Linux"], 1)
    self._CheckClientKwIndex(["Label2"], 1)
    self._CheckClientLibraries(client)
    self._CheckMemory(client)

  @parser_test_lib.WithAllParsers
  def testInterrogateWindows(self):
    """Test the Interrogate flow."""
    client_id = self._SetupMinimalClient()
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(
            system="Windows", version="6.1.7600", kernel="6.1.7601")

        with test_lib.ConfigOverrider({
            "Artifacts.non_kb_interrogate_artifacts": ["WMILogicalDisks"],
        }):
          # Run the flow in the simulated way
          flow_test_lib.TestFlowHelper(
              discovery.Interrogate.__name__,
              client_mock,
              token=self.token,
              client_id=client_id)

    client = self._OpenClient(client_id)
    self._CheckBasicInfo(client, "test_node.test", "Windows", 100 * 1000000)
    self._CheckClientInfo(client)
    self._CheckGRRConfig(client)
    self._CheckNotificationsCreated(self.token.username, client_id)
    self._CheckClientSummary(
        client_id,
        client.GetSummary(),
        "Windows",
        "6.1.7600",
        kernel="6.1.7601")
    # jim parsed from registry profile keys
    self._CheckUsers(client, ["jim", "kovacs"])
    self._CheckNetworkInfo(client)
    # No VFS test for the relational db.
    self._CheckLabels(client_id)
    self._CheckLabelIndex(client_id)
    self._CheckWindowsDiskInfo(client)
    # No registry pathspec test for the relational db.
    self._CheckClientKwIndex(["Linux"], 0)
    self._CheckClientKwIndex(["Windows"], 1)
    self._CheckClientKwIndex(["Label2"], 1)
    self._CheckMemory(client)

  @parser_test_lib.WithAllParsers
  @mock.patch.object(fleetspeak_utils, "GetLabelsFromFleetspeak")
  def testFleetspeakClient(self, mock_labels_fn):
    mock_labels_fn.return_value = ["foo", "bar"]
    client_id = "C.0000000000000001"
    data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=True)
    client_mock = action_mocks.InterrogatedClient()
    client_mock.InitializeClient(
        fqdn="fleetspeak.test.com",
        system="Linux",
        release="Ubuntu",
        version="14.4")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.FakeTestDataVFSHandler):
      flow_test_lib.TestFlowHelper(
          discovery.Interrogate.__name__,
          client_mock,
          token=self.token,
          client_id=client_id)

    snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    self.assertEqual(snapshot.knowledge_base.fqdn, "fleetspeak.test.com")
    self.assertEqual(snapshot.knowledge_base.os, "Linux")
    self._CheckClientInfo(snapshot)
    self._CheckGRRConfig(snapshot)
    self._CheckNotificationsCreated(self.token.username, client_id)
    self._CheckRelease(snapshot, "Ubuntu", "14.4")
    self._CheckNetworkInfo(snapshot)
    labels = data_store.REL_DB.ReadClientLabels(client_id)
    self.assertCountEqual([l.name for l in labels], ["foo", "bar"])

  @parser_test_lib.WithAllParsers
  @mock.patch.object(fleetspeak_utils, "GetLabelsFromFleetspeak")
  def testFleetspeakClient_OnlyGRRLabels(self, mock_labels_fn):
    mock_labels_fn.return_value = []
    client_id = "C.0000000000000001"
    data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=True)
    client_mock = action_mocks.InterrogatedClient()
    client_mock.InitializeClient(
        fqdn="fleetspeak.test.com",
        system="Linux",
        release="Ubuntu",
        version="14.4")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.FakeTestDataVFSHandler):
      with self.assertStatsCounterDelta(1,
                                        discovery.FLEETSPEAK_UNLABELED_CLIENTS):

        flow_test_lib.TestFlowHelper(
            discovery.Interrogate.__name__,
            client_mock,
            token=self.token,
            client_id=client_id)

    rdf_labels = data_store.REL_DB.ReadClientLabels(client_id)
    expected_labels = [
        action_mocks.InterrogatedClient.LABEL1,
        action_mocks.InterrogatedClient.LABEL2,
    ]
    self.assertCountEqual([l.name for l in rdf_labels], expected_labels)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
