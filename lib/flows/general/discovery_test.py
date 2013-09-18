#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for Interrogate."""

import socket

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib


class InterrogatedClient(object):
  """A mock of client state."""

  def GetPlatformInfo(self, _):
    return [rdfvalue.Uname(
        system="Linux",
        node="test_node",
        release="5",
        version="2",
        machine="i386")]

  def GetInstallDate(self, _):
    return [rdfvalue.DataBlob(integer=100)]

  def EnumerateUsers(self, _):
    return [rdfvalue.User(username="Foo",
                          full_name="FooFoo",
                          last_logon=150),
            rdfvalue.User(username="Bar",
                          full_name="BarBar",
                          last_logon=250),
            rdfvalue.User(username=u"文德文",
                          full_name="BarBar",
                          last_logon=250)]

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

  def Find(self, _):
    raise RuntimeError("Find not supported in this test, "
                       "use EnumerateUsers.")


class TestClientInterrogate(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def setUp(self):
    super(TestClientInterrogate, self).setUp()
    self.flow_reply = None

  def MockSendReply(self, reply=None):
    self.flow_reply = reply

  def testInterrogate(self):
    """Test the Interrogate flow."""

    flow_name = "Interrogate"

    with test_lib.Stubber(flow.GRRFlow, "SendReply", self.MockSendReply):
      # Run the flow in the simulated way
      for _ in test_lib.TestFlowHelper(flow_name, InterrogatedClient(),
                                       token=self.token,
                                       client_id=self.client_id):
        pass

    # Now check that the AFF4 object is properly set
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.assertEqual(fd.Get(fd.Schema.HOSTNAME), "test_node")
    self.assertEqual(fd.Get(fd.Schema.SYSTEM), "Linux")
    self.assertEqual(fd.Get(fd.Schema.INSTALL_DATE), 100 * 1000000)

    # Check the client info
    info = fd.Get(fd.Schema.CLIENT_INFO)

    self.assertEqual(info.client_name, config_lib.CONFIG["Client.name"])
    self.assertEqual(info.client_version,
                     int(config_lib.CONFIG["Client.version_numeric"]))
    self.assertEqual(info.build_time, config_lib.CONFIG["Client.build_time"])

    # Check the client config
    config_info = fd.Get(fd.Schema.GRR_CONFIG)
    self.assertEqual(config_info.location, "http://www.example.com")
    self.assertEqual(config_info.poll_min, 1.0)

    # Check that the index has been updated.
    index_fd = aff4.FACTORY.Create(fd.Schema.client_index, "AFF4Index",
                                   mode="r", token=self.token)

    self.assertEqual(
        [fd.urn],
        [x for x in index_fd.Query([fd.Schema.HOSTNAME], ".*test.*")])

    # Check for notifications
    user_fd = aff4.FACTORY.Open("aff4:/users/test", token=self.token)
    notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)

    self.assertEqual(len(notifications), 1)
    notification = notifications[0]

    self.assertEqual(notification.subject, rdfvalue.RDFURN(self.client_id))

    # Check that reply sent from the flow is correct
    self.assertEqual(self.flow_reply.client_info.client_name,
                     config_lib.CONFIG["Client.name"])
    self.assertEqual(self.flow_reply.client_info.client_version,
                     int(config_lib.CONFIG["Client.version_numeric"]))
    self.assertEqual(self.flow_reply.client_info.build_time,
                     config_lib.CONFIG["Client.build_time"])

    self.assertEqual(self.flow_reply.system_info.system, "Linux")
    self.assertEqual(self.flow_reply.system_info.node, "test_node")
    self.assertEqual(self.flow_reply.system_info.release, "5")
    self.assertEqual(self.flow_reply.system_info.version, "2")
    self.assertEqual(self.flow_reply.system_info.machine, "i386")

    users = list(fd.Get(fd.Schema.USER))
    self.assertEqual(len(users), 3)
    self.assertEqual(users[0].username, "Foo")
    self.assertEqual(users[1].username, "Bar")
    self.assertEqual(users[2].username, u"文德文")
    self.assertEqual(str(fd.Get(fd.Schema.USERNAMES)),
                     "Foo Bar 文德文")

    net_fd = fd.OpenMember("network")
    interfaces = list(net_fd.Get(net_fd.Schema.INTERFACES))
    self.assertEqual(interfaces[0].mac_address, "123456")
    self.assertEqual(interfaces[0].addresses[0].human_readable, "127.0.0.1")
    self.assertEqual(socket.inet_ntoa(interfaces[0].addresses[0].packed_bytes),
                     "127.0.0.1")

    # Mac addresses should be available as hex for searching
    mac_addresses = fd.Get(fd.Schema.MAC_ADDRESS)
    self.assertTrue("123456".encode("hex") in str(mac_addresses))

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

    # Check the empty process branch exists
    fd = aff4.FACTORY.Open(self.client_id.Add("processes"), token=self.token)
    self.assertEqual(fd.__class__.__name__, "ProcessListing")

    # Check flow's reply
    self.assertEqual(len(self.flow_reply.users), 3)
    self.assertEqual(self.flow_reply.users[0].username, "Foo")
    self.assertEqual(self.flow_reply.users[1].username, "Bar")
    self.assertEqual(self.flow_reply.users[2].username, u"文德文")

    self.assertEqual(len(self.flow_reply.interfaces), 1)
    self.assertEqual(self.flow_reply.interfaces[0].mac_address, "123456")
