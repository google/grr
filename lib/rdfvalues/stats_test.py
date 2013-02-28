#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Test for RunningStats class."""



import math

from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base


class RunningStatsTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RunningStats

  def GenerateSample(self, number=0):
    value = rdfvalue.RunningStats()
    value.RegisterValue(number)
    value.RegisterValue(number * 2)
    return value

  def testMeanIsCalculatedCorrectly(self):
    stats = rdfvalue.RunningStats()
    values = range(100)

    for v in values:
      stats.RegisterValue(v)

    # Compare calculated mean with a precalculated value.
    self.assertTrue(math.fabs(stats.mean - 49.5) < 1e-7)

  def testStdDevIsCalculatedCorrectly(self):
    stats = rdfvalue.RunningStats()
    values = range(100)

    for v in values:
      stats.RegisterValue(v)

    # Compare calculated standard deviation with a precalculated value.
    self.assertTrue(math.fabs(stats.std - 28.86607004) < 1e-7)

  def testHistogramIsCalculatedCorrectly(self):
    stats = rdfvalue.RunningStats()
    stats.histogram = rdfvalue.StatsHistogram(initializer=[2.0, 4.0, 10.0])

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
    self.assertEquals(stats.histogram.bins[0].num, 2)

    self.assertAlmostEquals(stats.histogram.bins[1].range_max_value, 4.0)
    self.assertEquals(stats.histogram.bins[1].num, 3)

    self.assertAlmostEquals(stats.histogram.bins[2].range_max_value, 10.0)
    self.assertEquals(stats.histogram.bins[2].num, 4)
