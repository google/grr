#!/usr/bin/env python
"""A module that configures the behaviour of pytest runner."""
from __future__ import absolute_import
from __future__ import division

import sys
import threading
import traceback


from absl import flags
import pytest

from grr.test_lib import testing_startup

FLAGS = flags.FLAGS

SKIP_BENCHMARK = pytest.mark.skip(
    reason="benchmark tests are executed only with --benchmark flag")

test_args = None


def pytest_cmdline_preparse(config, args):
  """A pytest hook that is called during command-line argument parsing."""
  del config  # Unused.

  try:
    separator = args.index("--")
  except ValueError:
    separator = len(args)

  global test_args
  test_args = args[separator + 1:]
  del args[separator:]


def pytest_cmdline_main(config):
  """A pytest hook that is called when the main function is executed."""
  del config  # Unused.
  sys.argv = ["pytest"] + test_args


last_module = None


def pytest_runtest_setup(item):
  """A pytest hook that is called before each test item is executed."""
  # We need to re-initialize flags (and hence also testing setup) because
  # various modules might have various flags defined.
  global last_module
  if last_module != item.module:
    FLAGS(sys.argv)
    testing_startup.TestInit()
  last_module = item.module


def pytest_addoption(parser):
  """A pytest hook that is called during the argument parser initialization."""
  parser.addoption(
      "-B",
      "--benchmark",
      dest="benchmark",
      default=False,
      action="store_true",
      help="run tests marked as benchmarks")

  parser.addoption(
      "--full_thread_trace",
      action="store_true",
      default=False,
      help="Include a full stacktrace for all thread in case of a thread leak.",
  )


def pytest_collection_modifyitems(session, config, items):
  """A pytest hook that is called when the test item collection is done."""
  del session  # Unused.

  benchmark = config.getoption("benchmark")
  for item in items:
    if not benchmark and item.get_marker("benchmark"):
      item.add_marker(SKIP_BENCHMARK)


def _generate_full_thread_trace():
  """Generates a full stack trace for all currently running threads."""
  threads = threading.enumerate()

  res = "Stacktrace for:\n"
  for thread in threads:
    res += "%s (id %d)\n" % (thread.name, thread.ident)

  res += "\n"

  frames = sys._current_frames()  # pylint: disable=protected-access
  for thread_id, stack in frames.items():
    res += "Thread ID: %s\n" % thread_id
    for filename, lineno, name, line in traceback.extract_stack(stack):
      res += "File: '%s', line %d, in %s\n" % (filename, lineno, name)
      if line:
        res += "  %s\n" % (line.strip())

  return res


last_test_name = None
known_leaks = []


@pytest.fixture(scope="function", autouse=True)
def thread_leak_check(request):
  """Makes sure that no threads are left running by any test."""
  threads = threading.enumerate()

  thread_names = [thread.name for thread in threads]

  allowed_thread_names = [
      "MainThread",

      # We start one thread per connector and let them run since there is a lot
      # of overhead involved.
      "ApiRegressionHttpConnectorV1",
      "ApiRegressionHttpConnectorV2",

      # Selenium takes long to set up, we clean up using an atexit handler.
      "SeleniumServerThread",

      # All these threads are constructed in setUpClass and destroyed in
      # tearDownClass so they are not real leaks.
      "api_e2e_server",
      "GRRHTTPServerTestThread",
      "SharedFDSTestThread",

      # Python specialty, sometimes it misreports threads using this name.
      "Dummy-1",
  ]

  # Remove up to one instance of each allowed thread name.
  for allowed_name in allowed_thread_names + known_leaks:
    if allowed_name in thread_names:
      thread_names.remove(allowed_name)

  current_test_name = request.node.name

  if thread_names:
    # Store any leaks so we only alert once about each leak.
    known_leaks.extend(thread_names)

    error_msg = ("Detected unexpected thread(s): %s. "
                 "Last test was %s, next test is %s." %
                 (thread_names, last_test_name, current_test_name))

    if request.config.getoption("full_thread_trace"):
      error_msg += "\n\n" + _generate_full_thread_trace()

    raise RuntimeError(error_msg)

  global last_test_name
  last_test_name = current_test_name
