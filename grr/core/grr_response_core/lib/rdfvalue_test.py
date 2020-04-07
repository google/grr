#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Tests for utility classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import sys
import unittest

from absl import app
from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr.test_lib import test_lib

long_string = (
    "迎欢迎\n"
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Morbi luctus "
    "ex sed dictum volutpat. Integer maximus, mauris at tincidunt iaculis, "
    "felis magna scelerisque ex, in scelerisque est odio non nunc. "
    "Suspendisse et lobortis augue. Donec faucibus tempor massa, sed dapibus"
    " erat iaculis ut. Vestibulum eu elementum nulla. Nullam scelerisque "
    "hendrerit lorem. Integer vitae semper metus. Suspendisse accumsan "
    "dictum felis. Etiam viverra, felis sed ullamcorper vehicula, libero "
    "nisl tempus dui, a porta lacus erat et erat. Morbi mattis elementum "
    "efficitur. Pellentesque aliquam placerat mauris non accumsan.")


class RDFValueTest(absltest.TestCase):
  """RDFValue tests."""

  def testStr(self):
    """Test RDFValue.__str__."""
    self.assertEqual(str(rdfvalue.RDFInteger(1)), "1")
    self.assertEqual(str(rdfvalue.RDFString(long_string)), long_string)

  # TODO(hanuszczak): Current implementation of `repr` for RDF values is broken
  # and not in line with Python guidelines. For example, `repr` should be
  # unambiguous whereas current implementation will trim long representations
  # with `...`. Moreover, the representation for most types is questionable at
  # best.
  #
  # The implementation should be fixed and proper tests should be written.


class RDFBytesTest(absltest.TestCase):

  def testFromHumanReadable(self):
    string = u"zażółć gęślą jaźń"

    result = rdfvalue.RDFBytes.FromHumanReadable(string)
    expected = rdfvalue.RDFBytes.FromSerializedBytes(string.encode("utf-8"))
    self.assertEqual(result, expected)


class RDFStringTest(absltest.TestCase):

  def testFromHumanReadable(self):
    string = u"pchnąć w tę łódź jeża lub ośm skrzyń fig"

    result = rdfvalue.RDFString.FromHumanReadable(string)
    self.assertEqual(str(result), string)

  def testEqualWithBytes(self):
    self.assertEqual(rdfvalue.RDFString(u"foo"), b"foo")
    self.assertNotEqual(rdfvalue.RDFString(u"foo"), b"\x80\x81\x82")

  def testLessThanWithBytes(self):
    self.assertLess(rdfvalue.RDFString(u"abc"), b"def")
    self.assertGreater(rdfvalue.RDFString(u"xyz"), b"ghi")
    self.assertLess(rdfvalue.RDFString(u"012"), b"\x80\x81\x81")

  # TODO: Python on Windows ships with UCS-2 by default, which does
  # not properly support unicode.
  @unittest.skipIf(
      sys.maxunicode <= 65535,
      "Your Python installation does not properly support Unicode (likely: "
      "Python with no UCS4 support on Windows.")
  def testLenOfEmoji(self):
    self.assertLen(rdfvalue.RDFString("🚀🚀"), 2)


class RDFIntegerTest(absltest.TestCase):

  def testFromHumanReadable(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"42")
    self.assertEqual(result, rdfvalue.RDFInteger(42))

  def testFromHumanReadablePositive(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"+108")
    self.assertEqual(result, rdfvalue.RDFInteger(108))

  def testFromHumanReadableNegative(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"-1337")
    self.assertEqual(result, rdfvalue.RDFInteger(-1337))

  def testFromHumanReadableZero(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"0")
    self.assertEqual(result, rdfvalue.RDFInteger(0))

  def testFromHumanReadableRaisesOnNonInteger(self):
    with self.assertRaises(ValueError):
      rdfvalue.RDFInteger.FromHumanReadable(u"12.3")

  def testFromHumanReadableRaisesOnNonDecimal(self):
    with self.assertRaises(ValueError):
      rdfvalue.RDFInteger.FromHumanReadable(u"12A")


