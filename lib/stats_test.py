#!/usr/bin/env python

# Copyright 2011 Google Inc.
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

"""Tests for the stats classes."""


import time


from grr.client import conf
import logging

from grr.lib import registry
from grr.lib import stats
from grr.lib import test_lib


class StatsTestInit(registry.InitHook):
  def __init__(self):
    stats.STATS.RegisterVar("test_counter")
    stats.STATS.RegisterVar("test_counter2")
    stats.STATS.RegisterMap("test_map", "time", bin_list=[0.1], precision=0)
    stats.STATS.RegisterMap("test_map2", "time", bin_list=[0.1], precision=0)
    stats.STATS.RegisterNAvg("test_navg", 10)
    stats.STATS.RegisterNAvg("test_navg2", 10)
    stats.STATS.RegisterVar("test_var")


class StatsTests(test_lib.GRRBaseTest):
  """Stats tests."""

  def Sleep(self, n):
    self.mock_time += n

  def setUp(self):
    self.mock_time = 100.0
    self.sleep_orig = time.sleep
    self.time_orig = time.time
    time.sleep = self.Sleep
    time.time = lambda: self.mock_time

  def tearDown(self):
    time.sleep = self.sleep_orig
    time.time = self.time_orig

  def CountErrors(self, *unused_args):
    self.errors_logged += 1

  def testBasics(self):
    """Test exported vars."""

    self.assertTrue(stats.STATS.IsRegistered("test_var"))

    stats.STATS.Set("test_var", 89)
    self.assertEqual(stats.STATS.Get("test_var"), 89)

    logging.error = self.CountErrors
    self.errors_logged = 0

    self.assertFalse(stats.STATS.IsRegistered("test_undefined"))
    stats.STATS.Set("test_undefined", 10)
    self.assertEqual(self.errors_logged, 1)

    self.assertEqual(stats.STATS.Get("test_undefined"), 0)

  @stats.Counted("test_counter")
  def CountedFunc(self):
    pass

  def testCountingDecorator(self):
    """Test function call counting."""
    old_counter = stats.STATS.Get("test_counter")

    for _ in range(10):
      self.CountedFunc()

    self.assertEqual(stats.STATS.Get("test_counter"), old_counter + 10)

  @stats.NAvgTimed("test_navg")
  def NAvgTimedFunc(self, n):
    self.Sleep(n)

  def testNAvgTimedDecorator(self):
    """Test timing decorators."""
    self.assertEqual(stats.STATS.Get("test_navg"), 0)
    self.NAvgTimedFunc(0.5)
    self.assertAlmostEqual(stats.STATS.Get("test_navg"), 0.5)

    for _ in range(9):
      self.NAvgTimedFunc(0)
    # Expected: 0.05
    self.assertAlmostEqual(stats.STATS.Get("test_navg"), 0.05)

    self.NAvgTimedFunc(0)
    # Now the 0.5 value should have been dropped
    self.assertAlmostEqual(stats.STATS.Get("test_navg"), 0.0)

  @stats.Timed("test_map")
  def TimedFunc1(self, n):
    self.Sleep(n)

  def testMaps(self):
    """Test binned timings."""
    m = stats.STATS.GetMap("test_map")
    self.assertEqual(m[">0.1"], 0)
    self.assertEqual(m[0.1], 0)

    for _ in range(3):
      self.TimedFunc1(0)

    self.assertEqual(m[">0.1"], 0)
    self.assertEqual(m[0.1], 3)

    self.TimedFunc1(0.11)

    self.assertEqual(m[">0.1"], 1)
    self.assertEqual(m[0.1], 3)

  @stats.Timed("test_map2")
  @stats.NAvgTimed("test_navg2")
  @stats.Counted("test_counter2")
  def OverdecoratedFunc(self, n):
    self.Sleep(n)

  def testCombiningDecorators(self):
    """Test combining decorators."""
    old_counter = stats.STATS.Get("test_counter2")
    old_avg = stats.STATS.Get("test_navg2")
    old_map = str(stats.STATS.GetMap("test_map2"))

    self.OverdecoratedFunc(0.02)

    # Check if all vars get updated
    self.assertEqual(old_counter + 1, stats.STATS.Get("test_counter2"))
    self.assertNotEqual(old_avg, stats.STATS.Get("test_navg2"))
    self.assertNotEqual(old_map, str(stats.STATS.Get("test_map2")))

  @stats.Timed("test_map2")
  @stats.NAvgTimed("test_navg2")
  @stats.Counted("test_counter2")
  def IRaise(self, n):
    self.Sleep(n)
    raise Exception()

  def testExceptionHandling(self):
    """Test decorators when exceptions are thrown."""
    old_counter = stats.STATS.Get("test_counter2")
    old_avg = stats.STATS.Get("test_navg2")
    old_map = str(stats.STATS.GetMap("test_map2"))

    self.assertRaises(Exception, self.IRaise, 0.03)

    # Check if all vars still get updated
    self.assertEqual(old_counter + 1, stats.STATS.Get("test_counter2"))
    self.assertNotEqual(old_avg, stats.STATS.Get("test_navg2"))
    self.assertNotEqual(old_map, str(stats.STATS.Get("test_map2")))

  @stats.NAvgTimed("test_multiple_timing")
  def Func1(self, n):
    self.Sleep(n)

  @stats.NAvgTimed("test_multiple_timing")
  def Func2(self, n):
    self.Sleep(n)

  @stats.Counted("test_multiple_count")
  def Func3(self, n):
    self.Sleep(n)

  @stats.Counted("test_multiple_count")
  def Func4(self, n):
    self.Sleep(n)

  @stats.Timed("test_multiple_map")
  def Func5(self, n):
    self.Sleep(n)

  @stats.Timed("test_multiple_map")
  def Func6(self, n):
    self.Sleep(n)

  def testMultipleFuncs(self):
    """Tests if multiple decorators produce aggregate stats."""

    stats.STATS.RegisterNAvg("test_multiple_timing", 10)

    self.Func1(0)
    self.Func2(0.1)
    # Avg should be around 0.05
    self.assertAlmostEqual(stats.STATS.Get("test_multiple_timing"), 0.05)

    stats.STATS.RegisterVar("test_multiple_count")

    self.Func3(0)
    self.Func4(0)

    self.assertEqual(stats.STATS.Get("test_multiple_count"), 2)

    stats.STATS.RegisterMap("test_multiple_map", "time",
                            bin_list=[0.1], precision=0)

    self.Func5(0)
    self.Func6(0)

    m = stats.STATS.GetMap("test_multiple_map")
    self.assertEqual(m[">0.1"], 0)
    self.assertEqual(m[0.1], 2)

  @stats.TimespanAvg("test_timespan_avg")
  def TimespanFunc1(self, n):
    time.sleep(n)

  @stats.TimespanAvg("test_timespan_avg_short")
  def TimespanFunc2(self, n):
    self.Sleep(n)

  def testTimespanAvg(self):
    """Tests the timespan average."""

    stats.STATS.RegisterTimespanAvg("test_timespan_avg", 20)
    stats.STATS.RegisterTimespanAvg("test_timespan_avg_short", 10)

    for _ in range(3):
      self.TimespanFunc1(2)
      self.TimespanFunc2(2)

    # After 12 seconds
    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg"), 2)
    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg_short"), 2)

    for _ in range(3):
      self.TimespanFunc1(1)
      self.TimespanFunc2(1)

    # After 18 Seconds
    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg"), 1.5)
    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg_short"), 1.25)

    for _ in range(3):
      self.TimespanFunc1(1)
      self.TimespanFunc2(1)

    # After 24 seconds
    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg"), 1.25)
    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg_short"), 1.0)

    self.Sleep(30)

    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg"), 0)
    self.assertEqual(stats.STATS.GetFunction("test_timespan_avg_short"), 0)

  def Exported(self):
    self.exported_call_count += 1
    return self.exported_call_count

  def testExportFunctions(self):
    """Tests if exporting functions directly works."""
    self.exported_call_count = 0

    stats.STATS.RegisterFunction("function_export_test", self.Exported)
    self.assertEqual(stats.STATS.GetFunction("function_export_test"), 1)
    self.assertEqual(stats.STATS.GetFunction("function_export_test"), 2)
    self.assertEqual(stats.STATS.GetFunction("function_export_test"), 3)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
