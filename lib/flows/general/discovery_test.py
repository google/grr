#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for Interrogate."""

import socket

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import artifact_test
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import search
from grr.lib import test_lib


class DiscoveryTestEventListener(flow.EventListener):
  """A test listener to receive new client discoveries."""
  well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:discovery_test")
  EVENTS = ["Discovery"]

  # For this test we just write the event as a class attribute.
  event = None

  @flow.EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    DiscoveryTestEventListener.event = event


class TestClientInterrogate(artifact_test.ArtifactTestHelper):
  """Test the interrogate flow."""

  def _CheckUsers(self, all_users):
    """Check all user stores."""
    summary = self.fd.Get(self.fd.Schema.SUMMARY)
    self.assertItemsEqual([x.username for x in summary.users], all_users)

    users = [x.username for x in self.fd.Get(self.fd.Schema.USER)]
    self.assertItemsEqual(users, all_users)
    self.assertItemsEqual(self.fd.Get(self.fd.Schema.USERNAMES), all_users)

    # Check kb users
    kbusers = [x.username for x in
               self.fd.Get(self.fd.Schema.KNOWLEDGE_BASE).users]
    self.assertItemsEqual(kbusers, all_users)

  def _CheckAFF4Object(self, hostname, system, install_date):
    self.assertEqual(self.fd.Get(self.fd.Schema.HOSTNAME), hostname)
    self.assertEqual(self.fd.Get(self.fd.Schema.SYSTEM), system)
    self.assertEqual(self.fd.Get(self.fd.Schema.INSTALL_DATE), install_date)

  def _CheckClientInfo(self):
    info = self.fd.Get(self.fd.Schema.CLIENT_INFO)
    self.assertEqual(info.client_name, config_lib.CONFIG["Client.name"])
    self.assertEqual(info.client_version,
                     int(config_lib.CONFIG["Client.version_numeric"]))
    self.assertEqual(info.build_time, config_lib.CONFIG["Client.build_time"])

  def _CheckGRRConfig(self):
    """Check old and new client config."""
    config_info = self.fd.Get(self.fd.Schema.GRR_CONFIGURATION)
    self.assertEqual(config_info["Client.control_urls"],
                     ["http://localhost:8001/control"])
    self.assertEqual(config_info["Client.poll_min"], 1.0)

  def _CheckClientIndex(self, host_pattern):
    """Check that the index has been updated."""
    index_fd = aff4.FACTORY.Create(self.fd.Schema.client_index, "AFF4Index",
                                   mode="r", token=self.token)

    self.assertEqual(
        [self.fd.urn],
        [x for x in index_fd.Query([self.fd.Schema.HOSTNAME], host_pattern)])

  def _CheckNotificationsCreated(self):
    user_fd = aff4.FACTORY.Open("aff4:/users/test", token=self.token)
    notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)

    self.assertEqual(len(notifications), 1)
    notification = notifications[0]

    self.assertEqual(notification.subject, rdfvalue.RDFURN(self.client_id))

  def _CheckClientSummary(self, osname, version):
    summary = self.fd.Get(self.fd.Schema.SUMMARY)
    self.assertEqual(summary.client_info.client_name,
                     config_lib.CONFIG["Client.name"])
    self.assertEqual(summary.client_info.client_version,
                     int(config_lib.CONFIG["Client.version_numeric"]))
    self.assertEqual(summary.client_info.build_time,
                     config_lib.CONFIG["Client.build_time"])

    self.assertEqual(summary.system_info.system, osname)
    self.assertEqual(summary.system_info.node, "test_node")
    self.assertEqual(summary.system_info.release, "5")
    self.assertEqual(summary.system_info.version, version)
    self.assertEqual(summary.system_info.machine, "i386")

    self.assertEqual(len(summary.interfaces), 1)
    self.assertEqual(summary.interfaces[0].mac_address, "123456")

    # Check that the client summary was published to the event listener.
    self.assertEqual(DiscoveryTestEventListener.event.client_id, self.client_id)
    self.assertEqual(
        DiscoveryTestEventListener.event.interfaces[0].mac_address,
        "123456")

  def _CheckNetworkInfo(self):
    net_fd = self.fd.OpenMember("network")
    interfaces = list(net_fd.Get(net_fd.Schema.INTERFACES))
    self.assertEqual(interfaces[0].mac_address, "123456")
    self.assertEqual(interfaces[0].addresses[0].human_readable, "100.100.100.1")
    self.assertEqual(socket.inet_ntoa(interfaces[0].addresses[0].packed_bytes),
                     "100.100.100.1")

    # Mac addresses should be available as hex for searching
    mac_addresses = self.fd.Get(self.fd.Schema.MAC_ADDRESS)
    self.assertTrue("123456".encode("hex") in str(mac_addresses))

    # Same for IP addresses.
    ip_addresses = self.fd.Get(self.fd.Schema.HOST_IPS)
    self.assertTrue("100.100.100.1" in str(ip_addresses))

  def _CheckVFS(self):
    # Check that virtual directories exist for the mount points
    fd = aff4.FACTORY.Open(self.client_id.Add("fs/os/mnt/data"),
                           token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

    fd = aff4.FACTORY.Open(self.client_id.Add("fs/tsk/dev/sda"),
                           token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

    fd = aff4.FACTORY.Open(self.client_id.Add("devices/dev/sda"),
                           token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

  def _CheckLabelIndex(self):
    """Check that label indexes are updated."""
    self.assertEqual(
        list(search.SearchClients("label:Label2", token=self.token)),
        [self.client_id])

  def _CheckWindowsDiskInfo(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    volumes = client.Get(client.Schema.VOLUMES)
    self.assertEqual(len(volumes), 2)
    for result in volumes:
      self.assertTrue(isinstance(result, rdfvalue.Volume))
      self.assertTrue(result.windows.drive_letter in ["Z:", "C:"])

  def _CheckRegistryPathspec(self):
    # This tests that we can click refresh on a key in the registry vfs subtree
    # even if we haven't downloaded any other key above it in the tree.

    fd = aff4.FACTORY.Open(self.client_id.Add("registry").Add(
        "HKEY_LOCAL_MACHINE").Add("random/path/bla"), token=self.token)
    pathspec = fd.real_pathspec
    self.assertEqual(pathspec.pathtype, rdfvalue.PathSpec.PathType.REGISTRY)
    self.assertEqual(pathspec.CollapsePath(),
                     u"/HKEY_LOCAL_MACHINE/random/path/bla")

  def testInterrogateLinuxWithWtmp(self):
    """Test the Interrogate flow."""
    test_lib.ClientFixture(self.client_id, token=self.token)

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.FakeTestDataVFSHandler

    config_lib.CONFIG.Set("Artifacts.knowledge_base", ["LinuxWtmp",
                                                       "NetgroupConfiguration"])
    config_lib.CONFIG.Set("Artifacts.netgroup_filter_regexes", [r"^login$"])
    self.SetLinuxClient()
    client_mock = action_mocks.InterrogatedClient("TransferBuffer", "StatFile",
                                                  "Find", "HashBuffer",
                                                  "ListDirectory",
                                                  "FingerprintFile")
    client_mock.InitializeClient()

    for _ in test_lib.TestFlowHelper("Interrogate", client_mock,
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    self.fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self._CheckAFF4Object("test_node", "Linux", 100 * 1000000)
    self._CheckClientInfo()
    self._CheckClientIndex(".*test.*")
    self._CheckGRRConfig()
    self._CheckNotificationsCreated()
    self._CheckClientSummary("Linux", "12.04")

    # users 1,2,3 from wtmp
    # users yagharek, isaac from netgroup
    self._CheckUsers(["yagharek", "isaac", "user1", "user2", "user3"])
    self._CheckNetworkInfo()
    self._CheckVFS()
    self._CheckLabelIndex()

  def testInterrogateWindows(self):
    """Test the Interrogate flow."""

    test_lib.ClientFixture(self.client_id, token=self.token)

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.FakeRegistryVFSHandler
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.FakeFullVFSHandler

    client_mock = action_mocks.InterrogatedClient("TransferBuffer", "StatFile",
                                                  "Find", "HashBuffer",
                                                  "ListDirectory",
                                                  "FingerprintFile")

    self.SetWindowsClient()
    client_mock.InitializeClient(system="Windows", version="6.1.7600")

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("Interrogate", client_mock,
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    self.fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self._CheckAFF4Object("test_node", "Windows", 100 * 1000000)
    self._CheckClientInfo()
    self._CheckClientIndex(".*Host.*")
    self._CheckGRRConfig()
    self._CheckNotificationsCreated()
    self._CheckClientSummary("Windows", "6.1.7600")

    # users Bert and Ernie added by the fixture should not be present (USERS
    # overriden by kb)
    # jim parsed from registry profile keys
    self._CheckUsers(["jim", "kovacs"])
    self._CheckNetworkInfo()
    self._CheckVFS()
    self._CheckLabelIndex()
    self._CheckWindowsDiskInfo()
    self._CheckRegistryPathspec()
