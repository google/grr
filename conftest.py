#!/usr/bin/env python
"""A module that configures the behaviour of pytest runner."""
import sys

import pytest

from grr.core.grr_response_core.lib import flags
from grr.test_lib import testing_startup

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
    flags.Initialize()
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


def pytest_collection_modifyitems(session, config, items):
  """A pytest hook that is called when the test item collection is done."""
  del session  # Unused.

  benchmark = config.getoption("benchmark")
  for item in items:
    if not benchmark and item.get_marker("benchmark"):
      item.add_marker(SKIP_BENCHMARK)
