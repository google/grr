#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for Interrogate."""

import socket

from grr.client import vfs
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


class InterrogatedClient(test_lib.ActionMock):
  """A mock of client state."""

  def InitializeClient(self, system="Linux", version="12.04"):
    self.system = system
    self.version = version
    self.response_count = 0

  def GetPlatformInfo(self, _):
    return [rdfvalue.Uname(
        system=self.system,
        node="test_node",
        release="5",
        version=self.version,
        machine="i386")]

  def GetInstallDate(self, _):
    return [rdfvalue.DataBlob(integer=100)]

  def EnumerateInterfaces(self, _):
    return [rdfvalue.Interface(
        mac_address="123456",
        addresses=[
            rdfvalue.NetworkAddress(
                address_type=rdfvalue.NetworkAddress.Family.INET,
                human_readable="127.0.0.1",
                packed_bytes=socket.inet_aton("127.0.0.1"),
                )]
        )]

  def EnumerateFilesystems(self, _):
    return [rdfvalue.Filesystem(device="/dev/sda",
                                mount_point="/mnt/data")]

  def GetClientInfo(self, _):
    return [rdfvalue.ClientInformation(
        client_name=config_lib.CONFIG["Client.name"],
        client_version=int(config_lib.CONFIG["Client.version_numeric"]),
        build_time=config_lib.CONFIG["Client.build_time"],
        labels=["GRRLabel1", "Label2"],
        )]

  def GetConfig(self, _):
    return [rdfvalue.GRRConfig(
        location="http://www.example.com",
        foreman_check_frequency=1,
        max_post_size=1000000,
        max_out_queue=100,
        poll_min=1.0,
        poll_max=5
        )]

  def GetUserInfo(self, user):
    user.homedir = "/usr/local/home/%s" % user.username
    user.full_name = user.username.capitalize()
    return [user]

  def GetConfiguration(self, _):
    return [rdfvalue.Dict({"Client.control_urls":
                           ["http://localhost:8001/control"], "Client.poll_min":
                           1.0})]


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
    config_info = self.fd.Get(self.fd.Schema.GRR_CONFIG)
    self.assertEqual(config_info.location, "http://www.example.com")
    self.assertEqual(config_info.poll_min, 1.0)

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
    self.assertEqual(interfaces[0].addresses[0].human_readable, "127.0.0.1")
    self.assertEqual(socket.inet_ntoa(interfaces[0].addresses[0].packed_bytes),
                     "127.0.0.1")

    # Mac addresses should be available as hex for searching
    mac_addresses = self.fd.Get(self.fd.Schema.MAC_ADDRESS)
    self.assertTrue("123456".encode("hex") in str(mac_addresses))

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

  def testInterrogateLinuxWithWtmp(self):
    """Test the Interrogate flow."""
    test_lib.ClientFixture(self.client_id, token=self.token)

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientTestDataVFSFixture

    config_lib.CONFIG.Set("Artifacts.knowledge_base", ["LinuxWtmp",
                                                       "NetgroupConfiguration"])
    config_lib.CONFIG.Set("Artifacts.netgroup_filter_regexes", [r"^login$"])
    self.SetLinuxClient()
    client_mock = InterrogatedClient("TransferBuffer", "StatFile", "Find",
                                     "HashBuffer", "ListDirectory", "HashFile")
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
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.ClientRegistryVFSFixture
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientFullVFSFixture

    client_mock = InterrogatedClient("TransferBuffer", "StatFile", "Find",
                                     "HashBuffer", "ListDirectory", "HashFile")

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


