#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from absl.testing import absltest
from typing import Text

from grr_response_core.lib.util import yaml


class ParseTest(absltest.TestCase):

  def testSimpleDict(self):
    parsed = yaml.Parse("{ 'foo': 'bar', 'quux': 42 }")
    expected = {"foo": "bar", "quux": 42}
    self.assertEqual(parsed, expected)

  def testComplexDict(self):
    parsed = yaml.Parse("""
foo.bar:
  quux: [4, 8, 15, 16, 23, 42]
  thud:
  - blargh
  - norf
foo.baz:
  - 3.14
  - 1.62
    """)

    expected = {
        "foo.bar": {
            "quux": [4, 8, 15, 16, 23, 42],
            "thud": ["blargh", "norf"],
        },
        "foo.baz": [3.14, 1.62],
    }

    self.assertEqual(parsed, expected)

  def testUnicode(self):
    parsed = yaml.Parse("""
gęsi:
- zbożowa
- krótkodzioba
- białoczelna

grzebiące:
- jarząbek
- głuszec
- bażant
    """)

    expected = {
        "gęsi": ["zbożowa", "krótkodzioba", "białoczelna"],
        "grzebiące": ["jarząbek", "głuszec", "bażant"],
    }

    self.assertEqual(parsed, expected)

  def testUnicodeTags(self):
    parsed = yaml.Parse("""
!!python/unicode żółć: !!python/unicode jaźń
!!python/unicode kość: !!python/unicode łoś
    """)

    expected = {
        "żółć": "jaźń",
        "kość": "łoś",
    }

    self.assertEqual(parsed, expected)

  def testStringsAreUnicodeObjects(self):
    self.assertIsInstance(yaml.Parse("\"foo\""), Text)


class DumpTest(absltest.TestCase):

  def testSimpleDict(self):
    dumped = yaml.Dump({
        "foo": "bar",
        "quux": 42,
    })

    expected = """\
foo: bar
quux: 42
"""

    self.assertEqual(dumped, expected)

  def testComplexDict(self):
    dumped = yaml.Dump({
        "foo.bar": {
            "quux": [4, 8, 15, 16, 23, 42],
            "thud": ["blargh", "norf"],
        },
        "foo.baz": [3.14, 1.62],
    })

    expected = """\
foo.bar:
  quux:
  - 4
  - 8
  - 15
  - 16
  - 23
  - 42
  thud:
  - blargh
  - norf
foo.baz:
- 3.14
- 1.62
"""

    self.assertEqual(dumped, expected)

  def testUnicode(self):
    data = collections.OrderedDict()
    data["gęsi"] = ["zbożowa", "krótkodzioba", "białoczelna"]
    data["grzebiące"] = ["jarząbek", "głuszec", "bażant"]
    dumped = yaml.Dump(data)

    expected = """\
gęsi:
- zbożowa
- krótkodzioba
- białoczelna
grzebiące:
- jarząbek
- głuszec
- bażant
"""

    self.assertEqual(dumped, expected)


if __name__ == "__main__":
  absltest.main()
