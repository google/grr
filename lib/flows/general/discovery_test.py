#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for Interrogate."""

from grr.client import client_config
from grr.lib import aff4
from grr.lib import test_lib
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class InterrogatedClient(object):
  """A mock of client state."""

  def GetPlatformInfo(self, _):
    return [jobs_pb2.Uname(
        system="Linux",
        node="test_node",
        release="5",
        version="2",
        machine="i386")]

  def GetInstallDate(self, _):
    return [jobs_pb2.DataBlob(integer=100)]

  def EnumerateUsers(self, _):
    return [jobs_pb2.UserAccount(username="Foo",
                                 full_name="FooFoo",
                                 last_logon=150),
            jobs_pb2.UserAccount(username="Bar",
                                 full_name="BarBar",
                                 last_logon=250),
            jobs_pb2.UserAccount(username=u"文德文",
                                 full_name="BarBar",
                                 last_logon=250)]

  def EnumerateInterfaces(self, _):
    return [jobs_pb2.Interface(mac_address="123456",
                               ip4_addresses="127.0.0.1")]

  def EnumerateFilesystems(self, _):
    return [sysinfo_pb2.Filesystem(device="/dev/sda",
                                   mount_point="/mnt/data")]

  def GetClientInfo(self, _):
    return [jobs_pb2.ClientInformation(
        client_name=client_config.GRR_CLIENT_NAME,
        client_version=client_config.GRR_CLIENT_VERSION,
        revision=client_config.GRR_CLIENT_REVISION,
        build_time=client_config.GRR_CLIENT_BUILDTIME)]

  def GetConfig(self, _):
    return [jobs_pb2.GRRConfig(
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


class TestInterrogate(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def CheckLightweight(self, fd):
    """Checks for attributes set by the lightweight interrogation flow."""

    self.assertEqual(fd.Get(fd.Schema.HOSTNAME), "test_node")
    self.assertEqual(fd.Get(fd.Schema.SYSTEM), "Linux")
    self.assertEqual(fd.Get(fd.Schema.INSTALL_DATE), 100 * 1000000)

    # Check the client info
    info = fd.Get(fd.Schema.CLIENT_INFO).data

    self.assertEqual(info.client_name, client_config.GRR_CLIENT_NAME)
    self.assertEqual(info.client_version, client_config.GRR_CLIENT_VERSION)
    self.assertEqual(info.revision, client_config.GRR_CLIENT_REVISION)
    self.assertEqual(info.build_time, client_config.GRR_CLIENT_BUILDTIME)

    # Check the client config
    config_info = fd.Get(fd.Schema.GRR_CONFIG)
    self.assertEqual(config_info.data.location, "http://www.example.com")
    self.assertEqual(config_info.data.poll_min, 1.0)

    # Check that the index has been updated.
    index_fd = aff4.FACTORY.Create(fd.Schema.client_index, "AFF4Index",
                                   mode="r", token=self.token)

    self.assertEqual(
        [fd.urn],
        [x.urn for x in index_fd.Query([fd.Schema.HOSTNAME], "test")])

    # Check for notifications
    fd = aff4.FACTORY.Open("aff4:/users/test", token=self.token)
    notifications = fd.Get(fd.Schema.PENDING_NOTIFICATIONS)

    self.assertEqual(len(notifications.data), 1)
    notification = notifications.data[0]

    self.assertEqual(notification.subject, self.client_id)

  def testLightweightInterrogate(self):
    """Tests the lightweight interrogation."""

    flow_name = "Interrogate"

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper(flow_name, InterrogatedClient(),
                                     token=self.token,
                                     client_id=self.client_id,
                                     lightweight=True):
      pass

    # Now check that the AFF4 object is properly set
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.CheckLightweight(fd)

    # Users have not been created.
    users = fd.Get(fd.Schema.USER)
    self.assertEqual(users, None)

  def testInterrogate(self):
    """Test the Interrogate flow."""

    flow_name = "Interrogate"

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper(flow_name, InterrogatedClient(),
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    # Now check that the AFF4 object is properly set
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)

    self.CheckLightweight(fd)

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

    # Mac addresses should be available as hex for searching
    mac_addresses = fd.Get(fd.Schema.MAC_ADDRESS)
    self.assert_("123456".encode("hex") in str(mac_addresses))

    # Check that virtual directories exist for the mount points
    fd = aff4.FACTORY.Open(self.client_id + "/fs/os/mnt/data", token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

    fd = aff4.FACTORY.Open(self.client_id + "/fs/tsk/dev/sda", token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

    fd = aff4.FACTORY.Open(self.client_id + "/devices/dev/sda",
                           token=self.token)
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(len(list(fd.OpenChildren())), 0)

    # Check the empty process branch exists
    fd = aff4.FACTORY.Open(self.client_id + "/processes", token=self.token)
    self.assertEqual(fd.__class__.__name__, "ProcessListing")
