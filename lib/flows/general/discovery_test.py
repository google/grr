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

from grr.lib import aff4
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class TestInterrogate(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def testInterrogate(self):
    """Test the Interrogate flow."""

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
                                     last_logon=250)]

      def EnumerateInterfaces(self, _):
        return [jobs_pb2.Interface(mac_address="123456",
                                   ip_address="127.0.0.1")]

      def EnumerateFilesystems(self, _):
        return [sysinfo_pb2.Filesystem(device="/dev/sda",
                                       mount_point="/mnt/data")]

    flow_name = "Interrogate"
    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper(flow_name, InterrogatedClient(),
                                     client_id=self.client_id):
      pass

    # Now check that the AFF4 object is properly set
    fd = aff4.FACTORY.Open(self.client_id)

    self.assertEqual(fd.Get(fd.Schema.HOSTNAME), "test_node")
    self.assertEqual(fd.Get(fd.Schema.SYSTEM), "Linux")
    self.assertEqual(fd.Get(fd.Schema.INSTALL_DATE), 100 * 1000000)

    users = list(fd.Get(fd.Schema.USER))
    self.assertEqual(len(users), 2)
    self.assertEqual(users[0].username, "Foo")
    self.assertEqual(users[1].username, "Bar")

    interfaces = list(fd.Get(fd.Schema.INTERFACE))
    self.assertEqual(interfaces[0].mac_address, "123456")

    # Mac addresses should be available as hex for searching
    mac_addresses = fd.Get(fd.Schema.MAC_ADDRESS)
    self.assert_("123456".encode("hex") in str(mac_addresses))

    # Check that virtual directories exist for the mount points
    fd = aff4.FACTORY.Open(self.client_id + "/mnt/data")
    # But no directory listing exists yet - we will need to fetch a new one
    self.assertEqual(fd.Get(fd.Schema.DIRECTORY), None)

  def testWindowsProcessListing(self):
    """Test the windows process listing flow."""

    class TestClientMock(object):
      """A mock of client state."""

      def WmiQuery(self, _):
        for x in range(1, 5):
          yield utils.ProtoDict(
              dict(ProcessId=x,
                   ParentProcessId=x,
                   CommandLine="command %s" % x,
                   ExecutablePath="c:\\command %s.exe" % x,
                   CreationDate="20080%d26084622.375000+120" % x)).ToProto()

    # First make a client
    self.testInterrogate()

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("ListWindowsProcesses", TestClientMock(),
                                     client_id=self.client_id):
      pass

    # Now check that the AFF4 object is properly set
    fd = aff4.FACTORY.Open(self.client_id)
    processes = fd.Get(fd.Schema.PROCESSES)

    for i, process in enumerate(processes):
      i += 1
      self.assertEqual(process.pid, i)
      self.assertEqual(process.ppid, i)
      self.assertEqual(process.cmdline, "command %s" % i)
