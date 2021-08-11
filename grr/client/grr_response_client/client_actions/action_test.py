#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test client actions."""

import collections
import contextlib
import os
import platform
import stat
import unittest
from unittest import mock

from absl import app
import psutil

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client.client_actions import standard
from grr_response_client.unprivileged import communication
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class ProgressAction(actions.ActionPlugin):
  """A mock action which just calls Progress."""
  in_rdfvalue = rdf_client.LogMessage
  out_rdfvalues = [rdf_client.LogMessage]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # A number of tests below call action's Execute() method that
    # accepts a GrrMessage and checks whether it has passed the
    # authentication. Turning this off in order to not complicate
    # the testing code.
    self._authentication_required = False

  def Run(self, message):
    del message  # Unused.
    time = 100
    for _ in range(3):
      time += 5
      with test_lib.FakeTime(time):
        self.Progress()


class ActionTest(client_test_lib.EmptyActionTest):
  """Test the client Actions."""

  def testReadBuffer(self):
    """Test reading a buffer."""
    path = os.path.join(self.base_path, "morenumbers.txt")
    p = rdf_paths.PathSpec(path=path, pathtype=rdf_paths.PathSpec.PathType.OS)
    result = self.RunAction(
        standard.ReadBuffer,
        rdf_client.BufferReference(pathspec=p, offset=100, length=10))[0]

    self.assertEqual(result.offset, 100)
    self.assertEqual(result.length, 10)
    self.assertEqual(result.data, b"7\n38\n39\n40")

  def testListDirectory(self):
    """Tests listing directories."""
    p = rdf_paths.PathSpec(path=self.base_path, pathtype=0)
    results = self.RunAction(standard.ListDirectory,
                             rdf_client_action.ListDirRequest(pathspec=p))
    # Find the number.txt file
    result = None
    for result in results:
      if os.path.basename(result.pathspec.path) == "morenumbers.txt":
        break

    self.assertTrue(result)
    self.assertEqual(result.__class__, rdf_client_fs.StatEntry)
    self.assertEqual(result.pathspec.Basename(), "morenumbers.txt")
    self.assertEqual(result.st_size, 3893)
    self.assertTrue(stat.S_ISREG(int(result.st_mode)))

  def testProcessListing(self):
    """Tests if listing processes works."""

    def ProcessIter():
      return iter([client_test_lib.MockWindowsProcess()])

    with utils.Stubber(psutil, "process_iter", ProcessIter):
      results = self.RunAction(standard.ListProcesses, None)

      self.assertLen(results, 1)
      result = results[0]

      self.assertEqual(result.pid, 10)
      self.assertEqual(result.ppid, 1)
      self.assertEqual(result.name, "cmd")
      self.assertEqual(result.exe, "cmd.exe")
      self.assertEqual(result.cmdline, ["c:\\Windows\\cmd.exe", "/?"])
      self.assertEqual(result.ctime, 1217061982375000)
      self.assertEqual(result.username, "test")
      self.assertEqual(result.status, "running")
      self.assertEqual(result.cwd, "X:\\RECEPÇÕES")
      self.assertEqual(result.num_threads, 1)
      self.assertEqual(result.user_cpu_time, 1.0)
      self.assertEqual(result.system_cpu_time, 1.0)
      # This is disabled in the flow since it takes too long.
      # self.assertEqual(result.cpu_percent, 10.0)
      self.assertEqual(result.RSS_size, 100000)
      self.assertEqual(result.VMS_size, 150000)
      self.assertEqual(result.memory_percent, 10.0)
      self.assertEqual(result.nice, 10)

  def testRaisesWhenRuntimeLimitIsExceeded(self):
    message = rdf_flows.GrrMessage(
        name="ProgressAction",
        runtime_limit_us=rdfvalue.Duration.From(9, rdfvalue.SECONDS))
    worker = mock.MagicMock()
    with test_lib.FakeTime(100):
      action = ProgressAction(worker)
      action.SendReply = mock.MagicMock()  # pylint: disable=invalid-name
      action.Execute(message)

    self.assertEqual(action.SendReply.call_count, 1)
    self.assertEqual(action.SendReply.call_args[0][0].status,
                     "RUNTIME_LIMIT_EXCEEDED")

    self.assertEqual(worker.Heartbeat.call_count, 1)

    self.assertEqual(worker.SendClientAlert.call_count, 1)
    self.assertEqual(worker.SendClientAlert.call_args[0][0],
                     "Runtime limit exceeded.")

  def testDoesNotRaiseWhenFasterThanRuntimeLimit(self):
    message = rdf_flows.GrrMessage(
        name="ProgressAction",
        runtime_limit_us=rdfvalue.Duration.From(16, rdfvalue.SECONDS))
    worker = mock.MagicMock()
    with test_lib.FakeTime(100):
      action = ProgressAction(worker)
      action.SendReply = mock.MagicMock()  # pylint: disable=invalid-name
      action.Execute(message)

    self.assertEqual(worker.Heartbeat.call_count, 3)
    self.assertEqual(action.SendReply.call_count, 1)
    self.assertEqual(action.SendReply.call_args[0][0].status, "OK")

  def testDoesNotRaiseForZeroRuntimeLimit(self):
    message = rdf_flows.GrrMessage(name="ProgressAction", runtime_limit_us=0)
    worker = mock.MagicMock()
    with test_lib.FakeTime(100):
      action = ProgressAction(worker)
      action.SendReply = mock.MagicMock()
      action.Execute(message)

    self.assertEqual(worker.Heartbeat.call_count, 3)
    self.assertEqual(action.SendReply.call_count, 1)
    self.assertEqual(action.SendReply.call_args[0][0].status, "OK")

  def testCPUAccounting(self):
    with contextlib.ExitStack() as stack:
      server_cpu_time = 1.0
      server_sys_time = 1.1
      stack.enter_context(
          mock.patch.object(communication, "TotalServerCpuTime",
                            lambda: server_cpu_time))
      stack.enter_context(
          mock.patch.object(communication, "TotalServerSysTime",
                            lambda: server_sys_time))

      process_cpu_time = 1.2
      process_sys_time = 1.3

      class FakeProcess(object):

        def __init__(self, pid=None):
          pass

        def cpu_times(self):  # pylint: disable=invalid-name
          return collections.namedtuple("pcputimes",
                                        ["user", "system"])(process_cpu_time,
                                                            process_sys_time)

      stack.enter_context(mock.patch.object(psutil, "Process", FakeProcess))

      class _ProgressAction(ProgressAction):

        def Run(self, *args):
          super().Run(*args)
          nonlocal server_cpu_time, server_sys_time
          server_cpu_time = 42.0
          server_sys_time = 43.0
          nonlocal process_cpu_time, process_sys_time
          process_cpu_time = 10.0
          process_sys_time = 11.0

      message = rdf_flows.GrrMessage(name="ProgressAction", runtime_limit_us=0)
      worker = mock.MagicMock()
      action = _ProgressAction(worker)
      action.SendReply = mock.MagicMock()
      action.Execute(message)
      self.assertEqual(action.SendReply.call_count, 1)
      self.assertAlmostEqual(
          action.SendReply.call_args[0][0].cpu_time_used.user_cpu_time,
          42.0 - 1.0 + 10.0 - 1.2)
      self.assertAlmostEqual(
          action.SendReply.call_args[0][0].cpu_time_used.system_cpu_time,
          43.0 - 1.1 + 11.0 - 1.3)

  def testCPULimit(self):

    class FakeProcess(object):

      def __init__(self, pid=None):
        del pid  # unused
        self.times = [(1, 0), (2, 0), (3, 0), (10000, 0), (10001, 0)]
        self.pcputimes = collections.namedtuple("pcputimes", ["user", "system"])

      def cpu_times(self):  # pylint: disable=g-bad-name
        return self.pcputimes(*self.times.pop(0))

    with mock.patch.object(psutil, "Process", FakeProcess):
      worker = mock.MagicMock()
      action = ProgressAction(grr_worker=worker)
      message = rdf_flows.GrrMessage(name="ProgressAction", cpu_limit=3600)
      action.Execute(message)

      self.assertEqual(worker.SendReply.call_count, 1)
      reply = worker.SendReply.call_args[0][0]

      self.assertIn("Action exceeded cpu limit.", reply.error_message)
      self.assertIn("CPUExceededError", reply.error_message)
      self.assertEqual("CPU_LIMIT_EXCEEDED", reply.status)

      self.assertEqual(worker.SendClientAlert.call_count, 1)
      self.assertEqual(worker.SendClientAlert.call_args[0][0],
                       "Cpu limit exceeded.")

  @unittest.skipIf(platform.system() == "Windows",
                   "os.statvfs is not available on Windows")
  def testStatFS(self):
    import posix  # pylint: disable=g-import-not-at-top

    f_bsize = 4096
    # Simulate pre-2.6 kernel
    f_frsize = 0
    f_blocks = 9743394
    f_bfree = 5690052
    f_bavail = 5201809
    f_files = 2441216
    f_ffree = 2074221
    f_favail = 2074221
    f_flag = 4096
    f_namemax = 255

    def MockStatFS(unused_path):
      return posix.statvfs_result(
          (f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree,
           f_favail, f_flag, f_namemax))

    def MockIsMount(path):
      """Only return True for the root path."""
      # All code should ideally deal only with unicode paths. Unfortunately,
      # this is not always the case. While fixing path handling should be dealt
      # with at some point, for the time being this works and is more in line
      # with the original function (`os.path.ismount` works with bytestrings as
      # well).
      return path == "/" or path == b"/"

    with utils.MultiStubber((os, "statvfs", MockStatFS),
                            (os.path, "ismount", MockIsMount)):

      # This test assumes "/" is the mount point for /usr/bin
      results = self.RunAction(
          standard.StatFS,
          rdf_client_action.StatFSRequest(path_list=["/usr/bin", "/"]))
      self.assertLen(results, 2)

      # Both results should have mount_point as "/"
      self.assertEqual(results[0].unixvolume.mount_point,
                       results[1].unixvolume.mount_point)
      result = results[0]
      self.assertEqual(result.bytes_per_sector, f_bsize)
      self.assertEqual(result.sectors_per_allocation_unit, 1)
      self.assertEqual(result.total_allocation_units, f_blocks)
      self.assertEqual(result.actual_available_allocation_units, f_bavail)
      self.assertAlmostEqual(result.FreeSpacePercent(), 53.388, delta=0.001)
      self.assertEqual(result.unixvolume.mount_point, "/")
      self.assertEqual(result.Name(), "/")

      # Test we get a result even if one path is bad
      results = self.RunAction(
          standard.StatFS,
          rdf_client_action.StatFSRequest(path_list=["/does/not/exist", "/"]))
      self.assertLen(results, 1)
      self.assertEqual(result.Name(), "/")

  def testProgressThrottling(self):

    class MockWorker(object):

      def Heartbeat(self):
        pass

    worker = MockWorker()

    with test_lib.Instrument(client_utils, "KeepAlive") as instrument:
      for time, expected_count in [(100, 1), (101, 1), (102, 1), (103, 2),
                                   (104, 2), (105, 2), (106, 3)]:
        with test_lib.FakeTime(time):
          action = ProgressAction(grr_worker=worker)
          action.Progress()
          self.assertEqual(instrument.call_count, expected_count)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
