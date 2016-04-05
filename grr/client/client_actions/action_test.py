#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test client actions."""

import __builtin__
import collections
import logging
import os
import platform
import posix
import stat

import mock
import psutil

# Populate the action registry
# pylint: disable=unused-import, g-bad-import-order
from grr.client import client_plugins
from grr.client import client_utils
from grr.client.client_actions import standard
# pylint: enable=unused-import, g-bad-import-order

from grr.client import actions
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils
from grr.lib import worker_mocks
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths


# pylint: mode=test
# pylint: disable=g-bad-name


class MockWindowsProcess(object):
  """A mock windows process."""

  pid = 10

  def ppid(self):
    return 1

  def name(self):
    return "cmd"

  def exe(self):
    return "cmd.exe"

  def username(self):
    return "test"

  def cmdline(self):
    return ["c:\\Windows\\cmd.exe", "/?"]

  def create_time(self):
    return 1217061982.375000

  def status(self):
    return "running"

  def cwd(self):
    return "X:\\RECEP\xc3\x87\xc3\x95ES"

  def num_threads(self):
    return 1

  def cpu_times(self):
    return (1.0, 1.0)

  def cpu_percent(self):
    return 10.0

  def memory_info(self):
    meminfo = collections.namedtuple("Meminfo", ["rss", "vms"])
    return meminfo(rss=100000, vms=150000)

  def memory_percent(self):
    return 10.0

  def open_files(self):
    return []

  def connections(self):
    return []

  def nice(self):
    return 10

  def as_dict(self, attrs=None):
    dic = {}
    if attrs is None:
      return dic
    for name in attrs:
      if hasattr(self, name):
        attr = getattr(self, name)
        if callable(attr):
          dic[name] = attr()
        else:
          dic[name] = attr
      else:
        dic[name] = None
    return dic


class ProgressAction(actions.ActionPlugin):
  """A mock action which just calls Progress."""
  in_rdfvalue = rdf_client.LogMessage
  out_rdfvalues = [rdf_client.LogMessage]

  time = 100

  def Run(self, message):
    _ = message
    for _ in range(3):
      self.time += 5
      with test_lib.FakeTime(self.time):
        self.Progress()


def process_iter():
  return iter([MockWindowsProcess()])


