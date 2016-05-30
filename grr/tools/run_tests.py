#!/usr/bin/env python
"""A test runner based on multiprocessing.

This program will run all the tests in separate processes to speed things up.
"""

import curses
import os
import StringIO
import subprocess
import sys
import time
import unittest

import psutil

# These need to register plugins so,
# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
from grr.checks import tests
from grr.client import tests

from grr.gui import tests
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import tests
from grr.lib import utils
from grr.parsers import tests
from grr.path_detection import tests
from grr.server.data_server import tests
from grr.tools.export_plugins import tests
from grr.worker import worker_test
# pylint: enable=unused-import,g-bad-import-order

flags.DEFINE_string("output", None,
                    "The name of the file we write on (default stderr).")

flags.DEFINE_list("exclude_tests", [],
                  "A comma-separated list of tests to exclude form running.")

flags.DEFINE_integer("processes", 0,
                     "Total number of simultaneous tests to run.")


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
  """Run an individual test.

  Ignore the argument test_suite passed to this function, then
  magically acquire an individual test name as specified by the --tests
  flag, run it, and then exit the whole Python program completely.

  Args:
    test_suite: Ignored.
    stream: The stream to print results to.

  Returns:
    This function does not return; it causes a program exit.
  """

  out_fd = stream
  if stream:
    out_fd = StringIO.StringIO()

  try:
    # Here we use a GRREverythingTestLoader to load tests from.
    # However, the fact that GRREverythingTestLoader loads all
    # tests is irrelevant, because GrrTestProgram simply reads
    # from the --tests flag passed to the program, so not all
    # tests are ran. Only the test specified via --tests will
    # be ran. Because --tests supports only one test at a time
    # this will cause only an individual test to be ran.
    # GrrTestProgram then terminates the execution of the whole
    # python program using sys.exit() so this function does not
    # return.
    test_lib.GrrTestProgram(argv=[sys.argv[0], test_suite],
                            testLoader=GRREverythingTestLoader(
                                labels=flags.FLAGS.labels),
                            testRunner=unittest.TextTestRunner(stream=out_fd))
  finally:
    # Clean up before the program exits.
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
    result += open(metadata["output_path"], "rb").read()

  print "\t{0: <40} {1} in {2: >6.2f}s".format(name, result,
                                               now - metadata["start"])


def DoesTestHaveLabels(cls, labels):
  """Returns true if any tests in cls have any of the labels."""
  labels = set(labels)

  for name in dir(cls):
    if name.startswith("test"):
      item = getattr(cls, name, None)
      if labels.intersection(getattr(item, "labels", set(["small"]))):
        return True

  return False


def main(argv=None):
  if flags.FLAGS.tests:
    stream = sys.stderr

    if flags.FLAGS.output:
      stream = open(flags.FLAGS.output, "ab")
      os.close(sys.stderr.fileno())
      os.close(sys.stdout.fileno())
      sys.stderr = stream
      sys.stdout = stream

    sys.argv = [""]
    if flags.FLAGS.verbose:
      sys.argv.append("--verbose")

    if flags.FLAGS.debug:
      sys.argv.append("--debug")

    suites = flags.FLAGS.tests or test_lib.GRRBaseTest.classes

    if len(suites) != 1:
      raise ValueError("Only a single test is supported in single "
                       "processing mode, but %i were specified" % len(suites))

    test_suite = suites[0]
    print "Running test %s in single process mode" % test_suite
    sys.stdout.flush()
    RunTest(test_suite, stream=stream)

  else:
    processes = {}
    print "Running tests with labels %s" % ",".join(flags.FLAGS.labels)

    with utils.TempDirectory() as temp_dir:
      start = time.time()
      labels = set(flags.FLAGS.labels)

      skipped_tests = 0
      for name, cls in test_lib.GRRBaseTest.classes.items():
        if name.startswith("_"):
          continue

        if labels and not DoesTestHaveLabels(cls, labels):
          print "Skipping test %s due to labels" % name
          skipped_tests += 1
          continue

        if name in flags.FLAGS.exclude_tests:
          print "Skipping test %s" % name
          skipped_tests += 1
          continue

        result_filename = os.path.join(temp_dir, name)

        argv = [sys.executable] + sys.argv[:]
        if "--output" not in argv:
          argv.extend(["--output", result_filename])

        if flags.FLAGS.config:
          argv.extend(["--config", flags.FLAGS.config])

        argv.extend(["--tests", name])
        argv.extend(["--labels", ",".join(flags.FLAGS.labels)])

        # Maintain metadata about each test.
        processes[name] = dict(pipe=subprocess.Popen(argv),
                               start=time.time(),
                               output_path=result_filename,
                               test=name)

        max_processes = flags.FLAGS.processes
        if not max_processes:
          max_processes = max(psutil.cpu_count() - 1, 1)
        WaitForAvailableProcesses(processes,
                                  max_processes=max_processes,
                                  completion_cb=ReportTestResult)

      # Wait for all jobs to finish.
      WaitForAvailableProcesses(processes,
                                max_processes=0,
                                completion_cb=ReportTestResult)

      passed_tests = [p for p in processes.values() if p["exit_code"] == 0]
      failed_tests = [p for p in processes.values() if p["exit_code"] != 0]

      print("\nRan %s tests in %0.2f sec, %s tests passed, %s tests failed"
            ", %s skipped.") % (len(processes), time.time() - start,
                                len(passed_tests), len(failed_tests),
                                skipped_tests)

      if failed_tests:
        colorizer = Colorizer()

        print "Failing tests: "
        for metadata in failed_tests:
          print colorizer.Render("RED", metadata["test"])

        sys.exit(-1)


def DistEntry():
  """This is called from the package entry point."""
  flags.StartMain(main)


if __name__ == "__main__":
  DistEntry()
