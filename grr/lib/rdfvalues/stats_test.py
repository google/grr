#!/usr/bin/env python
"""Test for RunningStats class."""


import math

from grr.lib import flags
from grr.lib.rdfvalues import stats as stats_rdf
from grr.lib.rdfvalues import test_base
from grr.test_lib import test_lib


class RunningStatsTest(test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = stats_rdf.RunningStats

  def GenerateSample(self, number=0):
    value = stats_rdf.RunningStats()
    value.RegisterValue(number)
    value.RegisterValue(number * 2)
    value.histogram = stats_rdf.StatsHistogram.FromBins([2.0, number, 10.0])
    return value

  def testMeanIsCalculatedCorrectly(self):
    stats = stats_rdf.RunningStats()
    values = range(100)

    for v in values:
      stats.RegisterValue(v)

    # Compare calculated mean with a precalculated value.
    self.assertTrue(math.fabs(stats.mean - 49.5) < 1e-7)

  def testStdDevIsCalculatedCorrectly(self):
    stats = stats_rdf.RunningStats()
    values = range(100)

    for v in values:
      stats.RegisterValue(v)

    # Compare calculated standard deviation with a precalculated value.
    self.assertTrue(math.fabs(stats.std - 28.86607004) < 1e-7)

  def testHistogramIsCalculatedCorrectly(self):
    stats = stats_rdf.RunningStats()
    stats.histogram = stats_rdf.StatsHistogram.FromBins([2.0, 4.0, 10.0])

    stats.RegisterValue(1.0)
    stats.RegisterValue(1.0)

    stats.RegisterValue(2.0)
    stats.RegisterValue(2.1)
    stats.RegisterValue(2.2)

    stats.RegisterValue(8.0)
    stats.RegisterValue(9.0)
    stats.RegisterValue(10.0)
    stats.RegisterValue(11.0)

    self.assertAlmostEquals(stats.histogram.bins[0].range_max_value, 2.0)
    self.assertEqual(stats.histogram.bins[0].num, 2)

    self.assertAlmostEquals(stats.histogram.bins[1].range_max_value, 4.0)
    self.assertEqual(stats.histogram.bins[1].num, 3)

    self.assertAlmostEquals(stats.histogram.bins[2].range_max_value, 10.0)
    self.assertEqual(stats.histogram.bins[2].num, 4)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
