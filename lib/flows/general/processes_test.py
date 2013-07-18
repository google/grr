#!/usr/bin/env python
"""Test the process list module."""

import os

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class ProcessListTest(test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testProcessListing(self):
    """Test that the ListProcesses flow works."""

    class ClientMock(object):
      def ListProcesses(self, _):
        response = rdfvalue.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=long(1333718907.167083 * 1e6))
        return [response]

    for _ in test_lib.TestFlowHelper(
        "ListProcesses", ClientMock(), client_id=self.client_id,
        token=self.token):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(self.client_id.Add("processes"), token=self.token)
    processes = fd.Get(fd.Schema.PROCESSES)

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
    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    self.assertEqual(len(fd), 0)

  def testFetchesAndStoresBinary(self):
    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    summaries = list(fd)
    self.assertEqual(len(summaries), 1)
    self.assertEqual(summaries[0].stat.pathspec.path, process.exe)
    self.assertEqual(summaries[0].stat.st_size, os.stat(process.exe).st_size)

  def testDoesNotFetchDuplicates(self):
    process1 = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    process2 = rdfvalue.Process(
        pid=3,
        ppid=1,
        cmdline=["test_img.dd", "--arg"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process1, process2])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    self.assertEqual(len(fd), 1)

  def testIgnoresMissingFiles(self):
    process1 = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    process2 = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["file_that_does_not_exist"],
        exe=os.path.join(self.base_path, "file_that_does_not_exist"),
        ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process1, process2])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper(
        "GetProcessesBinaries", client_mock, client_id=self.client_id,
        token=self.token, check_flow_errors=False, output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    summaries = list(fd)
    self.assertEqual(len(summaries), 1)
    self.assertEqual(summaries[0].stat.pathspec.path, process1.exe)


class VolatilityActionMock(test_lib.ActionMock):
  """Client with real file actions and mocked-out VolatilityAction."""

  def __init__(self, processes_list):
    super(VolatilityActionMock, self).__init__("TransferBuffer", "StatFile",
                                               "HashBuffer")
    self.processes_list = processes_list

  def VolatilityAction(self, _):
    volatility_response = rdfvalue.VolatilityResult()

    section = rdfvalue.VolatilitySection()
    section.table.headers.Append(print_name="Protection", name="protection")
    section.table.headers.Append(print_name="start", name="start_pfn")
    section.table.headers.Append(print_name="Filename", name="filename")

    for proc in self.processes_list:
      section.table.rows.Append(values=[
          rdfvalue.VolatilityValue(
              type="__MMVAD_FLAGS", name="VadFlags",
              offset=0, vm="None", value=7,
              svalue="EXECUTE_WRITECOPY"),

          rdfvalue.VolatilityValue(
              value=42),

          rdfvalue.VolatilityValue(
              type="_UNICODE_STRING", name="FileName",
              offset=275427702111096,
              vm="AMD64PagedMemory@0x00187000 (Kernel AS@0x187000)",
              value=275427702111096, svalue=proc)
          ])
    volatility_response.sections.Append(section)

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

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    # Sorting output collection to make the test deterministic
    summaries = sorted(fd, key=lambda x: x.urn)

    self.assertEqual(len(summaries), 2)

    self.assertEqual(summaries[0].stat.pathspec.path, process1_exe)
    self.assertEqual(summaries[0].stat.st_size, os.stat(process1_exe).st_size)

    self.assertEqual(summaries[1].stat.pathspec.path, process2_exe)
    self.assertEqual(summaries[1].stat.st_size, os.stat(process2_exe).st_size)

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

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    summaries = list(fd)

    self.assertEqual(len(summaries), 1)
    self.assertEqual(summaries[0].stat.pathspec.path, process_exe)
    self.assertEqual(summaries[0].stat.st_size, os.stat(process_exe).st_size)

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

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    summaries = list(fd)

    self.assertEqual(len(summaries), 1)
    self.assertEqual(summaries[0].stat.pathspec.path, process1_exe)
    self.assertEqual(summaries[0].stat.st_size, os.stat(process1_exe).st_size)

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

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    summaries = list(fd)
    self.assertEqual(len(summaries), 1)
    self.assertEqual(summaries[0].stat.pathspec.path, process1_exe)
    self.assertEqual(summaries[0].stat.st_size, os.stat(process1_exe).st_size)
