#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for Interrogate."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import socket


import mock

from grr_response_client.client_actions import admin
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server.flows.general import discovery
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class DiscoveryTestEventListener(events.EventListener):
  """A test listener to receive new client discoveries."""

  EVENTS = ["Discovery"]

  # For this test we just write the event as a class attribute.
  event = None

  def ProcessMessages(self, msgs=None, token=None):
    DiscoveryTestEventListener.event = msgs[0]


@db_test_lib.DualDBTest
class TestClientInterrogate(acl_test_lib.AclTestMixin,
                            notification_test_lib.NotificationTestMixin,
                            flow_test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def _OpenClient(self, client_id):
    return data_store.REL_DB.ReadClientSnapshot(client_id)

  def _CheckUsersAFF4(self, client, expected_users):
    """Check all user stores."""
    summary = client.GetSummary()
    self.assertCountEqual([x.username for x in summary.users], expected_users)

    self.assertCountEqual(client.Get(client.Schema.USERNAMES), expected_users)

    # Check kb users
    kbusers = [
        x.username for x in client.Get(client.Schema.KNOWLEDGE_BASE).users
    ]
    self.assertCountEqual(kbusers, expected_users)

  def _CheckUsersRelational(self, client, expected_users):
    self.assertCountEqual(
        [user.username for user in client.knowledge_base.users], expected_users)

  def _CheckBasicInfoAFF4(self, client, fqdn, system, install_date):
    self.assertEqual(client.Get(client.Schema.FQDN), fqdn)
    self.assertEqual(client.Get(client.Schema.SYSTEM), system)
    self.assertEqual(client.Get(client.Schema.INSTALL_DATE), install_date)

  def _CheckBasicInfoRelational(self, client, fqdn, system, install_date):
    self.assertEqual(client.knowledge_base.fqdn, fqdn)
    self.assertEqual(client.knowledge_base.os, system)
    self.assertEqual(client.install_time, install_date)

  def _CheckClientInfoAFF4(self, client):
    info = client.Get(client.Schema.CLIENT_INFO)
    self.assertEqual(info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(info.client_version,
                     int(config.CONFIG["Source.version_numeric"]))
    self.assertEqual(info.build_time, config.CONFIG["Client.build_time"])

  def _CheckClientInfoRelational(self, client):
    info = client.startup_info.client_info
    self.assertEqual(info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(info.client_version,
                     int(config.CONFIG["Source.version_numeric"]))
    self.assertEqual(info.build_time, config.CONFIG["Client.build_time"])

  def _CheckGRRConfigAFF4(self, client):
    """Check old and new client config."""
    config_info = client.Get(client.Schema.GRR_CONFIGURATION)
    self.assertEqual(config_info["Client.server_urls"],
                     ["http://localhost:8001/"])
    self.assertEqual(config_info["Client.poll_min"], 1.0)

  def _CheckGRRConfigRelational(self, client):
    config_dict = {item.key: item.value for item in client.grr_configuration}

    # Config is stored in a string map so everything gets converted.
    self.assertEqual(config_dict["Client.server_urls"],
                     str(["http://localhost:8001/"]))
    self.assertEqual(config_dict["Client.poll_min"], str(1.0))

  def _CheckClientKwIndexAFF4(self, keywords, expected_count):
    # Tests that the client index has expected_count results when
    # searched for keywords.
    index = client_index.CreateClientIndex(token=self.token)
    self.assertLen(index.LookupClients(keywords), expected_count)

  def _CheckClientKwIndexRelational(self, keywords, expected_count):
    # Tests that the client index has expected_count results when
    # searched for keywords.
    index = client_index.ClientIndex()
    self.assertLen(index.LookupClients(keywords), expected_count)

  def _CheckNotificationsCreatedAFF4(self, username, client_urn):
    notifications = self.GetUserNotifications(username)

    self.assertLen(notifications, 1)
    notification = notifications[0]
    self.assertEqual(notification.subject, client_urn)

  def _CheckNotificationsCreatedRelational(self, username, client_id):
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
    self.assertEqual(summary.interfaces[0].mac_address, "123456")

    # Check that the client summary was published to the event listener.
    self.assertEqual(DiscoveryTestEventListener.event.client_id, client_id)
    self.assertEqual(DiscoveryTestEventListener.event.interfaces[0].mac_address,
                     "123456")
    self.assertTrue(DiscoveryTestEventListener.event.timestamp)

  def _CheckNetworkInfoAFF4(self, client):
    interfaces = list(client.Get(client.Schema.INTERFACES))
    self._CheckInterfaces(interfaces)

    mac_addresses = client.Get(client.Schema.MAC_ADDRESS)
    ip_addresses = client.Get(client.Schema.HOST_IPS)
    # Mac addresses should be available as hex for searching
    self.assertIn("123456".encode("hex"), str(mac_addresses))

    # Same for IP addresses.
    self.assertIn("100.100.100.1", str(ip_addresses))

  def _CheckNetworkInfoRelational(self, client):
    self._CheckInterfaces(client.interfaces)

  def _CheckInterfaces(self, interfaces):
    self.assertEqual(interfaces[0].mac_address, "123456")
    self.assertEqual(interfaces[0].addresses[0].human_readable, "100.100.100.1")
    self.assertEqual(
        socket.inet_ntop(socket.AF_INET,
                         str(interfaces[0].addresses[0].packed_bytes)),
        "100.100.100.1")

  def _CheckVFS(self, client_urn):
    # Check that virtual directories exist for the mount points
    fd = aff4.FACTORY.Open(client_urn.Add("fs/os/mnt/data"), token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEmpty(list(fd.OpenChildren()))

    fd = aff4.FACTORY.Open(client_urn.Add("fs/tsk/dev/sda"), token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEmpty(list(fd.OpenChildren()))

    fd = aff4.FACTORY.Open(client_urn.Add("devices/dev/sda"), token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEmpty(list(fd.OpenChildren()))

  def _CheckLabelsAFF4(self, client):
    expected_labels = ["GRRLabel1", "Label2"]

    labels = [label.name for label in client.GetLabels()]
    self.assertEqual(labels, expected_labels)

  def _CheckLabelsRelational(self, client_id):
    expected_labels = ["GRRLabel1", "Label2"]

    labels = data_store.REL_DB.ReadClientLabels(client_id)
    self.assertEqual([label.name for label in labels], expected_labels)

  def _CheckLabelIndexAFF4(self, client_id, token=None):
    """Check that label indexes are updated."""
    index = client_index.CreateClientIndex(token=token)

    self.assertCountEqual(
        list(index.LookupClients(["label:Label2"])), [client_id])

  def _CheckLabelIndexRelational(self, client_id):
    """Check that label indexes are updated."""
    self.assertCountEqual(
        client_index.ClientIndex().LookupClients(["label:Label2"]), [client_id])

  def _CheckWindowsDiskInfoAFF4(self, client):
    volumes = client.Get(client.Schema.VOLUMES)
    self._CheckWindowsDiskInfo(volumes)

  def _CheckWindowsDiskInfoRelational(self, client):
    self._CheckWindowsDiskInfo(client.volumes)

  def _CheckWindowsDiskInfo(self, volumes):
    self.assertLen(volumes, 2)
    for result in volumes:
      self.assertIsInstance(result, rdf_client_fs.Volume)
      self.assertIn(result.windowsvolume.drive_letter, ["Z:", "C:"])

  def _CheckRegistryPathspecAFF4(self, client_urn):
    # This tests that we can click refresh on a key in the registry vfs subtree
    # even if we haven't downloaded any other key above it in the tree.

    fd = aff4.FACTORY.Open(
        client_urn.Add("registry").Add("HKEY_LOCAL_MACHINE").Add(
            "random/path/bla"),
        token=self.token)
    pathspec = fd.real_pathspec
    self.assertEqual(pathspec.pathtype, rdf_paths.PathSpec.PathType.REGISTRY)
    self.assertEqual(pathspec.CollapsePath(),
                     u"/HKEY_LOCAL_MACHINE/random/path/bla")

  def _CheckReleaseAFF4(self, client, desired_release, desired_version):
    # Test for correct Linux release override behaviour.
    release = str(client.Get(client.Schema.OS_RELEASE))
    version = str(client.Get(client.Schema.OS_VERSION))

    self.assertEqual(release, desired_release)
    self.assertEqual(version, desired_version)

  def _CheckReleaseRelational(self, client, desired_release, desired_version):
    release = client.knowledge_base.os_release
    version = client.os_version

    self.assertEqual(release, desired_release)
    self.assertEqual(version, desired_version)

  def _CheckClientLibrariesAFF4(self, client):
    libs = client.Get(client.Schema.LIBRARY_VERSIONS)
    self.assertTrue(libs is not None)
    libs = libs.ToDict()

    error_str = admin.GetLibraryVersions.error_str
    # Strip off the exception itself.
    error_str = error_str[:error_str.find("%s")]
    for key in admin.GetLibraryVersions.library_map:
      self.assertIn(key, libs)
      self.assertNotStartsWith(libs[key], error_str)

  def _CheckClientLibrariesRelational(self, client):
    versions = client.library_versions
    keys = [item.key for item in versions]

    self.assertCountEqual(keys, admin.GetLibraryVersions.library_map.keys())

    error_str = admin.GetLibraryVersions.error_str
    # Strip off the exception itself.
    error_str = error_str[:error_str.find("%s")]

    values = [item.value for item in versions]
    for v in values:
      self.assertNotStartsWith(v, error_str)

  def _CheckMemoryAFF4(self, client):
    self.assertTrue(client.Get(client.Schema.MEMORY_SIZE))

  def _CheckMemoryRelational(self, client):
    self.assertTrue(client.memory_size)

  def _CheckCloudMetadataAFF4(self, client):
    cloud_instance = client.Get(client.Schema.CLOUD_INSTANCE)
    self._CheckCloudMetadata(cloud_instance)

  def _CheckCloudMetadataRelational(self, client):
    cloud_instance = client.cloud_instance
    self._CheckCloudMetadata(cloud_instance)

  def _CheckCloudMetadata(self, cloud_instance):
    self.assertTrue(cloud_instance)
    self.assertEqual(cloud_instance.google.instance_id, "instance_id")
    self.assertEqual(cloud_instance.google.project_id, "project_id")
    self.assertEqual(cloud_instance.google.zone, "zone")
    self.assertEqual(cloud_instance.google.unique_id,
                     "zone/project_id/instance_id")

  def setUp(self):
    super(TestClientInterrogate, self).setUp()
    # This test checks for notifications so we can't use a system user.
    self.token.username = "discovery_test_user"
    self.CreateUser(self.token.username)

  @parser_test_lib.WithAllParsers
  def testInterrogateCloudMetadataLinux(self):
    """Check google cloud metadata on linux."""
    client_id = self.SetupClient(0, system="Linux")
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.FakeTestDataVFSHandler):
      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": [
              "LinuxWtmp", "NetgroupConfiguration", "LinuxRelease"
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

    if data_store.RelationalDBReadEnabled():
      client = self._OpenClient(client_id.Basename())
      self._CheckCloudMetadataRelational(client)
    else:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      self._CheckCloudMetadataAFF4(client)

  @parser_test_lib.WithAllParsers
  def testInterrogateCloudMetadataWindows(self):
    """Check google cloud metadata on windows."""
    client_id = self.SetupClient(0, system="Windows")
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

    if data_store.RelationalDBReadEnabled():
      client = self._OpenClient(client_id.Basename())
      self._CheckCloudMetadataRelational(client)
    else:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      self._CheckCloudMetadataAFF4(client)

  @parser_test_lib.WithAllParsers
  def testInterrogateLinuxWithWtmp(self):
    """Test the Interrogate flow."""
    client_id = self.SetupClient(0, system="Linux")

    with vfs_test_lib.FakeTestDataVFSOverrider():
      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": [
              "LinuxWtmp", "NetgroupConfiguration", "LinuxRelease"
          ],
          "Artifacts.netgroup_filter_regexes": [r"^login$"]
      }):
        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(version="14.4")

        with test_lib.SuppressLogs():
          flow_test_lib.TestFlowHelper(
              discovery.Interrogate.__name__,
              client_mock,
              token=self.token,
              client_id=client_id)

    if data_store.RelationalDBReadEnabled():
      client_id = client_id.Basename()
      client = self._OpenClient(client_id)
      self._CheckBasicInfoRelational(client, "test_node.test", "Linux",
                                     100 * 1000000)
      self._CheckClientInfoRelational(client)
      self._CheckGRRConfigRelational(client)
      self._CheckNotificationsCreatedRelational(self.token.username, client_id)
      self._CheckClientSummary(
          client_id,
          client.GetSummary(),
          "Linux",
          "14.4",
          release="Ubuntu",
          kernel="3.13.0-39-generic")
      self._CheckReleaseRelational(client, "Ubuntu", "14.4")

      # users 1,2,3 from wtmp, users yagharek, isaac from netgroup
      self._CheckUsersRelational(
          client, ["yagharek", "isaac", "user1", "user2", "user3"])
      self._CheckNetworkInfoRelational(client)
      # No VFS test when running on the relational db.
      self._CheckLabelsRelational(client_id)
      self._CheckLabelIndexRelational(client_id)
      self._CheckClientKwIndexRelational(["Linux"], 1)
      self._CheckClientKwIndexRelational(["Label2"], 1)
      self._CheckClientLibrariesRelational(client)
      self._CheckMemoryRelational(client)
    else:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      self._CheckBasicInfoAFF4(client, "test_node.test", "Linux", 100 * 1000000)
      self._CheckClientInfoAFF4(client)
      self._CheckGRRConfigAFF4(client)
      self._CheckNotificationsCreatedAFF4(self.token.username, client_id)
      self._CheckClientSummary(
          client_id,
          client.GetSummary(),
          "Linux",
          "14.4",
          release="Ubuntu",
          kernel="3.13.0-39-generic")
      self._CheckReleaseAFF4(client, "Ubuntu", "14.4")

      # users 1,2,3 from wtmp, users yagharek, isaac from netgroup
      self._CheckUsersAFF4(client,
                           ["yagharek", "isaac", "user1", "user2", "user3"])
      self._CheckNetworkInfoAFF4(client)
      self._CheckVFS(client_id)
      self._CheckLabelsAFF4(client)
      self._CheckLabelIndexAFF4(client_id, token=self.token)
      self._CheckClientKwIndexAFF4(["Linux"], 1)
      self._CheckClientKwIndexAFF4(["Label2"], 1)
      self._CheckClientLibrariesAFF4(client)
      self._CheckMemoryAFF4(client)

  @parser_test_lib.WithAllParsers
  def testInterrogateWindows(self):
    """Test the Interrogate flow."""
    client_id = self.SetupClient(0, system="Windows")

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(
            system="Windows", version="6.1.7600", kernel="6.1.7601")

        # Run the flow in the simulated way
        flow_test_lib.TestFlowHelper(
            discovery.Interrogate.__name__,
            client_mock,
            token=self.token,
            client_id=client_id)

    if data_store.RelationalDBReadEnabled():
      client_id = client_id.Basename()
      client = self._OpenClient(client_id)
      self._CheckBasicInfoRelational(client, "test_node.test", "Windows",
                                     100 * 1000000)
      self._CheckClientInfoRelational(client)
      self._CheckGRRConfigRelational(client)
      self._CheckNotificationsCreatedRelational(self.token.username, client_id)
      self._CheckClientSummary(
          client_id,
          client.GetSummary(),
          "Windows",
          "6.1.7600",
          kernel="6.1.7601")
      # jim parsed from registry profile keys
      self._CheckUsersRelational(client, ["jim", "kovacs"])
      self._CheckNetworkInfoRelational(client)
      # No VFS test for the relational db.
      self._CheckLabelsRelational(client_id)
      self._CheckLabelIndexRelational(client_id)
      self._CheckWindowsDiskInfoRelational(client)
      # No registry pathspec test for the relational db.
      self._CheckClientKwIndexRelational(["Linux"], 0)
      self._CheckClientKwIndexRelational(["Windows"], 1)
      self._CheckClientKwIndexRelational(["Label2"], 1)
      self._CheckMemoryRelational(client)
    else:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      self._CheckBasicInfoAFF4(client, "test_node.test", "Windows",
                               100 * 1000000)
      self._CheckClientInfoAFF4(client)
      self._CheckGRRConfigAFF4(client)
      self._CheckNotificationsCreatedAFF4(self.token.username, client_id)
      self._CheckClientSummary(
          client_id,
          client.GetSummary(),
          "Windows",
          "6.1.7600",
          kernel="6.1.7601")
      # jim parsed from registry profile keys
      self._CheckUsersAFF4(client, ["jim", "kovacs"])
      self._CheckNetworkInfoAFF4(client)
      self._CheckVFS(client_id)
      self._CheckLabelsAFF4(client)
      self._CheckLabelIndexAFF4(client_id, token=self.token)
      self._CheckWindowsDiskInfoAFF4(client)
      self._CheckRegistryPathspecAFF4(client_id)
      self._CheckClientKwIndexAFF4(["Linux"], 0)
      self._CheckClientKwIndexAFF4(["Windows"], 1)
      self._CheckClientKwIndexAFF4(["Label2"], 1)
      self._CheckMemoryAFF4(client)


class TestClientInterrogateRelationalFlows(db_test_lib.RelationalDBEnabledMixin,
                                           TestClientInterrogate):
  pass


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