class ActionTest(test_lib.EmptyActionTest):
  """Test the client Actions."""

  def testReadBuffer(self):
    """Test reading a buffer."""
    path = os.path.join(self.base_path, "morenumbers.txt")
    p = rdf_paths.PathSpec(path=path,
                           pathtype=rdf_paths.PathSpec.PathType.OS)
    result = self.RunAction("ReadBuffer",
                            rdf_client.BufferReference(
                                pathspec=p, offset=100, length=10))[0]

    self.assertEqual(result.offset, 100)
    self.assertEqual(result.length, 10)
    self.assertEqual(result.data, "7\n38\n39\n40")

  def testListDirectory(self):
    """Tests listing directories."""
    p = rdf_paths.PathSpec(path=self.base_path, pathtype=0)
    results = self.RunAction("ListDirectory",
                             rdf_client.ListDirRequest(
                                 pathspec=p))
    # Find the number.txt file
    result = None
    for result in results:
      if os.path.basename(result.pathspec.path) == "morenumbers.txt":
        break

    self.assertTrue(result)
    self.assertEqual(result.__class__, rdf_client.StatEntry)
    self.assertEqual(result.pathspec.Basename(), "morenumbers.txt")
    self.assertEqual(result.st_size, 3893)
    self.assertTrue(stat.S_ISREG(result.st_mode))

  def testIteratedListDirectory(self):
    """Tests iterated listing of directories."""
    p = rdf_paths.PathSpec(path=self.base_path,
                           pathtype=rdf_paths.PathSpec.PathType.OS)
    non_iterated_results = self.RunAction(
        "ListDirectory", rdf_client.ListDirRequest(pathspec=p))

    # Make sure we get some results.
    l = len(non_iterated_results)
    self.assertTrue(l > 0)

    iterated_results = []
    request = rdf_client.ListDirRequest(pathspec=p)
    request.iterator.number = 2
    while True:
      responses = self.RunAction("IteratedListDirectory", request)
      results = responses[:-1]
      if not results: break

      for result in results:
        iterated_results.append(result)

    for x, y in zip(non_iterated_results, iterated_results):
      # Reset the st_atime in the results to avoid potential flakiness.
      x.st_atime = y.st_atime = 0

      self.assertRDFValuesEqual(x, y)

  def testSuspendableListDirectory(self):
    request = rdf_client.ListDirRequest()
    request.pathspec.path = self.base_path
    request.pathspec.pathtype = "OS"
    request.iterator.number = 2
    results = []

    grr_worker = worker_mocks.FakeClientWorker()

    while request.iterator.state != request.iterator.State.FINISHED:
      responses = self.RunAction("SuspendableListDirectory", request,
                                 grr_worker=grr_worker)
      results.extend(responses)
      for response in responses:
        if isinstance(response, rdf_client.Iterator):
          request.iterator = response

    filenames = [os.path.basename(r.pathspec.path)
                 for r in results if isinstance(r, rdf_client.StatEntry)]

    self.assertItemsEqual(filenames, os.listdir(self.base_path))

    iterators = [r for r in results if isinstance(r, rdf_client.Iterator)]
    # One for two files plus one extra with the FINISHED status.
    nr_files = len(os.listdir(self.base_path))
    expected_iterators = (nr_files / 2) + 1
    if nr_files % 2:
      expected_iterators += 1
    self.assertEqual(len(iterators), expected_iterators)

    # Make sure the thread has been deleted.
    self.assertEqual(grr_worker.suspended_actions, {})

  def testSuspendableActionException(self):

    class testActionWorker(actions.ClientActionWorker):

      def run(self):
        try:
          return super(testActionWorker, self).run()
        except Exception as e:  # pylint: disable=broad-except
          logging.info("Expected exception: %s", e)

    class RaisingListDirectory(standard.SuspendableListDirectory):

      iterations = 3

      def Suspend(self):
        RaisingListDirectory.iterations -= 1
        if not RaisingListDirectory.iterations:
          raise IOError("Ran out of iterations.")

        return super(RaisingListDirectory, self).Suspend()

    p = rdf_paths.PathSpec(path=self.base_path,
                           pathtype=rdf_paths.PathSpec.PathType.OS)
    request = rdf_client.ListDirRequest(pathspec=p)
    request.iterator.number = 2
    results = []

    grr_worker = worker_mocks.FakeClientWorker()
    while request.iterator.state != request.iterator.State.FINISHED:
      responses = self.ExecuteAction("RaisingListDirectory", request,
                                     grr_worker=grr_worker,
                                     action_worker_cls=testActionWorker)
      results.extend(responses)

      for response in responses:
        if isinstance(response, rdf_client.Iterator):
          request.iterator = response

      status = responses[-1]
      self.assertTrue(isinstance(status, rdf_flows.GrrStatus))
      if status.status != rdf_flows.GrrStatus.ReturnedStatus.OK:
        break

      if len(results) > 100:
        self.fail("Endless loop detected.")

    self.assertIn("Ran out of iterations", status.error_message)
    self.assertEqual(grr_worker.suspended_actions, {})

  def testEnumerateUsersLinux(self):
    """Enumerate users from the wtmp file."""
    # Linux only
    if platform.system() != "Linux": return

    path = os.path.join(self.base_path, "VFSFixture/var/log/wtmp")
    old_open = __builtin__.open
    old_listdir = os.listdir

    # Mock the open call
    def MockedOpen(requested_path, mode="r"):
      # Any calls to open the wtmp get the mocked out version.
      if "wtmp" in requested_path:
        self.assertEqual(requested_path, "/var/log/wtmp")
        return old_open(path)

      # Everything else has to be opened normally.
      return old_open(requested_path, mode)

    __builtin__.open = MockedOpen
    os.listdir = lambda x: ["wtmp"]
    try:
      results = self.RunAction("EnumerateUsers")
    finally:
      # Restore the original methods.
      __builtin__.open = old_open
      os.listdir = old_listdir

    found = 0
    for result in results:
      # This appears in ut_type RUN_LVL, not ut_type USER_PROCESS.
      self.assertNotEqual("runlevel", result.username)
      if result.username == "user1":
        found += 1
        self.assertEqual(result.last_logon, 1296552099 * 1000000)
      elif result.username == "user2":
        found += 1
        self.assertEqual(result.last_logon, 1296552102 * 1000000)
      elif result.username == "user3":
        found += 1
        self.assertEqual(result.last_logon, 1296569997 * 1000000)

    self.assertEqual(found, 3)

  def testProcessListing(self):
    """Tests if listing processes works."""

    old_process_iter = psutil.process_iter
    psutil.process_iter = process_iter

    try:
      results = self.RunAction("ListProcesses", None)

      self.assertEqual(len(results), 1)
      result = results[0]

      self.assertEqual(result.pid, 10)
      self.assertEqual(result.ppid, 1)
      self.assertEqual(result.name, "cmd")
      self.assertEqual(result.exe, "cmd.exe")
      self.assertEqual(result.cmdline, ["c:\\Windows\\cmd.exe", "/?"])
      self.assertEqual(result.ctime, 1217061982375000)
      self.assertEqual(result.username, "test")
      self.assertEqual(result.status, "running")
      self.assertEqual(result.cwd, ur"X:\RECEPÇÕES")
      self.assertEqual(result.num_threads, 1)
      self.assertEqual(result.user_cpu_time, 1.0)
      self.assertEqual(result.system_cpu_time, 1.0)
      # This is disabled in the flow since it takes too long.
      # self.assertEqual(result.cpu_percent, 10.0)
      self.assertEqual(result.RSS_size, 100000)
      self.assertEqual(result.VMS_size, 150000)
      self.assertEqual(result.memory_percent, 10.0)
      self.assertEqual(result.nice, 10)

    finally:
      psutil.process_iter = old_process_iter

  def testCPULimit(self):

    received_messages = []

    class MockWorker(object):

      def SendClientAlert(self, msg):
        received_messages.append(msg)

    class FakeProcess(object):

      times = [(1, 0), (2, 0), (3, 0), (10000, 0), (10001, 0)]

      def __init__(self, unused_pid):
        pass

      def cpu_times(self):
        return self.times.pop(0)

    results = []

    def MockSendReply(unused_self, reply=None, **kwargs):
      results.append(reply or rdf_client.LogMessage(**kwargs))

    message = rdf_flows.GrrMessage(name="ProgressAction", cpu_limit=3600)

    action_cls = actions.ActionPlugin.classes[message.name]
    with utils.MultiStubber((psutil, "Process", FakeProcess),
                            (action_cls, "SendReply", MockSendReply)):

      action_cls._authentication_required = False
      action = action_cls(grr_worker=MockWorker())
      action.Execute(message)

      self.assertTrue("Action exceeded cpu limit." in results[0].error_message)
      self.assertTrue("CPUExceededError" in results[0].error_message)

      self.assertEqual(len(received_messages), 1)
      self.assertEqual(received_messages[0], "Cpu limit exceeded.")

  def testSendReplyMultipleOutputTypes(self):
    """Check we can SendReply with multiple out_rdfvalues."""
    fake_worker = mock.MagicMock()
    actionplugin = actions.ActionPlugin(grr_worker=fake_worker)
    actionplugin.message = mock.MagicMock()
    actionplugin.out_rdfvalues = [rdf_client.BufferReference,
                                  rdf_client.Process]

    actionplugin.SendReply(data="blah")
    self.assertTrue(isinstance(fake_worker.SendReply.call_args[0][0],
                               rdf_client.BufferReference))

    with self.assertRaises(AttributeError):
      actionplugin.SendReply(badkeyword=10)

  def testStatFS(self):
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
      return posix.statvfs_result((f_bsize, f_frsize, f_blocks, f_bfree,
                                   f_bavail, f_files, f_ffree, f_favail, f_flag,
                                   f_namemax))

    def MockIsMount(path):
      """Only return True for the root path."""
      return path == "/"

    with utils.MultiStubber((os, "statvfs", MockStatFS),
                            (os.path, "ismount", MockIsMount)):

      # This test assumes "/" is the mount point for /usr/bin
      results = self.RunAction(
          "StatFS", rdf_client.StatFSRequest(path_list=["/usr/bin", "/"]))
      self.assertEqual(len(results), 2)

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
          "StatFS",
          rdf_client.StatFSRequest(path_list=["/does/not/exist", "/"]))
      self.assertEqual(len(results), 1)
      self.assertEqual(result.Name(), "/")

  def testProgressThrottling(self):
    action = actions.ActionPlugin.classes["ProgressAction"]()

    with test_lib.Instrument(client_utils, "KeepAlive") as instrument:
      for time, expected_count in [(100, 1),
                                   (101, 1),
                                   (102, 1),
                                   (103, 2),
                                   (104, 2),
                                   (105, 2),
                                   (106, 3)]:
        with test_lib.FakeTime(time):
          action.Progress()
          self.assertEqual(instrument.call_count, expected_count)


class ActionTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.EmptyActionTest


def main(argv):
  test_lib.GrrTestProgram(argv=argv, testLoader=ActionTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
