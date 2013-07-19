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


class RDFIntegerTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFInteger

  def GenerateSample(self, number=0):
    return rdfvalue.RDFInteger(number)


class DurationTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.Duration

  def GenerateSample(self, number=5):
    return rdfvalue.Duration("%ds" % number)

  def testStringRepresentationIsTransitive(self):
    t = rdfvalue.Duration("5m")
    self.assertEqual(t.seconds, 300)
    self.assertEqual(t, rdfvalue.Duration(300))
    self.assertEqual(str(t), "5m")


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


class RDFDatetimeTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFDatetime

  def GenerateSample(self, number=0):
    result = self.rdfvalue_class()
    result.ParseFromHumanReadable("2011/11/%02d" % (number+1))
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


class RDFDatetimeSecondsTest(RDFDatetimeTest):
  rdfvalue_class = rdfvalue.RDFDatetimeSeconds
