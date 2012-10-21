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

import os

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


class ListProcessesMock(test_lib.ActionMock):
  """Client with real file actions and mocked-out ListProcesses."""

  def __init__(self, processes_list):
    super(ListProcessesMock, self).__init__("TransferBuffer", "StatFile",
                                            "HashBuffer")
    self.processes_list = processes_list

  def ListProcesses(self, _):
    return self.processes_list


class GetProcessesBinariesTest(test_lib.FlowTestsBaseclass):
  """Test the get processes binaries flow."""

  def testFiltersOutProcessesWithoutExeAttribute(self):
    process = sysinfo_pb2.Process()
    process.pid = 2
    process.ppid = 1
    process.cmdline.append("test_img.dd")
    process.ctime = long(1333718907.167083 * 1e6)

    client_mock = ListProcessesMock([process])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    collection = fd.Get(fd.Schema.COLLECTION)
    self.assertEqual(len(collection), 0)

  def testFetchesAndStoresBinary(self):
    process = sysinfo_pb2.Process()
    process.pid = 2
    process.ppid = 1
    process.cmdline.append("test_img.dd")
    process.exe = os.path.join(self.base_path, "test_img.dd")
    process.ctime = long(1333718907.167083 * 1e6)

    client_mock = ListProcessesMock([process])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    collection = fd.Get(fd.Schema.COLLECTION)
    self.assertEqual(len(collection), 1)
    self.assertEqual(collection[0].pathspec.path, process.exe)
    self.assertEqual(collection[0].st_size, os.stat(process.exe).st_size)

  def testDoesNotFetchDuplicates(self):
    process1 = sysinfo_pb2.Process()
    process1.pid = 2
    process1.ppid = 1
    process1.cmdline.append("test_img.dd")
    process1.exe = os.path.join(self.base_path, "test_img.dd")
    process1.ctime = long(1333718907.167083 * 1e6)

    process2 = sysinfo_pb2.Process()
    process2.pid = 3
    process2.ppid = 1
    process2.cmdline.extend(["test_img.dd", "--arg"])
    process2.exe = os.path.join(self.base_path, "test_img.dd")
    process2.ctime = long(1333718942.167083 * 1e6)

    client_mock = ListProcessesMock([process1, process2])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    collection = fd.Get(fd.Schema.COLLECTION)
    self.assertEqual(len(collection), 1)

  def testIgnoresMissingFiles(self):
    process1 = sysinfo_pb2.Process()
    process1.pid = 2
    process1.ppid = 1
    process1.cmdline.append("test_img.dd")
    process1.exe = os.path.join(self.base_path, "test_img.dd")
    process1.ctime = long(1333718907.167083 * 1e6)

    process2 = sysinfo_pb2.Process()
    process2.pid = 2
    process2.ppid = 1
    process2.cmdline.append("file_that_does_not_exist")
    process2.exe = os.path.join(self.base_path, "file_that_does_not_exist")
    process2.ctime = long(1333718907.167083 * 1e6)

    client_mock = ListProcessesMock([process1, process2])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, check_flow_errors=False, output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    collection = fd.Get(fd.Schema.COLLECTION)
    self.assertEqual(len(collection), 1)
    self.assertEqual(collection[0].pathspec.path, process1.exe)
