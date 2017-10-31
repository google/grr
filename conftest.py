#!/usr/bin/env python
"""A module that configures the behaviour of pytest runner."""
import sys

from grr.lib import flags
from grr.test_lib import testing_startup

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


# FIXME(hanuszczak): This is a direct port of the way the current `run_tests.py`
# script works. `pytest` has a concept of markers which is a more idiomatic way
# of handlings this. The test suite should be ported to use markers and this
# custom labelling mechanism should be scrapped.
def pytest_addoption(parser):
  """A pytest hook that is called during the argument parser initialization."""
  parser.addoption(
      "-L",
      "--label",
      type=str,
      dest="labels",
      default=[],
      action="append",
      help="run tests only with specified labels")


def pytest_collection_modifyitems(session, config, items):
  """A pytest hook that is called when the test item collection is done."""
  del session  # Unused.
  filtered_items = []

  allowed_labels = set(config.getoption("labels") or ["small"])
  for item in items:
    item_labels = set(getattr(item.cls, "labels", ["small"]))
    if allowed_labels.intersection(item_labels):
      filtered_items.append(item)

  items[:] = filtered_items
