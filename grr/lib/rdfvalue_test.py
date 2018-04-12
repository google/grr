#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for utility classes."""


import unittest
from grr.lib import flags
from grr.lib import rdfvalue
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


class RDFValueTest(unittest.TestCase):
  """RDFValue tests."""

  def testStr(self):
    """Test RDFValue.__str__."""
    self.assertEqual(str(rdfvalue.RDFBool(True)), "1")
    self.assertEqual(str(rdfvalue.RDFString(long_string)), long_string)

  def testRepr(self):
    """Test RDFValue.__repr__."""
    self.assertEqual(repr(rdfvalue.RDFBool(True)), "<RDFBool('1')>")
    self.assertEqual(
        repr(rdfvalue.RDFString(long_string)),
        "<RDFString('\\xe8\\xbf\\x8e\\xe6\\xac\\xa2\\xe8\\xbf\\x8e\\nLorem "
        "ipsum dolor sit amet, consectetur adipiscing elit. Morbi luctus ex "
        "sed dictum volutp...')>")


class RDFDateTimeTest(unittest.TestCase):

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


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
