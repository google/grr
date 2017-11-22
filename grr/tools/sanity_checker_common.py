#!/usr/bin/env python
"""Classes and functions common for all test sanity checkers."""

from __future__ import print_function


class CollectionResult(object):
  """Result of the runner execution (collected test cases)."""

  def __init__(self):
    self.passed = []
    self.skipped = []
    self.failed = []

  def Append(self, kind, entry):
    getattr(self, kind).append(entry)

  def Dump(self):
    self._DumpKind("passed")
    self._DumpKind("skipped")
    self._DumpKind("failed")

  def _DumpKind(self, kind):
    print("%s:" % kind.upper())
    for entry in sorted(getattr(self, kind)):
      print(entry)
    print("")
