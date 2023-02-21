#!/usr/bin/env python
"""Test the process list module."""

import os

from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_server import data_store
from grr_response_server.flows.general import processes as flow_processes
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ListProcessesTest(flow_test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testProcessListingOnly(self):
    """Test that the ListProcesses flow works."""
    client_id = self.SetupClient(0)

    client_mock = action_mocks.ListProcessesMock([
        rdf_client.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083)
    ])

    session_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        client_id=client_id,
        creator=self.test_username)

    processes = flow_test_lib.GetFlowResults(client_id, session_id)

    self.assertLen(processes, 1)
    self.assertEqual(processes[0].ctime, 1333718907167083)
    self.assertEqual(processes[0].cmdline, ["cmd.exe"])

  def testProcessListingWithFilter(self):
    """Test that the ListProcesses flow works with filter."""
    client_id = self.SetupClient(0)

    client_mock = action_mocks.ListProcessesMock([
        rdf_client.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe="c:\\windows\\cmd.exe",
            ctime=1333718907167083),
        rdf_client.Process(
            pid=3,
            ppid=1,
            cmdline=["cmd2.exe"],
            exe="c:\\windows\\cmd2.exe",
            ctime=1333718907167083),
        rdf_client.Process(
            pid=4, ppid=1, cmdline=["missing_exe.exe"], ctime=1333718907167083),
        rdf_client.Process(
            pid=5, ppid=1, cmdline=["missing2_exe.exe"], ctime=1333718907167083)
    ])

    session_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        filename_regex=r".*cmd2.exe")

    # Expect one result that matches regex
    processes = flow_test_lib.GetFlowResults(client_id, session_id)

    self.assertLen(processes, 1)
    self.assertEqual(processes[0].ctime, 1333718907167083)
    self.assertEqual(processes[0].cmdline, ["cmd2.exe"])

    # Expect two skipped results
    logs = data_store.REL_DB.ReadFlowLogEntries(client_id, session_id, 0, 100)
    for log in logs:
      if "Skipped 2" in log.message:
        return
    raise RuntimeError("Skipped process not mentioned in logs")

  def testProcessListingFilterConnectionState(self):
    client_id = self.SetupClient(0)
    p1 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        connections=[
            rdf_client_network.NetworkConnection(family="INET", state="CLOSED")
        ])
    p2 = rdf_client.Process(
        pid=3,
        ppid=1,
        cmdline=["cmd2.exe"],
        exe="c:\\windows\\cmd2.exe",
        ctime=1333718907167083,
        connections=[
            rdf_client_network.NetworkConnection(family="INET", state="LISTEN")
        ])
    p3 = rdf_client.Process(
        pid=4,
        ppid=1,
        cmdline=["missing_exe.exe"],
        ctime=1333718907167083,
        connections=[
            rdf_client_network.NetworkConnection(
                family="INET", state="ESTABLISHED")
        ])
    client_mock = action_mocks.ListProcessesMock([p1, p2, p3])

    session_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        connection_states=["ESTABLISHED", "LISTEN"])

    processes = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(processes, 2)
    states = set()
    for process in processes:
      states.add(str(process.connections[0].state))
    self.assertCountEqual(states, ["ESTABLISHED", "LISTEN"])

  def testWhenFetchingFiltersOutProcessesWithoutExeAndConnectionState(self):
    client_id = self.SetupClient(0)
    p1 = rdf_client.Process(
        pid=2, ppid=1, cmdline=["test_img.dd"], ctime=1333718907167083)

    p2 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        connections=[
            rdf_client_network.NetworkConnection(
                family="INET", state="ESTABLISHED")
        ])

    client_mock = action_mocks.ListProcessesMock([p1, p2])

    session_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        fetch_binaries=True,
        client_id=client_id,
        connection_states=["LISTEN"],
        creator=self.test_username)

    # No output matched.
    processes = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertEmpty(processes)

  def testFetchesAndStoresBinary(self):
    client_id = self.SetupClient(0)

    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083)

    client_mock = action_mocks.ListProcessesMock([process])

    session_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        client_id=client_id,
        fetch_binaries=True,
        creator=self.test_username)

    binaries = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(binaries, 1)
    self.assertEqual(binaries[0].pathspec.path, process.exe)
    self.assertEqual(binaries[0].st_size, os.stat(process.exe).st_size)

  def testDoesNotFetchDuplicates(self):
    client_id = self.SetupClient(0)
    process1 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083)

    process2 = rdf_client.Process(
        pid=3,
        ppid=1,
        cmdline=["test_img.dd", "--arg"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083)

    client_mock = action_mocks.ListProcessesMock([process1, process2])

    session_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        client_id=client_id,
        fetch_binaries=True,
        creator=self.test_username)

    processes = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(processes, 1)

  def testWhenFetchingIgnoresMissingFiles(self):
    client_id = self.SetupClient(0)
    process1 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["test_img.dd"],
        exe=os.path.join(self.base_path, "test_img.dd"),
        ctime=1333718907167083)

    process2 = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["file_that_does_not_exist"],
        exe=os.path.join(self.base_path, "file_that_does_not_exist"),
        ctime=1333718907167083)

    client_mock = action_mocks.ListProcessesMock([process1, process2])

    session_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        client_id=client_id,
        fetch_binaries=True,
        creator=self.test_username,
        check_flow_errors=False)

    binaries = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(binaries, 1)
    self.assertEqual(binaries[0].pathspec.path, process1.exe)

  def testPidFiltering(self):
    client_id = self.SetupClient(0)

    proc_foo = rdf_client.Process()
    proc_foo.pid = 42
    proc_foo.exe = "/usr/bin/foo"

    proc_bar = rdf_client.Process()
    proc_bar.pid = 108
    proc_bar.exe = "/usr/bin/bar"

    proc_baz = rdf_client.Process()
    proc_baz.pid = 1337
    proc_baz.exe = "/usr/bin/baz"

    args = flow_processes.ListProcessesArgs()
    args.pids = [42, 1337]

    client_mock = action_mocks.ListProcessesMock([proc_foo, proc_bar, proc_baz])
    flow_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
        client_mock=client_mock,
        client_id=client_id,
        flow_args=args,
    )

    results = flow_test_lib.GetFlowResults(client_id=client_id, flow_id=flow_id)
    self.assertLen(results, 2)

    result_exes = {result.exe for result in results}
    self.assertIn("/usr/bin/foo", result_exes)
    self.assertIn("/usr/bin/baz", result_exes)
    self.assertNotIn("/usr/bin/bar", result_exes)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
