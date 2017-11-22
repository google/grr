#!/usr/bin/env python
"""Prints test cases executed by the `pytest` test runner."""

import sys
import pytest

import sanity_checker_common


class StdoutRedirect(object):
  """Temporarily redirects all of the standard output somewhere else."""

  def __init__(self, replacement):
    self.replacement = replacement

  def __enter__(self):
    self.real_stdout = sys.stdout
    sys.stdout = self.replacement

  def __exit__(self, exc_type, exc_value, traceback):
    del exc_type  # Unused.
    del exc_value  # Unused.
    del traceback  # Unused.
    sys.stdout = self.real_stdout


class PytestTestCaseCollector(object):
  """Executes the `pytest` runner and collects executed test cases."""

  def __init__(self, args):
    self.args = args
    self.result = None

  def Execute(self):
    self.result = sanity_checker_common.CollectionResult()
    with StdoutRedirect(sys.stderr):
      pytest.main(self.args, plugins=[self])
    return self.result

  # pylint: disable=invalid-name
  def pytest_runtest_logreport(self, report):
    if report.when == "call":
      self.result.Append(report.outcome, report.nodeid)

  # pylint: enable=invalid-name


def main(argv):
  collector = PytestTestCaseCollector(argv[1:])
  collector.Execute().Dump()


if __name__ == "__main__":
  main(sys.argv)