class RDFDateTimeTest(absltest.TestCase):

  def testLerpMiddle(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")
    end_time = start_time + rdfvalue.Duration.From(10, rdfvalue.DAYS)
    lerped_time = rdfvalue.RDFDatetime.Lerp(
        0.5, start_time=start_time, end_time=end_time)
    self.assertEqual(lerped_time,
                     start_time + rdfvalue.Duration.From(5, rdfvalue.DAYS))

  def testLerpZero(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01")
    end_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")
    lerped_time = rdfvalue.RDFDatetime.Lerp(
        0.0, start_time=start_time, end_time=end_time)
    self.assertEqual(lerped_time, start_time)

  def testLerpOne(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01")
    end_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")
    lerped_time = rdfvalue.RDFDatetime.Lerp(
        1.0, start_time=start_time, end_time=end_time)
    self.assertEqual(lerped_time, end_time)

  def testLerpQuarter(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01")
    end_time = start_time + rdfvalue.Duration.From(4, rdfvalue.DAYS)
    lerped_time = rdfvalue.RDFDatetime.Lerp(
        0.25, start_time=start_time, end_time=end_time)
    self.assertEqual(lerped_time,
                     start_time + rdfvalue.Duration.From(1, rdfvalue.DAYS))

  def testLerpRaisesTypeErrorIfTimesAreNotRDFDatetime(self):
    now = rdfvalue.RDFDatetime.Now()

    with self.assertRaisesRegex(TypeError, "non-datetime"):
      rdfvalue.RDFDatetime.Lerp(0.0, start_time=10, end_time=now)

    with self.assertRaisesRegex(TypeError, "non-datetime"):
      rdfvalue.RDFDatetime.Lerp(
          0.0,
          start_time=now,
          end_time=rdfvalue.Duration.From(1, rdfvalue.DAYS))

  def testLerpRaisesValueErrorIfProgressIsNotNormalized(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")
    end_time = rdfvalue.RDFDatetime.FromHumanReadable("2011-01-01")

    with self.assertRaises(ValueError):
      rdfvalue.RDFDatetime.Lerp(1.5, start_time=start_time, end_time=end_time)

    with self.assertRaises(ValueError):
      rdfvalue.RDFDatetime.Lerp(-0.5, start_time=start_time, end_time=end_time)

  def testFloorToMinutes(self):
    dt = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34:56")
    expected = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34")
    self.assertEqual(
        dt.Floor(rdfvalue.Duration.From(60, rdfvalue.SECONDS)), expected)

  def testFloorToHours(self):
    dt = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34")
    expected = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:00")
    self.assertEqual(
        dt.Floor(rdfvalue.Duration.From(1, rdfvalue.HOURS)), expected)

  def testFloorToDays(self):
    dt = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34")
    expected = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11")
    self.assertEqual(
        dt.Floor(rdfvalue.Duration.From(1, rdfvalue.DAYS)), expected)

  def testFloorExact(self):
    dt = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34:56")
    self.assertEqual(dt.Floor(rdfvalue.Duration.From(1, rdfvalue.SECONDS)), dt)


class RDFDatetimeSecondsTest(absltest.TestCase):

  def testFromDatetime_withMicroSeconds(self):
    dt_with_micros = datetime.datetime(2000, 1, 1, microsecond=5000)
    dt = datetime.datetime(2000, 1, 1)
    self.assertEqual(
        rdfvalue.RDFDatetimeSeconds.FromDatetime(dt_with_micros),
        rdfvalue.RDFDatetimeSeconds.FromDatetime(dt))

  def testBug122716179(self):
    d = rdfvalue.RDFDatetimeSeconds.FromSecondsSinceEpoch(1)
    self.assertEqual(d.AsMicrosecondsSinceEpoch(), 1000000)
    diff = rdfvalue.RDFDatetimeSeconds(10) - rdfvalue.Duration("3s")
    self.assertEqual(diff.AsMicrosecondsSinceEpoch(), 7000000)


class DurationSecondsTest(absltest.TestCase):

  def testPublicAttributes(self):
    duration = rdfvalue.DurationSeconds.FromHumanReadable("1h")
    self.assertEqual(duration.ToInt(rdfvalue.SECONDS), 3600)
    self.assertEqual(duration.ToInt(rdfvalue.MILLISECONDS), 3600 * 1000)
    self.assertEqual(duration.microseconds, 3600 * 1000 * 1000)

  def testFromDays(self):
    self.assertEqual(
        rdfvalue.DurationSeconds.From(2, rdfvalue.DAYS),
        rdfvalue.DurationSeconds.FromHumanReadable("2d"))
    self.assertEqual(
        rdfvalue.DurationSeconds.From(31, rdfvalue.DAYS),
        rdfvalue.DurationSeconds.FromHumanReadable("31d"))

  def testFromHours(self):
    self.assertEqual(
        rdfvalue.DurationSeconds.From(48, rdfvalue.HOURS),
        rdfvalue.DurationSeconds.FromHumanReadable("48h"))
    self.assertEqual(
        rdfvalue.DurationSeconds.From(24, rdfvalue.HOURS),
        rdfvalue.DurationSeconds.FromHumanReadable("24h"))

  def testFromSeconds(self):
    self.assertEqual(
        rdfvalue.DurationSeconds.From(1337,
                                      rdfvalue.SECONDS).ToInt(rdfvalue.SECONDS),
        1337)

  def testFromMicroseconds(self):
    duration = rdfvalue.DurationSeconds.From(3000000, rdfvalue.MICROSECONDS)
    self.assertEqual(duration.microseconds, 3000000)
    self.assertEqual(duration.ToInt(rdfvalue.SECONDS), 3)

  def testFloatConstructorRaises(self):
    with self.assertRaises(TypeError):
      rdfvalue.DurationSeconds(3.14)

  def testSerializeToBytes(self):
    self.assertEqual(
        b"0",
        rdfvalue.DurationSeconds.From(0, rdfvalue.WEEKS).SerializeToBytes())
    self.assertEqual(
        b"1",
        rdfvalue.DurationSeconds.From(1, rdfvalue.SECONDS).SerializeToBytes())
    self.assertEqual(
        b"2",
        rdfvalue.DurationSeconds.From(2, rdfvalue.SECONDS).SerializeToBytes())
    self.assertEqual(
        b"999",
        rdfvalue.DurationSeconds.From(999, rdfvalue.SECONDS).SerializeToBytes())
    self.assertEqual(
        b"1000",
        rdfvalue.DurationSeconds.From(1000,
                                      rdfvalue.SECONDS).SerializeToBytes())

  def testFromWireFormat(self):
    for i in [0, 7, 1337]:
      val = rdfvalue.DurationSeconds.FromWireFormat(i)
      self.assertEqual(i, val.ToInt(rdfvalue.SECONDS))

      val2 = rdfvalue.DurationSeconds.FromWireFormat(
          val.SerializeToWireFormat())
      self.assertEqual(val, val2)


MAX_UINT64 = 18446744073709551615


class DurationTest(absltest.TestCase):

  def testInitializationFromMicroseconds(self):
    for i in [0, 1, 7, 60, 1337, MAX_UINT64]:
      val = rdfvalue.Duration.From(i, rdfvalue.MICROSECONDS)
      self.assertEqual(i, val.microseconds)
      self.assertEqual(val,
                       rdfvalue.Duration.FromHumanReadable("{} us".format(i)))
      self.assertEqual(val, rdfvalue.Duration(i))

  def testInitializationFromMilliseconds(self):
    for i in [0, 1, 7, 60, 1337, MAX_UINT64 // 1000]:
      val = rdfvalue.Duration.From(i, rdfvalue.MILLISECONDS)
      self.assertEqual(i * 1000, val.microseconds)
      self.assertEqual(val,
                       rdfvalue.Duration.FromHumanReadable("{} ms".format(i)))

  def testInitializationFromSeconds(self):
    for i in [0, 1, 7, 60, 1337, MAX_UINT64 // 1000000]:
      val = rdfvalue.Duration.From(i, rdfvalue.SECONDS)
      self.assertEqual(i * 1000000, val.microseconds)
      self.assertEqual(val,
                       rdfvalue.Duration.FromHumanReadable("{} s".format(i)))

  def testInitializationFromMinutes(self):
    for i in [0, 1, 7, 60, 1337, MAX_UINT64 // 60000000]:
      val = rdfvalue.Duration.From(i, rdfvalue.MINUTES)
      self.assertEqual(i * 60000000, val.microseconds)
      self.assertEqual(val,
                       rdfvalue.Duration.FromHumanReadable("{} m".format(i)))

  def testInitializationFromHours(self):
    for i in [0, 1, 7, 60, 1337, MAX_UINT64 // 3600000000]:
      val = rdfvalue.Duration.From(i, rdfvalue.HOURS)
      self.assertEqual(i * 3600000000, val.microseconds)
      self.assertEqual(val,
                       rdfvalue.Duration.FromHumanReadable("{} h".format(i)))

  def testInitializationFromDays(self):
    for i in [0, 1, 7, 60, 1337, MAX_UINT64 // 86400000000]:
      val = rdfvalue.Duration.From(i, rdfvalue.DAYS)
      self.assertEqual(i * 86400000000, val.microseconds)
      self.assertEqual(val,
                       rdfvalue.Duration.FromHumanReadable("{} d".format(i)))

  def testInitializationFromWeeks(self):
    for i in [0, 1, 7, 60, 1337, MAX_UINT64 // 604800000000]:
      val = rdfvalue.Duration.From(i, rdfvalue.WEEKS)
      self.assertEqual(i * 604800000000, val.microseconds)
      self.assertEqual(val,
                       rdfvalue.Duration.FromHumanReadable("{} w".format(i)))

  def testConversionToInt(self):
    for i in [0, 1, 7, 60, 1337, 12345, 123456, 1234567, MAX_UINT64]:
      val = rdfvalue.Duration.From(i, rdfvalue.MICROSECONDS)
      self.assertEqual(val.ToInt(rdfvalue.MICROSECONDS), i)
      self.assertEqual(val.ToInt(rdfvalue.MILLISECONDS), i // 1000)
      self.assertEqual(val.ToInt(rdfvalue.SECONDS), i // (1000 * 1000))
      self.assertEqual(val.ToInt(rdfvalue.MINUTES), i // (60 * 1000 * 1000))
      self.assertEqual(val.ToInt(rdfvalue.HOURS), i // (60 * 60 * 1000 * 1000))
      self.assertEqual(
          val.ToInt(rdfvalue.DAYS), i // (24 * 60 * 60 * 1000 * 1000))
      self.assertEqual(
          val.ToInt(rdfvalue.WEEKS), i // (7 * 24 * 60 * 60 * 1000 * 1000))

  def testConversionToFractional(self):
    for i in [0, 1, 7, 60, 1337, 12345, 123456, 1234567, MAX_UINT64]:
      val = rdfvalue.Duration.From(i, rdfvalue.MICROSECONDS)
      self.assertAlmostEqual(val.ToFractional(rdfvalue.MICROSECONDS), i)
      self.assertAlmostEqual(val.ToFractional(rdfvalue.MILLISECONDS), i / 1000)
      self.assertAlmostEqual(
          val.ToFractional(rdfvalue.SECONDS), i / (1000 * 1000))
      self.assertAlmostEqual(
          val.ToFractional(rdfvalue.MINUTES), i / (60 * 1000 * 1000))
      self.assertAlmostEqual(
          val.ToFractional(rdfvalue.HOURS), i / (60 * 60 * 1000 * 1000))
      self.assertAlmostEqual(
          val.ToFractional(rdfvalue.DAYS), i / (24 * 60 * 60 * 1000 * 1000))
      self.assertAlmostEqual(
          val.ToFractional(rdfvalue.WEEKS),
          i / (7 * 24 * 60 * 60 * 1000 * 1000))

  def testStringDeserialization(self):
    for i in [0, 1, 7, 60, 1337, 12345, 123456, 1234567, MAX_UINT64]:
      val = rdfvalue.Duration.From(i, rdfvalue.MICROSECONDS)
      self.assertEqual(
          rdfvalue.Duration.FromSerializedBytes(val.SerializeToBytes()), val)

  def testHumanReadableStringSerialization(self):
    self.assertEqual("0 us", str(rdfvalue.Duration.From(0, rdfvalue.WEEKS)))
    self.assertEqual("1 us",
                     str(rdfvalue.Duration.From(1, rdfvalue.MICROSECONDS)))
    self.assertEqual("2 us",
                     str(rdfvalue.Duration.From(2, rdfvalue.MICROSECONDS)))
    self.assertEqual("999 us",
                     str(rdfvalue.Duration.From(999, rdfvalue.MICROSECONDS)))
    self.assertEqual("1 ms",
                     str(rdfvalue.Duration.From(1000, rdfvalue.MICROSECONDS)))
    self.assertEqual("1 ms",
                     str(rdfvalue.Duration.From(1, rdfvalue.MILLISECONDS)))
    self.assertEqual(
        "{} us".format(MAX_UINT64),
        str(rdfvalue.Duration.From(MAX_UINT64, rdfvalue.MICROSECONDS)))
    self.assertEqual("3 s", str(rdfvalue.Duration.From(3, rdfvalue.SECONDS)))
    self.assertEqual("3 m", str(rdfvalue.Duration.From(3, rdfvalue.MINUTES)))
    self.assertEqual("3 h", str(rdfvalue.Duration.From(3, rdfvalue.HOURS)))
    self.assertEqual("3 d", str(rdfvalue.Duration.From(3, rdfvalue.DAYS)))
    self.assertEqual("3 w", str(rdfvalue.Duration.From(21, rdfvalue.DAYS)))

  def testSerializeToBytes(self):
    self.assertEqual(
        b"0",
        rdfvalue.Duration.From(0, rdfvalue.WEEKS).SerializeToBytes())
    self.assertEqual(
        b"1",
        rdfvalue.Duration.From(1, rdfvalue.MICROSECONDS).SerializeToBytes())
    self.assertEqual(
        b"2",
        rdfvalue.Duration.From(2, rdfvalue.MICROSECONDS).SerializeToBytes())
    self.assertEqual(
        b"999",
        rdfvalue.Duration.From(999, rdfvalue.MICROSECONDS).SerializeToBytes())
    self.assertEqual(
        b"1000",
        rdfvalue.Duration.From(1000, rdfvalue.MICROSECONDS).SerializeToBytes())
    self.assertEqual(
        str(MAX_UINT64).encode("utf-8"),
        rdfvalue.Duration.From(MAX_UINT64,
                               rdfvalue.MICROSECONDS).SerializeToBytes())
    self.assertEqual(
        b"3000000",
        rdfvalue.Duration.From(3, rdfvalue.SECONDS).SerializeToBytes())

  def testAdditionOfDurationsIsEqualToIntegerAddition(self):
    for a in [0, 1, 7, 60, 1337, MAX_UINT64 // 2]:
      for b in [0, 1, 7, 60, 1337, MAX_UINT64 // 2]:
        self.assertEqual(
            rdfvalue.Duration(a) + rdfvalue.Duration(b),
            rdfvalue.Duration(a + b))

  def testSubtractionOfDurationsIsEqualToIntegerSubtraction(self):
    for a in [0, 1, 7, 60, 1337, MAX_UINT64]:
      for b in [0, 1, 7, 60, 1337, MAX_UINT64]:
        self.assertEqual(
            rdfvalue.Duration(a) - rdfvalue.Duration(min(a, b)),
            rdfvalue.Duration(a - min(a, b)))

  def testFromWireFormat(self):
    for i in [0, 7, 1337, MAX_UINT64]:
      val = rdfvalue.Duration.FromWireFormat(i)
      self.assertEqual(i, val.microseconds)

  def testSubtractionFromDateTimeIsEqualToIntegerSubtraction(self):
    for a in [0, 1, 7, 60, 1337]:
      for b in [0, 1, 7, 60, 1337]:
        lhs = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(a)
        rhs = rdfvalue.Duration(min(a, b))
        result = lhs - rhs
        self.assertEqual(result.AsMicrosecondsSinceEpoch(), a - min(a, b))

  def testAdditionToDateTimeIsEqualToIntegerAddition(self):
    for a in [0, 1, 7, 60, 1337]:
      for b in [0, 1, 7, 60, 1337]:
        lhs = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(a)
        rhs = rdfvalue.Duration(b)
        result = lhs + rhs
        self.assertEqual(result.AsMicrosecondsSinceEpoch(), a + b)

  def testComparisonIsEqualToIntegerComparison(self):
    for a in [0, 1, 7, 60, 1337, MAX_UINT64 - 1, MAX_UINT64]:
      for b in [0, 1, 7, 60, 1337, MAX_UINT64 - 1, MAX_UINT64]:
        dur_a = rdfvalue.Duration(a)
        dur_b = rdfvalue.Duration(b)
        if a > b:
          self.assertGreater(dur_a, dur_b)
        if a >= b:
          self.assertGreaterEqual(dur_a, dur_b)
        if a == b:
          self.assertEqual(dur_a, dur_b)
        if a <= b:
          self.assertLessEqual(dur_a, dur_b)
        if a < b:
          self.assertLess(dur_a, dur_b)
        if a != b:
          self.assertNotEqual(dur_a, dur_b)


class DocTest(test_lib.DocTest):
  module = rdfvalue


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
