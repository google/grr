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

from grr.lib import aff4
from grr.lib import test_lib
from grr.proto import sysinfo_pb2


class ProcessListTest(test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testProcessListing(self):
    """Test that the ListProcesses flow works."""

    class ClientMock(object):
      def ListProcesses(self, _):
        response = sysinfo_pb2.Process()
        response.pid = 2
        response.ppid = 1
        response.cmdline.append("cmd.exe")
        response.exe = "c:\\windows\\cmd.exe"
        response.ctime = long(1333718907.167083 * 1e6)
        return [response]

    for _ in test_lib.TestFlowHelper(
        "ListProcesses", ClientMock(), client_id=self.client_id,
        token=self.token):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(
        self.client_id).Add("processes"), token=self.token)
    processes = fd.Get(fd.Schema.PROCESSES).data

    self.assertEqual(len(processes), 1)
    self.assertEqual(processes[0].ctime, 1333718907167083L)
    self.assertEqual(processes[0].cmdline, ["cmd.exe"])
