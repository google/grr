#!/usr/bin/env python
"""Test the process list module."""

import os

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.aff4_objects import collects
# pylint: disable=unused-import
from grr.lib.flows.general import processes as _
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client


class ListProcessesMock(action_mocks.ActionMock):
  """Client with real file actions and mocked-out ListProcesses."""

  def __init__(self, processes_list):
    super(ListProcessesMock, self).__init__("TransferBuffer", "StatFile",
                                            "Find", "HashBuffer", "HashFile")
    self.processes_list = processes_list

  def ListProcesses(self, _):
    return self.processes_list


class ListProcessesTest(test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testProcessListingOnly(self):
    """Test that the ListProcesses flow works."""

    client_mock = ListProcessesMock([rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6))])

    flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                      flow_name="ListProcesses",
                                      output="Processes",
                                      token=self.token)
    for _ in test_lib.TestFlowHelper(flow_urn,
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    # Check the output collection
    processes = aff4.FACTORY.Open(
        self.client_id.Add("Processes"),
        token=self.token)

    self.assertEqual(len(processes), 1)
    self.assertEqual(processes[0].ctime, 1333718907167083L)
    self.assertEqual(processes[0].cmdline, ["cmd.exe"])

  def testProcessListingWithFilter(self):
    """Test that the ListProcesses flow works with filter."""

    client_mock = ListProcessesMock([
        rdf_client.Process(pid=2,
                           ppid=1,
                           cmdline=["cmd.exe"],
                           exe="c:\\windows\\cmd.exe",
                           ctime=long(1333718907.167083 * 1e6)),
        rdf_client.Process(pid=3,
                           ppid=1,
                           cmdline=["cmd2.exe"],
                           exe="c:\\windows\\cmd2.exe",
                           ctime=long(1333718907.167083 * 1e6)),
        rdf_client.Process(pid=4,
                           ppid=1,
                           cmdline=["missing_exe.exe"],
                           ctime=long(1333718907.167083 * 1e6)),
        rdf_client.Process(pid=5,
                           ppid=1,
                           cmdline=["missing2_exe.exe"],
                           ctime=long(1333718907.167083 * 1e6))
    ])

    flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                      flow_name="ListProcesses",
                                      output="Processes",
                                      filename_regex=r".*cmd2.exe",
                                      token=self.token)
    for _ in test_lib.TestFlowHelper(flow_urn,
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    # Expect one result that matches regex
    processes = aff4.FACTORY.Open(
        self.client_id.Add("Processes"),
        token=self.token)

    self.assertEqual(len(processes), 1)
    self.assertEqual(processes[0].ctime, 1333718907167083L)
    self.assertEqual(processes[0].cmdline, ["cmd2.exe"])

    # Expect two skipped results
    logs = aff4.FACTORY.Open(flow_urn.Add("Logs"), token=self.token)
    for log in logs:
      if "Skipped 2" in log.log_message:
        return
    raise RuntimeError("Skipped process not mentioned in logs")

  def testWhenFetchingFiltersOutProcessesWithoutExeAttribute(self):
    process = rdf_client.Process(pid=2,
                                 ppid=1,
                                 cmdline=["test_img.dd"],
                                 ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper("ListProcesses",
                                     client_mock,
                                     fetch_binaries=True,
                                     client_id=self.client_id,
                                     token=self.token,
                                     output=output_path):
      pass

    # No file created since no output matched.
    with self.assertRaises(IOError):
      aff4.FACTORY.Open(
          self.client_id.Add(output_path),
          aff4_type=collects.RDFValueCollection,
          token=self.token)

  def testFetchesAndStoresBinary(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper("ListProcesses",
                                     client_mock,
                                     client_id=self.client_id,
                                     fetch_binaries=True,
                                     token=self.token,
                                     output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)
    binaries = list(fd)
    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.path, process.exe)
    self.assertEqual(binaries[0].st_size, os.stat(process.exe).st_size)

  def testDoesNotFetchDuplicates(self):
    process1 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    process2 = rdf_client.Process(
        pid=3,
        ppid=1,
        cmdline=["test_img.dd", "--arg"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process1, process2])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper("ListProcesses",
                                     client_mock,
                                     client_id=self.client_id,
                                     fetch_binaries=True,
                                     token=self.token,
                                     output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)
    self.assertEqual(len(fd), 1)

  def testWhenFetchingIgnoresMissingFiles(self):
    process1 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=long(1333718907.167083 * 1e6))

    process2 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["file_that_does_not_exist"],
        exe=os.path.join(self.base_path, "file_that_does_not_exist"),
        ctime=long(1333718907.167083 * 1e6))

    client_mock = ListProcessesMock([process1, process2])
    output_path = "analysis/GetBinariesFlowTest1"

    for _ in test_lib.TestFlowHelper("ListProcesses",
                                     client_mock,
                                     client_id=self.client_id,
                                     fetch_binaries=True,
                                     token=self.token,
                                     check_flow_errors=False,
                                     output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)
    binaries = list(fd)
    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.path, process1.exe)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
