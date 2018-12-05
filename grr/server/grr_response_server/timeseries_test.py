#!/usr/bin/env python
"""Tests for grr.lib.timeseries."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_server import timeseries
from grr.test_lib import test_lib


class TimeseriesTest(test_lib.GRRBaseTest):

  def makeSeries(self):
    s = timeseries.Timeseries()
    for i in range(1, 101):
      s.Append(i, (i + 5) * 10000)
    return s

  def testAppendFilterRange(self):
    s = self.makeSeries()
    self.assertLen(s.data, 100)
    self.assertEqual([1, 60000], s.data[0])
    self.assertEqual([100, 1050000], s.data[-1])

    s.FilterRange(100000, 200000)
    self.assertLen(s.data, 10)
    self.assertEqual([5, 100000], s.data[0])
    self.assertEqual([14, 190000], s.data[-1])

  def testNormalize(self):
    s = self.makeSeries()
    s.Normalize(10 * 10000, 100000, 600000)
    self.assertLen(s.data, 5)
    self.assertEqual([9.5, 100000], s.data[0])
    self.assertEqual([49.5, 500000], s.data[-1])

    s = timeseries.Timeseries()
    for i in range(0, 1000):
      s.Append(0.5, i * 10)
    s.Normalize(200, 5000, 10000)
    self.assertLen(s.data, 25)
    self.assertListEqual(s.data[0], [0.5, 5000])
    self.assertListEqual(s.data[24], [0.5, 9800])

    s = timeseries.Timeseries()
    for i in range(0, 1000):
      s.Append(i, i * 10)
    s.Normalize(200, 5000, 10000, mode=timeseries.NORMALIZE_MODE_COUNTER)
    self.assertLen(s.data, 25)
    self.assertListEqual(s.data[0], [519, 5000])
    self.assertListEqual(s.data[24], [999, 9800])

  def testToDeltas(self):
    s = self.makeSeries()
    self.assertLen(s.data, 100)
    s.ToDeltas()
    self.assertLen(s.data, 99)
    self.assertEqual([1, 60000], s.data[0])
    self.assertEqual([1, 1040000], s.data[-1])

    s = timeseries.Timeseries()
    for i in range(0, 1000):
      s.Append(i, i * 1e6)
    s.Normalize(
        20 * 1e6, 500 * 1e6, 1000 * 1e6, mode=timeseries.NORMALIZE_MODE_COUNTER)
    self.assertLen(s.data, 25)
    self.assertListEqual(s.data[0], [519, int(500 * 1e6)])
    s.ToDeltas()
    self.assertLen(s.data, 24)
    self.assertListEqual(s.data[0], [20, int(500 * 1e6)])
    self.assertListEqual(s.data[23], [20, int(960 * 1e6)])

  def testNormalizeFillsGapsWithNone(self):
    s = timeseries.Timeseries()
    for i in range(21, 51):
      s.Append(i, (i + 5) * 10000)
    for i in range(81, 101):
      s.Append(i, (i + 5) * 10000)
    s.Normalize(10 * 10000, 10 * 10000, 120 * 10000)
    self.assertLen(s.data, 11)
    self.assertEqual([None, 100000], s.data[0])
    self.assertEqual([22.5, 200000], s.data[1])
    self.assertEqual([None, 600000], s.data[5])
    self.assertEqual([None, 1100000], s.data[-1])

  def testMakeIncreasing(self):
    s = timeseries.Timeseries()
    for i in range(0, 5):
      s.Append(i, i * 1000)
    for i in range(0, 5):
      s.Append(i, (i + 6) * 1000)
    self.assertLen(s.data, 10)
    self.assertEqual([4, 10000], s.data[-1])
    s.MakeIncreasing()
    self.assertLen(s.data, 10)
    self.assertEqual([8, 10000], s.data[-1])

  def testAddRescale(self):
    s1 = timeseries.Timeseries()
    for i in range(0, 5):
      s1.Append(i, i * 1000)
    s2 = timeseries.Timeseries()
    for i in range(0, 5):
      s2.Append(2 * i, i * 1000)
    s1.Add(s2)

    for i in range(0, 5):
      self.assertEqual(3 * i, s1.data[i][0])

    s1.Rescale(1 / 3.0)
    for i in range(0, 5):
      self.assertEqual(i, s1.data[i][0])

  def testMean(self):
    s = timeseries.Timeseries()
    self.assertEqual(None, s.Mean())

    s = self.makeSeries()
    self.assertLen(s.data, 100)
    self.assertEqual(50, s.Mean())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
