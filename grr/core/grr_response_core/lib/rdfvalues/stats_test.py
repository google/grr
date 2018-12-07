#!/usr/bin/env python
"""Test for RunningStats class."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr.test_lib import test_lib


class RunningStatsTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdf_stats.RunningStats

  def GenerateSample(self, number=0):
    value = rdf_stats.RunningStats()
    value.RegisterValue(number)
    value.RegisterValue(number * 2)
    value.histogram = rdf_stats.StatsHistogram.FromBins([2.0, number, 10.0])
    return value

  def testMeanIsCalculatedCorrectly(self):
    stats = rdf_stats.RunningStats()
    values = range(100)

    for v in values:
      stats.RegisterValue(v)

    # Compare calculated mean with a precalculated value.
    self.assertAlmostEqual(stats.mean, 49.5)

  def testStdDevIsCalculatedCorrectly(self):
    stats = rdf_stats.RunningStats()
    values = range(100)

    for v in values:
      stats.RegisterValue(v)

    # Compare calculated standard deviation with a precalculated value.
    self.assertAlmostEqual(stats.std, 28.86607004)

  def testHistogramIsCalculatedCorrectly(self):
    stats = rdf_stats.RunningStats()
    stats.histogram = rdf_stats.StatsHistogram.FromBins([2.0, 4.0, 10.0])

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
