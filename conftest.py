#!/usr/bin/env python
"""A module that configures the behaviour of pytest runner."""

import os
import sys
import threading
import traceback

from absl import flags
import pytest

from grr_response_core.lib.util import compatibility
# pylint: disable=g-import-not-at-top
try:
  # This depends on grr_response_server, which is NOT available on all
  # (especially non-Linux development) platforms.
  from grr.test_lib import testing_startup
except ModuleNotFoundError:
  testing_startup = None
# pylint: enable=g-import-not-at-top

FLAGS = flags.FLAGS

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

  if "PYTEST_XDIST_WORKER" in os.environ:
    # If ran concurrently using pytest-xdist (`-n` cli flag), mainargv is the
    # result of the execution of pytest_cmdline_main in the main process.
    sys.argv = config.workerinput["mainargv"]
  else:
    # TODO: `sys.argv` on Python 2 uses `bytes` to represent passed
    # arguments.
    sys.argv = [compatibility.NativeStr("pytest")] + test_args


last_module = None


def pytest_runtest_setup(item):
  """A pytest hook that is called before each test item is executed."""
  # We need to re-initialize flags (and hence also testing setup) because
  # various modules might have various flags defined.
  global last_module
  if last_module != item.module:
    FLAGS(sys.argv)
    if testing_startup:
      testing_startup.TestInit()
  last_module = item.module


def pytest_addoption(parser):
  """A pytest hook that is called during the argument parser initialization."""
  parser.addoption(
      "--full_thread_trace",
      action="store_true",
      default=False,
      help="Include a full stacktrace for all thread in case of a thread leak.",
  )


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
  global last_test_name

  threads = threading.enumerate()

  # Quoting Python docs (https://docs.python.org/3/library/threading.html):
  # threading.current_thread():
  # Return the current Thread object, corresponding to the caller's thread
  # of control. If the caller's thread of control was not created through
  # the threading module, a dummy thread object with limited functionality
  # is returned.
  #
  # Quoting Python source
  # (https://github.com/python/cpython/blob/2a16eea71f56c2d8f38c295c8ce71a9a9a140aff/Lib/threading.py#L1269):
  # Dummy thread class to represent threads not started here.
  # These aren't garbage collected when they die, nor can they be waited for.
  # If they invoke anything in threading.py that calls current_thread(), they
  # leave an entry in the _active dict forever after.
  # Their purpose is to return *something* from current_thread().
  # They are marked as daemon threads so we won't wait for them
  # when we exit (conform previous semantics).
  #
  # See
  # https://stackoverflow.com/questions/55778365/what-is-dummy-in-threading-current-thread
  # for additional context.
  #
  # Dummy threads are named "Dummy-*" and are never deleted, since it's
  # impossible to detect the termination of alien threads, hence we have to
  # ignore them.
  thread_names = [
      thread.name for thread in threads if not thread.name.startswith("Dummy-")
  ]

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
      "api_integration_server",
      "ApiSslServerTest",
      "GRRHTTPServerTestThread",
      "SharedMemDBTestThread",

      # These threads seem to need to be allowed to run tests. Sample
      # %contentroot%/grr/server/grr_response_server/output_plugins/elasticsearch_plugin_test.py --no-header --no-summary -q in %contentroot%\grr\server\grr_response_server\output_plugins
      'pydevd.Writer',
      'pydevd.Reader',
      'pydevd.CommandThread',
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

  last_test_name = current_test_name
