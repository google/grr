#!/usr/bin/env python
# -*- coding: utf-8 -*-
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


class RDFURNTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFURN

  def GenerateSample(self, number=0):
    return rdfvalue.RDFURN("aff4:/C.12342%s/fs/os/" % number)

  def testRDFURN(self):
    """Test RDFURN handling."""
    # Make a url object
    str_url = "http://www.google.com/"
    url = rdfvalue.RDFURN(str_url, age=1)
    self.assertEqual(url.age, 1)
    self.assertEqual(url.Path(), "/")
    self.assertEqual(url._urn.netloc, "www.google.com")
    self.assertEqual(url._urn.scheme, "http")

    # Test the Add() function
    url = url.Add("some", age=2).Add("path", age=3)
    self.assertEqual(url.age, 3)
    self.assertEqual(url.Path(), "/some/path")
    self.assertEqual(url._urn.netloc, "www.google.com")
    self.assertEqual(url._urn.scheme, "http")


class RDFDatetimeTest(test_base.RDFValueTestCase):
  rdfvalue_class = rdfvalue.RDFDatetime

  def GenerateSample(self, number=0):
    return self.rdfvalue_class("2011/11/%02d" % (number+1))

  def testTimeZoneConversions(self):
    time_string = "2011-11-01 10:23:00"

    # Human readable strings are assumed to always be in UTC
    # timezone. Initialize from the human readable string.
    date1 = rdfvalue.RDFDatetime(time_string)

    self.assertEqual(int(date1), 1320142980000000)

    self.assertEqual(
        time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(date1) / 1e6)),
        time_string)

    # We always stringify the date in UTC timezone.
    self.assertEqual(str(date1), time_string)


class RDFDatetimeSecondsTest(RDFDatetimeTest):
  rdfvalue_class = rdfvalue.RDFDatetimeSeconds
