#!/usr/bin/env python
"""Test the process list module."""

import os

from grr.lib import aff4
from grr.lib import test_lib
from grr.proto import jobs_pb2
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


class VolatilityActionMock(test_lib.ActionMock):
  """Client with real file actions and mocked-out VolatilityAction."""

  def __init__(self, processes_list):
    super(VolatilityActionMock, self).__init__("TransferBuffer", "StatFile",
                                               "HashBuffer")
    self.processes_list = processes_list

  def VolatilityAction(self, _):
    volatility_response = jobs_pb2.VolatilityResponse()

    section = volatility_response.sections.add()

    header = section.table.headers.add()
    header.print_name = "Protection"
    header.name = "protection"

    header = section.table.headers.add()
    header.print_name = "start"
    header.name = "start_pfn"

    header = section.table.headers.add()
    header.print_name = "Filename"
    header.name = "filename"

    for proc in self.processes_list:
      row = section.table.rows.add()

      value = row.values.add()
      value.type = "__MMVAD_FLAGS"
      value.name = "VadFlags"
      value.offset = 0
      value.vm = "None"
      value.value = 7
      value.svalue = "EXECUTE_WRITECOPY"

      value = row.values.add()
      value.value = 42

      value = row.values.add()
      value.type = "_UNICODE_STRING"
      value.name = "FileName"
      value.offset = 275427702111096
      value.vm = "AMD64PagedMemory@0x00187000 (Kernel AS@0x187000)"
      value.value = 275427702111096
      value.svalue = proc

    return [volatility_response]


class GetProcessesBinariesVolatilityTest(test_lib.FlowTestsBaseclass):
  """Tests the Volatility-powered "get processes binaries" flow."""

  def testFetchesAndStoresBinary(self):
    process1_exe = os.path.join(self.base_path, "test_img.dd")
    process2_exe = os.path.join(self.base_path, "winexec_img.dd")

    client_mock = VolatilityActionMock([process1_exe, process2_exe])
    output_path = "analysis/GetBinariesFlowVolatilityTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinariesVolatility",
        client_mock,
        client_id=self.client_id,
        token=self.token,
        output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    # Sorting output collection to make the test deterministic
    collection = sorted(fd.Get(fd.Schema.COLLECTION),
                        key=lambda k: k.pathspec.path)
    self.assertEqual(len(collection), 2)

    self.assertEqual(collection[0].pathspec.path, process1_exe)
    self.assertEqual(collection[0].st_size, os.stat(process1_exe).st_size)

    self.assertEqual(collection[1].pathspec.path, process2_exe)
    self.assertEqual(collection[1].st_size, os.stat(process2_exe).st_size)

  def testDoesNotFetchDuplicates(self):
    process_exe = os.path.join(self.base_path, "test_img.dd")
    client_mock = VolatilityActionMock([process_exe, process_exe])
    output_path = "analysis/GetBinariesFlowVolatilityTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinariesVolatility",
        client_mock,
        client_id=self.client_id,
        token=self.token,
        output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    collection = fd.Get(fd.Schema.COLLECTION)
    self.assertEqual(len(collection), 1)
    self.assertEqual(collection[0].pathspec.path, process_exe)
    self.assertEqual(collection[0].st_size, os.stat(process_exe).st_size)

  def testFiltersOutBinariesUsingRegex(self):
    process1_exe = os.path.join(self.base_path, "test_img.dd")
    process2_exe = os.path.join(self.base_path, "empty_file")

    client_mock = VolatilityActionMock([process1_exe, process2_exe])
    output_path = "analysis/GetBinariesFlowVolatilityTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinariesVolatility",
        client_mock,
        client_id=self.client_id,
        token=self.token,
        output=output_path,
        filename_regex=".*\\.dd$"):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    collection = fd.Get(fd.Schema.COLLECTION)
    self.assertEqual(len(collection), 1)
    self.assertEqual(collection[0].pathspec.path, process1_exe)
    self.assertEqual(collection[0].st_size, os.stat(process1_exe).st_size)

  def testIgnoresMissingFiles(self):
    process1_exe = os.path.join(self.base_path, "test_img.dd")
    process2_exe = os.path.join(self.base_path, "file_that_does_not_exist")

    client_mock = VolatilityActionMock([process1_exe, process2_exe])
    output_path = "analysis/GetBinariesFlowVolatilityTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinariesVolatility",
        client_mock,
        check_flow_errors=False,
        client_id=self.client_id,
        token=self.token,
        output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(output_path),
                           token=self.token)
    collection = fd.Get(fd.Schema.COLLECTION)
    self.assertEqual(len(collection), 1)
    self.assertEqual(collection[0].pathspec.path, process1_exe)
    self.assertEqual(collection[0].st_size, os.stat(process1_exe).st_size)
