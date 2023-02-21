#!/usr/bin/env python
"""Basic rdfvalue tests."""

import datetime
import time

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr.test_lib import test_lib


class RDFBytesTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.RDFBytes

  def GenerateSample(self, number=0):
    return rdfvalue.RDFBytes(b"\x00hello%s\x01" % str(number).encode("ascii"))


class RDFStringTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.RDFString

  def GenerateSample(self, number=0):
    return rdfvalue.RDFString(u"Grüezi %s" % number)

  def testRDFStringGetItem(self):
    rdfstring = rdfvalue.RDFString("123456789")
    self.assertEqual(rdfstring[3], "4")
    self.assertEqual(rdfstring[-3:], "789")
    self.assertEqual(rdfstring[3:-3], "456")


class RDFIntegerTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.RDFInteger

  def GenerateSample(self, number=0):
    return rdfvalue.RDFInteger(number)

  def testComparableToPrimiviteInts(self):
    self.assertEqual(rdfvalue.RDFInteger(10), 10)
    self.assertGreater(rdfvalue.RDFInteger(10), 5)
    self.assertGreater(15, rdfvalue.RDFInteger(10))
    self.assertLess(rdfvalue.RDFInteger(10), 15)
    self.assertLess(5, rdfvalue.RDFInteger(10))

  def testDividesAndIsDividableByPrimitiveInts(self):
    self.assertEqual(rdfvalue.RDFInteger(10) // 5, 2)

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


class DurationSecondsTest(rdf_test_base.RDFValueTestMixin,
                          test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.DurationSeconds

  def GenerateSample(self, number=5):
    return rdfvalue.DurationSeconds("%ds" % number)

  def testStringRepresentationIsTransitive(self):
    t = rdfvalue.DurationSeconds("5 m")
    self.assertEqual(t.ToInt(rdfvalue.SECONDS), 300)
    self.assertEqual(t, rdfvalue.DurationSeconds(300))
    self.assertEqual(str(t), "5 m")

  def testMulNumber(self):
    t = rdfvalue.DurationSeconds("5m")
    t2 = t * 3
    self.assertEqual(t2.ToInt(rdfvalue.SECONDS), 300 * 3)

    # Test rmul
    t2 = 3 * t
    self.assertEqual(t2.ToInt(rdfvalue.SECONDS), 300 * 3)

  def testHashability(self):
    pass  # DurationSeconds does not need to be hashable.


class ByteSizeTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.ByteSize

  def GenerateSample(self, number=5):
    return rdfvalue.ByteSize("%sKib" % number)

  def testParsing(self):
    cases = [
        ("100gb", 100 * 1000**3),
        ("10kib", 10 * 1024),
        ("2.5kb", 2500),
        ("3.25MiB", 3.25 * 1024**2),
        ("3.25 MiB", 3.25 * 1024**2),
        ("12B", 12),
        ("12 B", 12),
    ]

    for string, expected in cases:
      self.assertEqual(expected, rdfvalue.ByteSize(string))


class RDFURNTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.RDFURN

  def GenerateSample(self, number=0):
    return rdfvalue.RDFURN("aff4:/C.12342%s/fs/os/" % number)

  def testRDFURN(self):
    """Test RDFURN handling."""
    # Make a url object
    str_url = "aff4:/hunts/W:AAAAAAAA/Results"
    url = rdfvalue.RDFURN(str_url)
    self.assertEqual(url.Path(), "/hunts/W:AAAAAAAA/Results")
    self.assertEqual(str(url), str_url)
    self.assertEqual(url.scheme, "aff4")

    # Test the Add() function
    url = url.Add("some").Add("path")
    self.assertEqual(url.Path(), "/hunts/W:AAAAAAAA/Results/some/path")
    self.assertEqual(str(url), utils.Join(str_url, "some", "path"))

    # Test that we can handle urns with a '?' and do not interpret them as
    # a delimiter between url and parameter list.
    str_url = "aff4:/C.0000000000000000/fs/os/c/regex.*?]&[+{}--"
    url = rdfvalue.RDFURN(str_url)
    self.assertEqual(url.Path(), str_url[5:])

    # Some more special characters...
    for path in ["aff4:/test/?#asd", "aff4:/test/#asd", "aff4:/test/?#"]:
      self.assertEqual(path, str(rdfvalue.RDFURN(path)))

  def testComparison(self):
    urn = rdfvalue.RDFURN("aff4:/abc/def")
    self.assertEqual(urn, str(urn))
    self.assertEqual(urn, "aff4:/abc/def")
    self.assertEqual(urn, "/abc/def")
    self.assertEqual(urn, "abc/def")

    self.assertNotEqual(urn, None)

    string_list = ["abc", "ghi", "def", "mno", "jkl"]
    urn_list = [rdfvalue.RDFURN(s) for s in string_list]

    self.assertEqual(string_list, urn_list)

    # Inequality.
    s = "some_urn"
    s2 = "some_other_urn"
    self.assertEqual(s, rdfvalue.RDFURN(s))
    self.assertFalse(s != rdfvalue.RDFURN(s))
    self.assertNotEqual(s, rdfvalue.RDFURN(s2))
    self.assertFalse(s == rdfvalue.RDFURN(s2))

  def testHashing(self):

    m = {}
    urn1 = rdfvalue.RDFURN("aff4:/test1")
    urn2 = rdfvalue.RDFURN("aff4:/test2")

    m[urn1] = 1
    self.assertIn(urn1, m)
    self.assertNotIn(urn2, m)

  def testInitialization(self):
    """Check that we can initialize from common initializers."""

    # Initialize from another instance.
    sample = self.GenerateSample("aff4:/")

    self.CheckRDFValue(self.rdfvalue_class(sample), sample)

  def testSerialization(self, sample=None):
    sample = self.GenerateSample("aff4:/")
    super().testSerialization(sample=sample)


class RDFDatetimeTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.RDFDatetime

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class.FromHumanReadable("2011/11/%02d" %
                                                   (number + 1))
    return result

  def testTimeZoneConversions(self):
    time_string = "2011-11-01 10:23:00"

    # Human readable strings are assumed to always be in UTC
    # timezone. Initialize from the human readable string.
    date1 = self.rdfvalue_class.FromHumanReadable(time_string)

    self.assertEqual(date1.AsMicrosecondsSinceEpoch(), 1320142980000000)

    self.assertEqual(
        time.strftime("%Y-%m-%d %H:%M:%S",
                      time.gmtime(date1.AsSecondsSinceEpoch())), time_string)

    # We always stringify the date in UTC timezone.
    self.assertEqual(str(date1), time_string)

  def testInitFromEmptyString(self):
    with test_lib.FakeTime(1000):
      # Init from an empty string should generate a DateTime object with a zero
      # time.
      date = self.rdfvalue_class.FromSerializedBytes(b"")
      self.assertEqual(int(date), 0)

      self.assertEqual(self.rdfvalue_class.Now().AsMicrosecondsSinceEpoch(),
                       int(1000 * 1e6))

  def testInitFromDatetimeObject(self):
    # Test initializing from a datetime object
    date = datetime.datetime(2015, 6, 17, 5, 22, 3)
    self.assertEqual(self.rdfvalue_class.FromDatetime(date).AsDatetime(), date)
    date = datetime.datetime.utcfromtimestamp(99999)
    self.assertEqual(
        self.rdfvalue_class.FromDatetime(date).AsSecondsSinceEpoch(), 99999)
    self.assertEqual(
        self.rdfvalue_class.FromDatetime(date).AsMicrosecondsSinceEpoch(),
        99999000000)
    # Test microsecond support
    date = datetime.datetime(1970, 1, 1, 0, 0, 0, 567)
    self.assertEqual(
        rdfvalue.RDFDatetime.FromDatetime(date).AsMicrosecondsSinceEpoch(), 567)

  def testInitFromDateObject(self):
    date = datetime.date(2018, 2, 1)
    self.assertEqual(
        self.rdfvalue_class.FromDate(date),
        self.rdfvalue_class.FromHumanReadable("2018-02-01 00:00:00"))

  def testAddNumber(self):
    date = rdfvalue.RDFDatetime(1e9)
    self.assertEqual(int(date + 60), 1e9 + 60e6)
    self.assertEqual(int(date + 1000.23), 1e9 + 1000230e3)
    self.assertEqual(int(date + (-10)), 1e9 - 10e6)

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
    duration = rdfvalue.Duration.FromHumanReadable("12h")
    date = self.rdfvalue_class.FromMicrosecondsSinceEpoch(int(1e9))
    self.assertEqual((date + duration).AsMicrosecondsSinceEpoch(),
                     1e9 + 12 * 3600e6)

  def testSubDuration(self):
    duration = rdfvalue.Duration.FromHumanReadable("5m")
    date = self.rdfvalue_class.FromMicrosecondsSinceEpoch(int(1e9))
    self.assertEqual((date - duration).AsMicrosecondsSinceEpoch(),
                     1e9 - 5 * 60e6)
    duration = rdfvalue.Duration.FromHumanReadable("1w")
    self.assertEqual((date - duration).AsMicrosecondsSinceEpoch(),
                     1e9 - 7 * 24 * 3600e6)

  def testIAddDuration(self):
    date = self.rdfvalue_class.FromMicrosecondsSinceEpoch(int(1e9))
    date += rdfvalue.Duration.FromHumanReadable("12h")
    self.assertEqual(date.AsMicrosecondsSinceEpoch(), 1e9 + 12 * 3600e6)

  def testISubDuration(self):
    date = self.rdfvalue_class.FromMicrosecondsSinceEpoch(int(1e9))
    date -= rdfvalue.Duration.FromHumanReadable("5m")
    self.assertEqual(date.AsMicrosecondsSinceEpoch(), 1e9 - 5 * 60e6)

    date = self.rdfvalue_class.FromMicrosecondsSinceEpoch(int(1e9))
    date -= rdfvalue.Duration.FromHumanReadable("1w")
    self.assertEqual(date.AsMicrosecondsSinceEpoch(), 1e9 - 7 * 24 * 3600e6)


class RDFDatetimeSecondsTest(RDFDatetimeTest):
  rdfvalue_class = rdfvalue.RDFDatetimeSeconds


class HashDigestTest(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  rdfvalue_class = rdfvalue.HashDigest

  def GenerateSample(self, number=0):
    return rdfvalue.HashDigest(b"\xca\x97\x81\x12\xca\x1b\xbd\xca\xfa\xc21\xb3"
                               b"\x9a#\xdcM\xa7\x86\xef\xf8\x14|Nr\xb9\x80w\x85"
                               b"\xaf\xeeH\xbb%s" % str(number).encode("ascii"))

  def testEqNeq(self):
    binary_digest = (b"\xca\x97\x81\x12\xca\x1b\xbd\xca\xfa\xc21\xb3"
                     b"\x9a#\xdcM\xa7\x86\xef\xf8\x14|Nr\xb9\x80w\x85"
                     b"\xaf\xeeH\xbb")
    sample = rdfvalue.HashDigest(binary_digest)
    hex_digest = ("ca978112ca1bbdcafac231b39a23dc4da786eff81"
                  "47c4e72b9807785afee48bb")
    self.assertEqual(str(sample), hex_digest)
    self.assertEqual(sample.SerializeToBytes(), binary_digest)
    self.assertNotEqual(sample.SerializeToBytes(), b"\xaa\xbb")
    self.assertNotEqual(str(sample), "deadbeef")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
