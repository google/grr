#!/usr/bin/env python
"""End to end tests for lib.flows.general.processes."""

from grr_response_proto import flows_pb2
from grr_response_test.end_to_end_tests import test_base


class TestProcessListing(test_base.EndToEndTest):
  """Test ListProcesses."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    f = self.RunFlowAndWait("ListProcesses")

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    # TODO(user): add a check for a GRR process (probably need to query
    # the server for the configuration option containing GRR agent name
    # to do that).


class TestListProcessesLinux(test_base.EndToEndTest):
  """Linux-specific tests for the process listing flow."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def testFilterPID(self):
    args = flows_pb2.ListProcessesArgs()
    # TODO - By default `filename_regex` is `.` and since it is
    # not supported by RRG yet, this skips RRG logic entirely. We clear it but
    # once RRG path support is added for it we can revert back to the default
    # value.
    args.filename_regex = ""
    args.pids.append(1)
    args.pids.append(2)

    flow = self.RunFlowAndWait("ListProcesses", args)

    results = list(flow.ListResults())
    self.assertLen(results, 2)

    results_by_pid = {result.payload.pid: result.payload for result in results}
    # PID 1 is the init system but this is pluggable so we cannot assert on a
    # specific name.
    self.assertIn(1, results_by_pid)
    # PID 2 on the other head is guaranteed to be the kernel thread daemon.
    self.assertEqual(results_by_pid[2].name, "kthreadd")


class TestListProcessesWindows(test_base.EndToEndTest):
  """Windows-specific tests for the process listing flow."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def testFilterPID(self):
    args = flows_pb2.ListProcessesArgs()
    # TODO - By default `filename_regex` is `.` and since it is
    # not supported by RRG yet, this skips RRG logic entirely. We clear it but
    # once RRG path support is added for it we can revert back to the default
    # value.
    args.filename_regex = ""
    args.pids.append(0)
    args.pids.append(4)

    flow = self.RunFlowAndWait("ListProcesses", args)

    results = list(flow.ListResults())
    self.assertLen(results, 2)

    results_by_pid = {result.payload.pid: result.payload for result in results}
    self.assertEqual(results_by_pid[0].name, "System Idle Process")
    self.assertEqual(results_by_pid[4].name, "System")


class TestListProcessesMacos(test_base.EndToEndTest):
  """macOS-specifc tests for the process listing flow."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  def testFilterPID(self):
    args = flows_pb2.ListProcessesArgs()
    # TODO - By default `filename_regex` is `.` and since it is
    # not supported by RRG yet, this skips RRG logic entirely. We clear it but
    # once RRG path support is added for it we can revert back to the default
    # value.
    args.filename_regex = ""
    args.pids.append(1)

    flow = self.RunFlowAndWait("ListProcesses", args)

    results = list(flow.ListResults())
    self.assertLen(results, 1)

    results_by_pid = {result.payload.pid: result.payload for result in results}
    self.assertEqual(results_by_pid[1].name, "launchd")
