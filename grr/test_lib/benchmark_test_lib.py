#!/usr/bin/env python
"""Classes for benchmarking-related tests."""

import logging
import time
import pytest

from grr.lib import registry
from grr.test_lib import test_lib


@pytest.mark.large
class MicroBenchmarks(test_lib.GRRBaseTest):
  """This base class created the GRR benchmarks."""
  __metaclass__ = registry.MetaclassRegistry

  units = "us"

  def setUp(self, extra_fields=None, extra_format=None):
    super(MicroBenchmarks, self).setUp()

    if extra_fields is None:
      extra_fields = []
    if extra_format is None:
      extra_format = []

    base_scratchpad_fields = ["Benchmark", "Time (%s)", "Iterations"]
    scratchpad_fields = base_scratchpad_fields + extra_fields
    # Create format string for displaying benchmark results.
    initial_fmt = ["45", "<20", "<20"] + extra_format
    self.scratchpad_fmt = " ".join([("{%d:%s}" % (ind, x))
                                    for ind, x in enumerate(initial_fmt)])
    # We use this to store temporary benchmark results.
    self.scratchpad = [
        scratchpad_fields, ["-" * len(x) for x in scratchpad_fields]
    ]

  def tearDown(self):
    super(MicroBenchmarks, self).tearDown()
    f = 1
    if self.units == "us":
      f = 1e6
    elif self.units == "ms":
      f = 1e3
    if len(self.scratchpad) > 2:
      print "\nRunning benchmark %s: %s" % (self._testMethodName,
                                            self._testMethodDoc or "")

      for row in self.scratchpad:
        if isinstance(row[1], (int, float)):
          row[1] = "%10.4f" % (row[1] * f)
        elif "%" in row[1]:
          row[1] %= self.units

        print self.scratchpad_fmt.format(*row)
      print

  def AddResult(self, name, time_taken, repetitions, *extra_values):
    logging.info("%s: %s (%s)", name, time_taken, repetitions)
    self.scratchpad.append([name, time_taken, repetitions] + list(extra_values))


class AverageMicroBenchmarks(MicroBenchmarks):
  """A MicroBenchmark subclass for tests that need to compute averages."""

  # Increase this for more accurate timing information.
  REPEATS = 1000
  units = "s"

  def setUp(self):
    super(AverageMicroBenchmarks, self).setUp(["Value"])

  def TimeIt(self, callback, name=None, repetitions=None, pre=None, **kwargs):
    """Runs the callback repetitively and returns the average time."""
    if repetitions is None:
      repetitions = self.REPEATS

    if name is None:
      name = callback.__name__

    if pre is not None:
      pre()

    start = time.time()
    for _ in xrange(repetitions):
      return_value = callback(**kwargs)

    time_taken = (time.time() - start) / repetitions
    self.AddResult(name, time_taken, repetitions, return_value)
