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


"""Compatibility mode.

This file defines a bunch of compatibility fixes to ensure we can run on older
versions of dependencies.
"""
import re
import unittest



def MonkeyPatch(cls, method_name, method):
  try:
    return getattr(cls, method_name)
  except AttributeError:
    setattr(cls, method_name, method)
    return method


# Fixup the protobuf implementation.
# pylint: disable=C6204
try:
  from google.protobuf import message

  # These are required to make protobufs pickle-able
  # pylint: disable=C6409
  def Message__getstate__(self):
    """Support the pickle protocol."""
    return dict(serialized=self.SerializePartialToString())

  def Message__setstate__(self, state):
    """Support the pickle protocol."""
    self.__init__()
    self.ParseFromString(state["serialized"])

  MonkeyPatch(message.Message, "__getstate__", Message__getstate__)
  MonkeyPatch(message.Message, "__setstate__", Message__setstate__)

except ImportError:
  pass


# Fix up python 2.6 unittest is missing some functions.
def assertItemsEqual(self, x, y):
  """This method is present in python 2.7 but is here for compatibility."""
  self.assertEqual(sorted(x), sorted(y))


def assertListEqual(self, x, y):
  self.assertItemsEqual(x, y)


def assertIsInstance(self, got_object, expected_class, msg=""):
  """Checks that got_object is an instance of expected_class or sub-class."""
  if not isinstance(got_object, expected_class):
    self.fail("%r is not an instance of %r. %s" % (got_object,
                                                   expected_class, msg))


def assertRaisesRegexp(self, expected_exception, expected_regexp,
                       callable_obj=None, *args, **kwargs):
  if isinstance(expected_regexp, basestring):
    expected_regexp = re.compile(expected_regexp)

  try:
    callable_obj(*args, **kwargs)
  except Exception, e:
    if expected_regexp.search(str(e)):
      return True

  self.fail("Regex not matched")


MonkeyPatch(unittest.TestCase, "assertItemsEqual", assertItemsEqual)
MonkeyPatch(unittest.TestCase, "assertListEqual", assertListEqual)
MonkeyPatch(unittest.TestCase, "assertIsInstance", assertIsInstance)
MonkeyPatch(unittest.TestCase, "assertRaisesRegexp", assertRaisesRegexp)
