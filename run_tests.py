#!/usr/bin/env python
# Copyright 2010 Google Inc.
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


"""A test runner based on multiprocessing.

This program will run all the tests in separate processes to speed things up.
"""
# argparse is standard in 2.7 so pylint: disable=C6203
import argparse
import curses
import os
import StringIO
import subprocess
import sys
import time
import unittest

# These need to register plugins so, pylint: disable=W0611

from grr.client import client_test
from grr.client import client_utils_test
from grr.client import client_vfs_test
from grr.client.client_actions import action_test

from grr.lib import access_control_test
from grr.lib import aff4_test
from grr.lib import communicator_test
from grr.lib import data_store_test
from grr.lib import fake_data_store_test
from grr.lib import flow_test
from grr.lib import flow_utils_test
from grr.lib import front_end_test
from grr.lib import hunt_test
from grr.lib import lexer_test
from grr.lib import mongo_data_store_test
from grr.lib import objectfilter_test
from grr.lib import scheduler_test
from grr.lib import stats_test
from grr.lib import test_lib
from grr.lib import threadpool_test
from grr.lib import type_info_test
from grr.lib import utils_test

from grr.parsers import chrome_history_test
from grr.parsers import firefox3_history_test
from grr.parsers import ie_history_test
from grr.parsers import linux_log_parser_test
from grr.parsers import osx_launchd_test
from grr.parsers import osx_quarantine_test
from grr.parsers import sqlite_file_test
from grr.worker import worker_test


def ParseArgs(argv=None):
  """Parse command line args and return a FLAGS object."""
  parser = argparse.ArgumentParser()

  parser.add_argument("tests", metavar="N", type=str, nargs="*",
                      help="A list of test suites to run.")

  parser.add_argument("--output",
                      help="The name of the file we write on (default stderr).")

  parser.add_argument("--processes", type=int, default=5,
                      help="Total number of simultaneous tests to run.")

  return parser.parse_args(argv)


FLAGS = ParseArgs()


class Colorizer(object):
  """A Class which wraps a string with colors."""

  COLORS = "BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE"
  COLOR_MAP = dict([(x, i) for i, x in enumerate(COLORS.split())])

  terminal_capable = False

  def __init__(self, stream=None):
    if stream is None:
      stream = sys.stdout

    try:
      if stream.isatty():
        curses.setupterm()
        self.terminal_capable = True
    except AttributeError:
      pass

  def Render(self, color, string, forground=True):
    """Decorate the string with the ansii escapes for the color."""
    if not self.terminal_capable or color not in self.COLOR_MAP:
      return string

    escape_seq = curses.tigetstr("setf")
    if not forground:
      escape_seq = curses.tigetstr("setb")

    if not escape_seq:
      return string

    return (curses.tparm(escape_seq, self.COLOR_MAP[color]) + string +
            curses.tigetstr("sgr0"))


class GRREverythingTestLoader(test_lib.GRRTestLoader):
  """Load all GRR test cases."""
  base_class = test_lib.GRRBaseTest


def RunTest(test_suite, stream=None):
  out_fd = stream
  if stream:
    out_fd = StringIO.StringIO()

  try:
    test_lib.GrrTestProgram(argv=[sys.argv[0], test_suite],
                            testLoader=GRREverythingTestLoader(),
                            testRunner=unittest.TextTestRunner(
                                stream=out_fd))
  finally:
    if stream:
      stream.write("Test name: %s\n" % test_suite)
      stream.write(out_fd.getvalue())
      stream.flush()


def WaitForAvailableProcesses(processes, max_processes=5, completion_cb=None):
  while True:
    pending_processes = 0

    # Check up on all the processes in our queue:
    for name, metadata in processes.items():
      # Skip the processes which already exited.
      if metadata.get("exit_code") is not None:
        continue

      exit_code = metadata["pipe"].poll()
      if exit_code is None:
        pending_processes += 1
      else:
        metadata["exit_code"] = exit_code

        # Child has exited, report it.
        if completion_cb:
          completion_cb(name, metadata)

    # Do we need to wait for processes to become available?
    if pending_processes <= max_processes:
      break

    time.sleep(0.1)


def ReportTestResult(name, metadata):
  """Print statistics about the outcome of a test run."""
  now = time.time()
  colorizer = Colorizer()

  if metadata["exit_code"] == 0:
    # Test completed successfully:
    result = colorizer.Render("GREEN", "PASSED")
  else:
    result = colorizer.Render("RED", "FAILED")

  print "\t{0: <40} {1} in {2: >6.2f}s".format(
      name, result, now - metadata["start"])


def main(argv=None):
  if FLAGS.tests:
    stream = sys.stderr

    if FLAGS.output:
      stream = open(FLAGS.output, "ab")
      os.close(sys.stderr.fileno())
      os.close(sys.stdout.fileno())
      sys.stderr = stream
      sys.stdout = stream

    sys.argv = [""]

    for test_suite in FLAGS.tests:
      RunTest(test_suite, stream=stream)

  else:
    processes = {}

    with test_lib.TempDirectory() as FLAGS.temp_dir:
      start = time.time()

      for name in test_lib.GRRBaseTest.classes:
        result_filename = os.path.join(FLAGS.temp_dir, name)

        argv = [sys.executable] + sys.argv[:]
        if "--output" not in argv:
          argv.extend(["--output", result_filename])

        argv.append(name)

        # Maintain metadata about each test.
        processes[name] = dict(pipe=subprocess.Popen(argv),
                               start=time.time())

        WaitForAvailableProcesses(
            processes, max_processes=FLAGS.processes,
            completion_cb=ReportTestResult)

      # Wait for all jobs to finish.
      WaitForAvailableProcesses(processes, max_processes=0,
                                completion_cb=ReportTestResult)

      passed_tests = len([p for p in processes.values() if p["exit_code"] == 0])
      failed_tests = len([p for p in processes.values() if p["exit_code"] != 0])

      print "\nRan %s tests in %0.2f sec, %s tests passed, %s tests failed." % (
          len(processes), time.time() - start, passed_tests, failed_tests)

      if failed_tests:
        sys.exit(-1)

if __name__ == "__main__":
  main(sys.argv)
