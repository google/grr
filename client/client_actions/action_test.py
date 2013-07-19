#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc. All Rights Reserved.
"""Test client actions."""


import __builtin__
import hashlib
import os
import platform
import stat

import psutil


# Populate the action registry
# pylint: disable=unused-import
from grr.client import actions
from grr.client import client_actions
from grr.client import comms
from grr.client import vfs
from grr.client.client_actions import tests
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import utils
# pylint: disable=g-bad-name


class MockWindowsProcess(object):

  pid = 10
  ppid = 1
  name = "cmd"
  exe = "cmd.exe"
  username = "test"
  cmdline = ["c:\\Windows\\cmd.exe", "/?"]

  create_time = 1217061982.375000
  status = "running"

  def getcwd(self):
    return "X:\\RECEP\xc3\x87\xc3\x95ES"

  def get_num_threads(self):
    return 1

  def get_cpu_times(self):
    return (1.0, 1.0)

  def get_cpu_percent(self):
    return 10.0

  def get_memory_info(self):
    return (100000, 150000)

  def get_memory_percent(self):
    return 10.0

  def get_open_files(self):
    return []

  def get_connections(self):
    return []

  def get_nice(self):
    return 10


class ProgressAction(actions.ActionPlugin):
  """A mock action which just calls Progress."""
  in_rdfvalue = rdfvalue.LogMessage
  out_rdfvalue = rdfvalue.LogMessage

  def Run(self, message):
    _ = message
    self.Progress()
    self.Progress()
    self.Progress()


def process_iter():
  return iter([MockWindowsProcess()])


class ActionTest(test_lib.EmptyActionTest):
  """Test the client Actions."""

  def testReadBuffer(self):
    """Test reading a buffer."""
    path = os.path.join(self.base_path, "morenumbers.txt")
    p = rdfvalue.PathSpec(path=path,
                          pathtype=rdfvalue.PathSpec.PathType.OS)
    result = self.RunAction("ReadBuffer",
                            rdfvalue.BufferReference(
                                pathspec=p, offset=100, length=10))[0]

    self.assertEqual(result.offset, 100)
    self.assertEqual(result.length, 10)
    self.assertEqual(result.data, "7\n38\n39\n40")

  def testListDirectory(self):
    """Tests listing directories."""
    p = rdfvalue.PathSpec(path=self.base_path, pathtype=0)
    results = self.RunAction("ListDirectory",
                             rdfvalue.ListDirRequest(
                                 pathspec=p))
    # Find the number.txt file
    result = None
    for result in results:
      if os.path.basename(result.pathspec.path) == "morenumbers.txt":
        break

    self.assert_(result)
    self.assertEqual(result.__class__, rdfvalue.StatEntry)
    self.assertEqual(result.pathspec.Basename(), "morenumbers.txt")
    self.assertEqual(result.st_size, 3893)
    self.assert_(stat.S_ISREG(result.st_mode))

  def testIteratedListDirectory(self):
    """Tests iterated listing of directories."""
    p = rdfvalue.PathSpec(path=self.base_path,
                          pathtype=rdfvalue.PathSpec.PathType.OS)
    non_iterated_results = self.RunAction(
        "ListDirectory", rdfvalue.ListDirRequest(pathspec=p))

    # Make sure we get some results.
    l = len(non_iterated_results)
    self.assertTrue(l > 0)

    iterated_results = []
    request = rdfvalue.ListDirRequest(pathspec=p)
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

      self.assertProtoEqual(x, y)

  def testHashFile(self):
    """Can we hash a file?"""
    path = os.path.join(self.base_path, "morenumbers.txt")
    p = rdfvalue.PathSpec(path=path,
                          pathtype=rdfvalue.PathSpec.PathType.OS)

    # The action returns a DataBlob object.
    result = self.RunAction("HashFile",
                            rdfvalue.ListDirRequest(
                                pathspec=p))[0]

    self.assertEqual(result.data,
                     hashlib.sha256(open(path).read()).digest())

  def testEnumerateUsersLinux(self):
    """Enumerate users from the wtmp file."""
    # Linux only
    if platform.system() != "Linux": return

    path = os.path.join(self.base_path, "wtmp")
    old_open = __builtin__.open
    old_listdir = os.listdir

    # Mock the open call
    def MockedOpen(_):
      return old_open(path)

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

      def get_cpu_times(self):
        return self.times.pop(0)

    results = []

    def MockSendReply(unused_self, reply=None, **kwargs):
      results.append(reply or rdfvalue.LogMessage(**kwargs))

    message = rdfvalue.GrrMessage(name="ProgressAction", cpu_limit=3600)

    old_proc = psutil.Process
    psutil.Process = FakeProcess
    try:
      action_cls = actions.ActionPlugin.classes[message.name]
      old_sendreply = action_cls.SendReply
      action_cls.SendReply = MockSendReply
      action_cls._authentication_required = False
      action = action_cls(message=message, grr_worker=MockWorker())

      action.Execute()

      self.assertTrue("Action exceeded cpu limit." in results[0].error_message)
      self.assertTrue("CPUExceededError" in results[0].error_message)

      self.assertTrue(len(received_messages), 1)
      self.assertEqual(received_messages[0], "Cpu limit exceeded.")
    finally:
      psutil.Process = old_proc
      action_cls.SendReply = old_sendreply


class ActionTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.EmptyActionTest


def main(argv):
  test_lib.GrrTestProgram(argv=argv, testLoader=ActionTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
