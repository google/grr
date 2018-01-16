#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for Interrogate."""

import platform
import socket


import mock

from grr import config
from grr.client.client_actions import admin
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import aff4
from grr.server import client_index
from grr.server import data_store
from grr.server import flow
from grr.server.flows.general import discovery
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class DiscoveryTestEventListener(flow.EventListener):
  """A test listener to receive new client discoveries."""
  well_known_session_id = rdfvalue.SessionID(flow_name="discoverytest")
  EVENTS = ["Discovery"]

  # For this test we just write the event as a class attribute.
  event = None

  @flow.EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    DiscoveryTestEventListener.event = event


class TestClientInterrogate(flow_test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def _CheckUsers(self, all_users):
    """Check all user stores."""
    summary = self.fd.GetSummary()
    self.assertItemsEqual([x.username for x in summary.users], all_users)

    self.assertItemsEqual(self.fd.Get(self.fd.Schema.USERNAMES), all_users)

    # Check kb users
    kbusers = [
        x.username for x in self.fd.Get(self.fd.Schema.KNOWLEDGE_BASE).users
    ]
    self.assertItemsEqual(kbusers, all_users)

  def _CheckAFF4Object(self, hostname, system, install_date):
    self.assertEqual(self.fd.Get(self.fd.Schema.HOSTNAME), hostname)
    self.assertEqual(self.fd.Get(self.fd.Schema.SYSTEM), system)
    self.assertEqual(self.fd.Get(self.fd.Schema.INSTALL_DATE), install_date)

  def _CheckClientInfo(self):
    info = self.fd.Get(self.fd.Schema.CLIENT_INFO)
    self.assertEqual(info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(info.client_version,
                     int(config.CONFIG["Source.version_numeric"]))
    self.assertEqual(info.build_time, config.CONFIG["Client.build_time"])

  def _CheckGRRConfig(self):
    """Check old and new client config."""
    config_info = self.fd.Get(self.fd.Schema.GRR_CONFIGURATION)
    self.assertEqual(config_info["Client.server_urls"],
                     ["http://localhost:8001/"])
    self.assertEqual(config_info["Client.poll_min"], 1.0)

  def _CheckClientKwIndex(self, keywords, expected_count):
    # Tests that the client index has expected_count results when
    # searched for keywords.

    # AFF4 index.
    index = client_index.CreateClientIndex(token=self.token)
    self.assertEqual(len(index.LookupClients(keywords)), expected_count)

    # Relational index.
    index = client_index.ClientIndex()
    self.assertEqual(len(index.LookupClients(keywords)), expected_count)

  def _CheckNotificationsCreated(self):
    user_fd = aff4.FACTORY.Open(
        "aff4:/users/%s" % self.token.username, token=self.token)
    notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)

    self.assertEqual(len(notifications), 1)
    notification = notifications[0]

    self.assertEqual(notification.subject, rdfvalue.RDFURN(self.client_id))

  def _CheckClientSummary(self,
                          osname,
                          version,
                          kernel="3.13.0-39-generic",
                          release="5"):
    summary = self.fd.GetSummary()
    self.assertEqual(summary.client_info.client_name,
                     config.CONFIG["Client.name"])
    self.assertEqual(summary.client_info.client_version,
                     int(config.CONFIG["Source.version_numeric"]))
    self.assertEqual(summary.client_info.build_time,
                     config.CONFIG["Client.build_time"])

    self.assertEqual(summary.system_info.system, osname)
    self.assertEqual(summary.system_info.node, "test_node")
    self.assertEqual(summary.system_info.release, release)
    self.assertEqual(summary.system_info.version, version)
    self.assertEqual(summary.system_info.machine, "i386")
    self.assertEqual(summary.system_info.kernel, kernel)

    self.assertEqual(len(summary.interfaces), 1)
    self.assertEqual(summary.interfaces[0].mac_address, "123456")

    # Check that the client summary was published to the event listener.
    self.assertEqual(DiscoveryTestEventListener.event.client_id, self.client_id)
    self.assertEqual(DiscoveryTestEventListener.event.interfaces[0].mac_address,
                     "123456")

  def _CheckNetworkInfo(self):
    interfaces = list(self.fd.Get(self.fd.Schema.INTERFACES))
    self.assertEqual(interfaces[0].mac_address, "123456")
    self.assertEqual(interfaces[0].addresses[0].human_readable, "100.100.100.1")
    self.assertEqual(
        socket.inet_ntop(socket.AF_INET,
                         str(interfaces[0].addresses[0].packed_bytes)),
        "100.100.100.1")

    # Mac addresses should be available as hex for searching
    mac_addresses = self.fd.Get(self.fd.Schema.MAC_ADDRESS)
    self.assertTrue("123456".encode("hex") in str(mac_addresses))

    # Same for IP addresses.
    ip_addresses = self.fd.Get(self.fd.Schema.HOST_IPS)
    self.assertTrue("100.100.100.1" in str(ip_addresses))

  def _CheckVFS(self):
    # Check that virtual directories exist for the mount points
    fd = aff4.FACTORY.Open(
        self.client_id.Add("fs/os/mnt/data"), token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

    fd = aff4.FACTORY.Open(
        self.client_id.Add("fs/tsk/dev/sda"), token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

    fd = aff4.FACTORY.Open(
        self.client_id.Add("devices/dev/sda"), token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

  def _CheckLabelIndex(self):
    """Check that label indexes are updated."""
    index = client_index.CreateClientIndex(token=self.token)

    # AFF4 index.
    self.assertEqual(
        list(index.LookupClients(["label:Label2"])), [self.client_id])

    # Relational index.
    self.assertEqual(client_index.ClientIndex().LookupClients(["label:Label2"]),
                     [self.client_id.Basename()])

  def _CheckWindowsDiskInfo(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    volumes = client.Get(client.Schema.VOLUMES)
    self.assertEqual(len(volumes), 2)
    for result in volumes:
      self.assertTrue(isinstance(result, rdf_client.Volume))
      self.assertTrue(result.windowsvolume.drive_letter in ["Z:", "C:"])

  def _CheckRegistryPathspec(self):
    # This tests that we can click refresh on a key in the registry vfs subtree
    # even if we haven't downloaded any other key above it in the tree.

    fd = aff4.FACTORY.Open(
        self.client_id.Add("registry").Add("HKEY_LOCAL_MACHINE").Add(
            "random/path/bla"),
        token=self.token)
    pathspec = fd.real_pathspec
    self.assertEqual(pathspec.pathtype, rdf_paths.PathSpec.PathType.REGISTRY)
    self.assertEqual(pathspec.CollapsePath(),
                     u"/HKEY_LOCAL_MACHINE/random/path/bla")

  def _CheckRelease(self, desired_release, desired_version):
    # Test for correct Linux release override behaviour.

    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    release = str(client.Get(client.Schema.OS_RELEASE))
    version = str(client.Get(client.Schema.OS_VERSION))

    self.assertEqual(release, desired_release)
    self.assertEqual(version, desired_version)

  def _CheckClientLibraries(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    libs = client.Get(client.Schema.LIBRARY_VERSIONS)
    self.assertTrue(libs is not None)
    libs = libs.ToDict()

    error_str = admin.GetLibraryVersions.error_str
    # Strip off the exception itself.
    error_str = error_str[:error_str.find("%s")]
    for key in admin.GetLibraryVersions.library_map:
      self.assertIn(key, libs)
      self.assertFalse(libs[key].startswith(error_str))

  def _CheckMemory(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertTrue(client.Get(client.Schema.MEMORY_SIZE))

  def _CheckCloudMetadata(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    cloud_instance = client.Get(client.Schema.CLOUD_INSTANCE)
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

  def testInterrogateCloudMetadataLinux(self):
    """Check google cloud metadata on linux."""
    self.SetupClients(1, system="Linux", os_version="12.04")
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
        for _ in flow_test_lib.TestFlowHelper(
            discovery.Interrogate.__name__,
            client_mock,
            token=self.token,
            client_id=self.client_id):
          pass

        self.fd = aff4.FACTORY.Open(self.client_id, token=self.token)
        self._CheckCloudMetadata()

  def testInterrogateCloudMetadataWindows(self):
    """Check google cloud metadata on windows."""
    self.SetupClients(1, system="Windows", os_version="6.2", arch="AMD64")
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):
        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(
            system="Windows", version="6.1.7600", kernel="6.1.7601")
        with mock.patch.object(platform, "system", return_value="Windows"):
          for _ in flow_test_lib.TestFlowHelper(
              discovery.Interrogate.__name__,
              client_mock,
              token=self.token,
              client_id=self.client_id):
            pass

        self.fd = aff4.FACTORY.Open(self.client_id, token=self.token)
        self._CheckCloudMetadata()

  def testInterrogateLinuxWithWtmp(self):
    """Test the Interrogate flow."""
    self.SetupClients(1, system="Linux", os_version="12.04")
    data_store.REL_DB.WriteClientMetadata(
        self.client_id.Basename(), fleetspeak_enabled=False)

    with vfs_test_lib.FakeTestDataVFSOverrider():
      with test_lib.ConfigOverrider({
          "Artifacts.knowledge_base": [
              "LinuxWtmp", "NetgroupConfiguration", "LinuxRelease"
          ],
          "Artifacts.netgroup_filter_regexes": [r"^login$"]
      }):
        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient()

        for _ in flow_test_lib.TestFlowHelper(
            discovery.Interrogate.__name__,
            client_mock,
            token=self.token,
            client_id=self.client_id):
          pass

        self.fd = aff4.FACTORY.Open(self.client_id, token=self.token)
        self._CheckAFF4Object("test_node", "Linux", 100 * 1000000)
        self._CheckClientInfo()
        self._CheckGRRConfig()
        self._CheckNotificationsCreated()
        self._CheckClientSummary(
            "Linux", "14.4", release="Ubuntu", kernel="3.13.0-39-generic")
        self._CheckRelease("Ubuntu", "14.4")

        # users 1,2,3 from wtmp
        # users yagharek, isaac from netgroup
        self._CheckUsers(["yagharek", "isaac", "user1", "user2", "user3"])
        self._CheckNetworkInfo()
        self._CheckVFS()
        self._CheckLabelIndex()
        self._CheckClientKwIndex(["Linux"], 1)
        self._CheckClientKwIndex(["Label2"], 1)
        self._CheckClientLibraries()
        self._CheckMemory()

  def testInterrogateWindows(self):
    """Test the Interrogate flow."""
    self.SetupClients(1, system="Windows", os_version="6.2", arch="AMD64")
    data_store.REL_DB.WriteClientMetadata(
        self.client_id.Basename(), fleetspeak_enabled=False)

    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):
      with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                     vfs_test_lib.FakeFullVFSHandler):

        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient(
            system="Windows", version="6.1.7600", kernel="6.1.7601")

        # Run the flow in the simulated way
        for _ in flow_test_lib.TestFlowHelper(
            discovery.Interrogate.__name__,
            client_mock,
            token=self.token,
            client_id=self.client_id):
          pass

        self.fd = aff4.FACTORY.Open(self.client_id, token=self.token)
        self._CheckAFF4Object("test_node", "Windows", 100 * 1000000)
        self._CheckClientInfo()
        self._CheckGRRConfig()
        self._CheckNotificationsCreated()
        self._CheckClientSummary("Windows", "6.1.7600", kernel="6.1.7601")

        # jim parsed from registry profile keys
        self._CheckUsers(["jim", "kovacs"])
        self._CheckNetworkInfo()
        self._CheckVFS()
        self._CheckLabelIndex()
        self._CheckWindowsDiskInfo()
        self._CheckRegistryPathspec()
        self._CheckClientKwIndex(["Linux"], 0)
        self._CheckClientKwIndex(["Windows"], 1)
        self._CheckClientKwIndex(["Label2"], 1)
        self._CheckMemory()


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
