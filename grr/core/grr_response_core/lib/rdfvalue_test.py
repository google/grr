#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for utility classes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys
import unittest


from absl import app
from absl.testing import absltest
from future.builtins import int
from future.builtins import str

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
    self.assertEqual(str(rdfvalue.RDFBool(True)), "1")
    self.assertEqual(str(rdfvalue.RDFString(long_string)), long_string)

  # TODO(hanuszczak): Current implementation of `repr` for RDF values is broken
  # and not in line with Python guidelines. For example, `repr` should be
  # unambiguous whereas current implementation will trim long representations
  # with `...`. Moreover, the representation for most types is questionable at
  # best (true booleans as presented as `<RDFBool('1')>`).
  #
  # The implementation should be fixed and proper tests should be written.


class RDFBytesTest(absltest.TestCase):

  def testParseFromHumanReadable(self):
    string = u"zażółć gęślą jaźń"

    result = rdfvalue.RDFBytes.FromHumanReadable(string)
    expected = rdfvalue.RDFBytes.FromSerializedString(string.encode("utf-8"))
    self.assertEqual(result, expected)


class RDFStringTest(absltest.TestCase):

  def testParseFromHumanReadable(self):
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

  def testParseFromHumanReadable(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"42")
    self.assertEqual(result, rdfvalue.RDFInteger(42))

  def testParseFromHumanReadablePositive(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"+108")
    self.assertEqual(result, rdfvalue.RDFInteger(108))

  def testParseFromHumanReadableNegative(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"-1337")
    self.assertEqual(result, rdfvalue.RDFInteger(-1337))

  def testParseFromHumanReadableZero(self):
    result = rdfvalue.RDFInteger.FromHumanReadable(u"0")
    self.assertEqual(result, rdfvalue.RDFInteger(0))

  def testParseFromHumanReadableRaisesOnNonInteger(self):
    with self.assertRaises(ValueError):
      rdfvalue.RDFInteger.FromHumanReadable(u"12.3")

  def testParseFromHumanReadableRaisesOnNonDecimal(self):
    with self.assertRaises(ValueError):
      rdfvalue.RDFInteger.FromHumanReadable(u"12A")


class RDFBool(absltest.TestCase):

  def testParseFromHumanReadableTrue(self):
    self.assertTrue(rdfvalue.RDFBool.FromHumanReadable(u"true"))
    self.assertTrue(rdfvalue.RDFBool.FromHumanReadable(u"True"))
    self.assertTrue(rdfvalue.RDFBool.FromHumanReadable(u"TRUE"))
    self.assertTrue(rdfvalue.RDFBool.FromHumanReadable(u"1"))

  def testParseFromHumanReadableFalse(self):
    self.assertFalse(rdfvalue.RDFBool.FromHumanReadable(u"false"))
    self.assertFalse(rdfvalue.RDFBool.FromHumanReadable(u"False"))
    self.assertFalse(rdfvalue.RDFBool.FromHumanReadable(u"FALSE"))
    self.assertFalse(rdfvalue.RDFBool.FromHumanReadable(u"0"))

  def testParseFromHumanReadableRaisesOnIncorrectInteger(self):
    with self.assertRaises(ValueError):
      rdfvalue.RDFBool.FromHumanReadable(u"2")

  def testParseFromHumanReadableRaisesOnWeirdInput(self):
    with self.assertRaises(ValueError):
      rdfvalue.RDFBool.FromHumanReadable(u"yes")


class RDFDateTimeTest(absltest.TestCase):

  def testLerpMiddle(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")
    end_time = start_time + rdfvalue.Duration("10d")
    lerped_time = rdfvalue.RDFDatetime.Lerp(
        0.5, start_time=start_time, end_time=end_time)
    self.assertEqual(lerped_time, start_time + rdfvalue.Duration("5d"))

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
    end_time = start_time + rdfvalue.Duration("4d")
    lerped_time = rdfvalue.RDFDatetime.Lerp(
        0.25, start_time=start_time, end_time=end_time)
    self.assertEqual(lerped_time, start_time + rdfvalue.Duration("1d"))

  def testLerpRaisesTypeErrorIfTimesAreNotRDFDatetime(self):
    now = rdfvalue.RDFDatetime.Now()

    with self.assertRaisesRegexp(TypeError, "non-datetime"):
      rdfvalue.RDFDatetime.Lerp(0.0, start_time=10, end_time=now)

    with self.assertRaisesRegexp(TypeError, "non-datetime"):
      rdfvalue.RDFDatetime.Lerp(
          0.0, start_time=now, end_time=rdfvalue.Duration("1d"))

  def testLerpRaisesValueErrorIfProgressIsNotNormalized(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2010-01-01")
    end_time = rdfvalue.RDFDatetime.FromHumanReadable("2011-01-01")

    with self.assertRaises(ValueError):
      rdfvalue.RDFDatetime.Lerp(1.5, start_time=start_time, end_time=end_time)

    with self.assertRaises(ValueError):
      rdfvalue.RDFDatetime.Lerp(-0.5, start_time=start_time, end_time=end_time)

  def testFloorToMinutes(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34:56")
    expected = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34")
    self.assertEqual(datetime.Floor(rdfvalue.Duration("60s")), expected)

  def testFloorToHours(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34")
    expected = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:00")
    self.assertEqual(datetime.Floor(rdfvalue.Duration("1h")), expected)

  def testFloorToDays(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34")
    expected = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11")
    self.assertEqual(datetime.Floor(rdfvalue.Duration("1d")), expected)

  def testFloorExact(self):
    datetime = rdfvalue.RDFDatetime.FromHumanReadable("2011-11-11 12:34:56")
    self.assertEqual(datetime.Floor(rdfvalue.Duration("1s")), datetime)


class DurationTest(absltest.TestCase):

  def testPublicAttributes(self):
    duration = rdfvalue.Duration("1h")
    self.assertEqual(duration.seconds, 3600)
    self.assertEqual(duration.milliseconds, 3600 * 1000)
    self.assertEqual(duration.microseconds, 3600 * 1000 * 1000)

  def testFromHours(self):
    self.assertEqual(rdfvalue.Duration.FromDays(2), rdfvalue.Duration("2d"))
    self.assertEqual(rdfvalue.Duration.FromDays(31), rdfvalue.Duration("31d"))

  def testFromDays(self):
    self.assertEqual(rdfvalue.Duration.FromHours(48), rdfvalue.Duration("48h"))
    self.assertEqual(rdfvalue.Duration.FromHours(24), rdfvalue.Duration("24h"))

  def testFromSeconds(self):
    self.assertEqual(rdfvalue.Duration.FromSeconds(1337).seconds, 1337)

  def testFromMicroseconds(self):
    duration = rdfvalue.Duration.FromMicroseconds(3000000)
    self.assertEqual(duration.microseconds, 3000000)
    self.assertEqual(duration.seconds, 3)

    # In general `int(•)` should not be used—one should use unit conversion
    # functions instead. However, API value renderers currently use that logic
    # so we verify that the call actually return an `int`.
    self.assertIsInstance(int(duration), int)

  def testFloatConstructorRaises(self):
    with self.assertRaises(TypeError):
      rdfvalue.Duration(3.14)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
