#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2012 Google Inc. All Rights Reserved.

"""Basic rdfvalue tests."""


import time

from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base


class RDFBytesTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFBytes

  def GenerateSample(self, number=0):
    return rdfvalue.RDFBytes("\x00hello%s\x01" % number)


class RDFStringTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFString

  def GenerateSample(self, number=0):
    return rdfvalue.RDFString(u"Grüezi %s" % number)

  def testRDFStringGetItem(self):
    rdfstring = rdfvalue.RDFString("123456789")
    self.assertEqual(rdfstring[3], "4")
    self.assertEqual(rdfstring[-3:], "789")
    self.assertEqual(rdfstring[3:-3], "456")


class RDFIntegerTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFInteger

  def GenerateSample(self, number=0):
    return rdfvalue.RDFInteger(number)

  def testComparableToPrimiviteInts(self):
    self.assertEqual(rdfvalue.RDFInteger(10), 10)
    self.assertTrue(rdfvalue.RDFInteger(10) > 5)
    self.assertTrue(15 > rdfvalue.RDFInteger(10))
    self.assertTrue(rdfvalue.RDFInteger(10) < 15)
    self.assertTrue(5 < rdfvalue.RDFInteger(10))

  def testDividesAndIsDividableByPrimitiveInts(self):
    self.assertEqual(rdfvalue.RDFInteger(10) / 5, 2)
    self.assertEqual(100 / rdfvalue.RDFInteger(10), 10)

  def testMultipliesAndIsMultipliedByByPrimitive(self):
    self.assertEqual(rdfvalue.RDFInteger(10) * 10, 100)
    self.assertEqual(10 * rdfvalue.RDFInteger(10), 100)

  def testUsableInBitwiseOr(self):
    def TestOr(val1, val2, expected):
      self.assertEqual(rdfvalue.RDFInteger(val1) | val2, expected)
      self.assertEqual(val1 | rdfvalue.RDFInteger(val2), expected)

      value = rdfvalue.RDFInteger(val1)
      value |= val2
      self.assertEqual(value, expected)

      value = val1
      value |= rdfvalue.RDFInteger(val2)
      self.assertEqual(value, expected)

    TestOr(True, False, True)
    TestOr(False, True, True)
    TestOr(False, False, False)
    TestOr(True, True, True)

  def testUsableInBitwiseAnd(self):
    def TestAnd(val1, val2, expected):
      self.assertEqual(rdfvalue.RDFInteger(val1) & val2, expected)
      self.assertEqual(val1 & rdfvalue.RDFInteger(val2), expected)

      value = rdfvalue.RDFInteger(val1)
      value &= val2
      self.assertEqual(value, expected)

      value = val1
      value &= rdfvalue.RDFInteger(val2)
      self.assertEqual(value, expected)

    TestAnd(True, False, False)
    TestAnd(False, True, False)
    TestAnd(False, False, False)
    TestAnd(True, True, True)


class RDFBoolTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFBool

  def GenerateSample(self, number=0):
    return rdfvalue.RDFBool(number % 2)

  def testComparableToPrimitiveBooleans(self):
    self.assertEqual(rdfvalue.RDFBool(True), True)
    self.assertNotEqual(rdfvalue.RDFBool(True), False)
    self.assertEqual(rdfvalue.RDFBool(False), False)
    self.assertNotEqual(rdfvalue.RDFBool(False), True)

  def testUsableInBitwiseOr(self):
    def TestOr(val1, val2, expected):
      self.assertEqual(rdfvalue.RDFBool(val1) | val2, expected)
      self.assertEqual(val1 | rdfvalue.RDFBool(val2), expected)

      value = rdfvalue.RDFBool(val1)
      value |= val2
      self.assertEqual(value, expected)

      value = val1
      value |= rdfvalue.RDFBool(val2)
      self.assertEqual(value, expected)

    TestOr(True, False, True)
    TestOr(False, True, True)
    TestOr(False, False, False)
    TestOr(True, True, True)

  def testUsableInBitwiseAnd(self):
    def TestAnd(val1, val2, expected):
      self.assertEqual(rdfvalue.RDFBool(val1) & val2, expected)
      self.assertEqual(val1 & rdfvalue.RDFBool(val2), expected)

      value = rdfvalue.RDFBool(val1)
      value &= val2
      self.assertEqual(value, expected)

      value = val1
      value &= rdfvalue.RDFBool(val2)
      self.assertEqual(value, expected)

    TestAnd(True, False, False)
    TestAnd(False, True, False)
    TestAnd(False, False, False)
    TestAnd(True, True, True)


class DurationTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.Duration

  def GenerateSample(self, number=5):
    return rdfvalue.Duration("%ds" % number)

  def testStringRepresentationIsTransitive(self):
    t = rdfvalue.Duration("5m")
    self.assertEqual(t.seconds, 300)
    self.assertEqual(t, rdfvalue.Duration(300))
    self.assertEqual(str(t), "5m")

  def testMulNumber(self):
    t = rdfvalue.Duration("5m")
    t2 = t * 3
    self.assertEqual(t2.seconds, 300 * 3)
    t2 = t * 1000.23
    self.assertEqual(t2.seconds, int(300 * 1000.23))
    t2 = t * (-10)
    self.assertEqual(t2.seconds, int(300 * (-10)))

    # Test rmul
    t2 = 3 * t
    self.assertEqual(t2.seconds, 300 * 3)
    t2 = 1000.23 * t
    self.assertEqual(t2.seconds, int(300 * 1000.23))
    t2 = (-10) * t
    self.assertEqual(t2.seconds, int(300 * (-10)))


class ByteSizeTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.ByteSize

  def GenerateSample(self, number=5):
    return rdfvalue.ByteSize("%sKib" % number)

  def testParsing(self):
    for string, expected in [("100gb", 100 * 1000 ** 3),
                             ("10kib", 10 * 1024),
                             ("2.5kb", 2500)]:
      self.assertEqual(expected, rdfvalue.ByteSize(string))


class RDFURNTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFURN

  def GenerateSample(self, number=0):
    return rdfvalue.RDFURN("aff4:/C.12342%s/fs/os/" % number)

  def testRDFURN(self):
    """Test RDFURN handling."""
    # Make a url object
    str_url = "aff4:/hunts/W:AAAAAAAA/Results"
    url = rdfvalue.RDFURN(str_url, age=1)
    self.assertEqual(url.age, 1)
    self.assertEqual(url.Path(), "/hunts/W:AAAAAAAA/Results")
    self.assertEqual(url._urn.netloc, "")
    self.assertEqual(url._urn.scheme, "aff4")

    # Test the Add() function
    url = url.Add("some", age=2).Add("path", age=3)
    self.assertEqual(url.age, 3)
    self.assertEqual(url.Path(), "/hunts/W:AAAAAAAA/Results/some/path")
    self.assertEqual(url._urn.netloc, "")
    self.assertEqual(url._urn.scheme, "aff4")

    # Test that we can handle urns with a '?' and do not interpret them as
    # a delimiter between url and parameter list.
    str_url = "aff4:/C.0000000000000000/fs/os/c/regex.*?]&[+{}--"
    url = rdfvalue.RDFURN(str_url, age=1)
    self.assertEqual(url.Path(), str_url[5:])

  def testInitialization(self):
    """Check that we can initialize from common initializers."""

    # Empty Initializer not allowed.
    self.assertRaises(ValueError, self.rdfvalue_class)

    # Initialize from another instance.
    sample = self.GenerateSample("aff4:/")

    self.CheckRDFValue(self.rdfvalue_class(sample), sample)

  def testSerialization(self, sample=None):
    sample = self.GenerateSample("aff4:/")
    super(RDFURNTest, self).testSerialization(sample=sample)


class RDFDatetimeTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFDatetime

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class()
    result.ParseFromHumanReadable("2011/11/%02d" % (number + 1))
    return result

  def testTimeZoneConversions(self):
    time_string = "2011-11-01 10:23:00"

    # Human readable strings are assumed to always be in UTC
    # timezone. Initialize from the human readable string.
    date1 = rdfvalue.RDFDatetime().ParseFromHumanReadable(time_string)

    self.assertEqual(int(date1), 1320142980000000)

    self.assertEqual(
        time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(date1) / 1e6)),
        time_string)

    # We always stringify the date in UTC timezone.
    self.assertEqual(str(date1), time_string)

  def testInitFromEmptyString(self):
    orig_time = time.time
    time.time = lambda: 1000
    try:
      # Init from an empty string should generate a DateTime object with a zero
      # time.
      date = rdfvalue.RDFDatetime("")
      self.assertEqual(int(date), 0)

      self.assertEqual(int(date.Now()), int(1000 * 1e6))

    finally:
      time.time = orig_time

  def testAddNumber(self):
    date = rdfvalue.RDFDatetime(1e9)
    self.assertEqual(int(date + 60), 1e9 + 60e6)
    self.assertEqual(int(date + 1000.23), 1e9 + 1000230e3)
    self.assertEqual(int(date + (-10)), 1e9 - 10e6)

  def testMulNumber(self):
    date = rdfvalue.RDFDatetime(1e9)
    self.assertEqual(int(date * 3), 1e9 * 3)
    self.assertEqual(int(date * 1000.23), int(1e9 * 1000.23))
    self.assertEqual(int(date * (-10)), int(1e9 * (-10)))

    # Test rmul
    self.assertEqual(int(3 * date), 1e9 * 3)
    self.assertEqual(int(1000.23 * date), int(1e9 * 1000.23))
    self.assertEqual(int((-10) * date), int(1e9 * (-10)))

  def testSubNumber(self):
    date = rdfvalue.RDFDatetime(1e9)
    self.assertEqual(int(date - 60), 1e9 - 60e6)
    self.assertEqual(int(date - (-1000.23)), 1e9 + 1000230e3)
    self.assertEqual(int(date - 1e12), 1e9 - 1e18)

  def testIAddNumber(self):
    date = rdfvalue.RDFDatetime(1e9)
    date += 60
    self.assertEqual(date, 1e9 + 60e6)

    date = rdfvalue.RDFDatetime(1e9)
    date += 1000.23
    self.assertEqual(date, 1e9 + 1000230e3)

    date = rdfvalue.RDFDatetime(1e9)
    date += -10
    self.assertEqual(date, 1e9 - 10e6)

  def testISubNumber(self):
    date = rdfvalue.RDFDatetime(1e9)
    date -= 60
    self.assertEqual(date, 1e9 - 60e6)

    date = rdfvalue.RDFDatetime(1e9)
    date -= -1000.23
    self.assertEqual(date, 1e9 + 1000230e3)

    date = rdfvalue.RDFDatetime(1e9)
    date -= 1e12
    self.assertEqual(date, 1e9 - 1e18)

  def testAddDuration(self):
    duration = rdfvalue.Duration("12h")
    date = rdfvalue.RDFDatetime(1e9)
    self.assertEqual(int(date + duration), 1e9 + 12 * 3600e6)
    duration = rdfvalue.Duration("-60s")
    self.assertEqual(int(date + duration), 1e9 - 60e6)

  def testSubDuration(self):
    duration = rdfvalue.Duration("5m")
    date = rdfvalue.RDFDatetime(1e9)
    self.assertEqual(int(date - duration), 1e9 - 5 * 60e6)
    duration = rdfvalue.Duration("-60s")
    self.assertEqual(int(date - duration), 1e9 + 60e6)
    duration = rdfvalue.Duration("1w")
    self.assertEqual(int(date - duration), 1e9 - 7 * 24 * 3600e6)

  def testIAddDuration(self):
    date = rdfvalue.RDFDatetime(1e9)
    date += rdfvalue.Duration("12h")
    self.assertEqual(date, 1e9 + 12 * 3600e6)

    date = rdfvalue.RDFDatetime(1e9)
    date += rdfvalue.Duration("-60s")
    self.assertEqual(date, 1e9 - 60e6)

  def testISubDuration(self):
    date = rdfvalue.RDFDatetime(1e9)
    date -= rdfvalue.Duration("5m")
    self.assertEqual(date, 1e9 - 5 * 60e6)

    date = rdfvalue.RDFDatetime(1e9)
    date -= rdfvalue.Duration("-60s")
    self.assertEqual(date, 1e9 + 60e6)

    date = rdfvalue.RDFDatetime(1e9)
    date -= rdfvalue.Duration("1w")
    self.assertEqual(date, 1e9 - 7 * 24 * 3600e6)


class RDFDatetimeSecondsTest(RDFDatetimeTest):
  rdfvalue_class = rdfvalue.RDFDatetimeSeconds


class HashDigestTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.HashDigest

  def GenerateSample(self, number=0):
    return rdfvalue.HashDigest("\xca\x97\x81\x12\xca\x1b\xbd\xca\xfa\xc21\xb3"
                               "\x9a#\xdcM\xa7\x86\xef\xf8\x14|Nr\xb9\x80w\x85"
                               "\xaf\xeeH\xbb%s" % number)

  def testEqNeq(self):
    binary_digest = ("\xca\x97\x81\x12\xca\x1b\xbd\xca\xfa\xc21\xb3"
                     "\x9a#\xdcM\xa7\x86\xef\xf8\x14|Nr\xb9\x80w\x85"
                     "\xaf\xeeH\xbb")
    sample = rdfvalue.HashDigest(binary_digest)
    hex_digest = ("ca978112ca1bbdcafac231b39a23dc4da786eff81"
                  "47c4e72b9807785afee48bb")
    self.assertEqual(sample, hex_digest)
    self.assertEqual(sample, binary_digest)
    self.assertNotEqual(sample, "\xaa\xbb")
    self.assertNotEqual(sample, "deadbeef")
