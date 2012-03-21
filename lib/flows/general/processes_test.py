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


"""Test the process list module."""
import shlex

from grr.client import vfs
from grr.lib import aff4
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2


class ProcessListTest(test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testWindowsProcessListing(self):
    """Test that the ListWindowsProcesses flow works."""

    class ClientMock(object):
      def WmiQuery(self, _):
        process1 = dict(ProcessId=2, ParentProcessId=1,
                        CommandLine="cmd.exe",
                        ExecutablePath="c:\windows\cmd.exe",
                        CreationDate="20080726084622.375000+120")

        return [utils.ProtoDict(process1).ToProto()]

    for _ in test_lib.TestFlowHelper(
        "ListWindowsProcesses", ClientMock(), client_id=self.client_id,
        token=self.token):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(
        self.client_id).Add("processes"), token=self.token)
    processes = fd.Get(fd.Schema.PROCESSES).data

    self.assertEqual(len(processes), 1)
    self.assertEqual(processes[0].ctime, 1217061982375000L)
    self.assertEqual(processes[0].cmdline, "cmd.exe")

  def testLinuxProcessListing(self):
    """Test the ListLinuxProcesses flow works."""
    # Install the mock
    vfs.VFS_HANDLERS[jobs_pb2.Path.OS] = test_lib.ClientVFSHandlerFixture

    client_mock = test_lib.ActionMock("ListDirectory", "ReadBuffer")

    for _ in test_lib.TestFlowHelper(
        "ListLinuxProcesses", client_mock, client_id=self.client_id,
        token=self.token):
      pass

    process_fd = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add(self.client_id).Add("processes"), token=self.token)
    processes = list(process_fd.Get(process_fd.Schema.PROCESSES))
    self.assertEqual(len(processes), 1)
    self.assertEqual(processes[0].exe, "/bin/ls")
    argv = shlex.split(utils.SmartStr(processes[0].cmdline))
    self.assertEqual(argv[0], "ls")
    self.assertEqual(argv[1], "hello world'")
    self.assertEqual(argv[2], "-l")

    for _ in test_lib.TestFlowHelper(
        "ListLinuxProcesses", client_mock, client_id=self.client_id,
        token=self.token):
      pass

    process_fd = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add(self.client_id).Add("processes"), token=self.token)
    processes = list(process_fd.Get(process_fd.Schema.PROCESSES))
