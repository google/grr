#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections
import io

from absl.testing import absltest
from typing import Any
from typing import Text

from grr_response_core.lib.util import temp
from grr_response_core.lib.util.compat import json


class ParseTest(absltest.TestCase):

  def testSimpleDict(self):
    parsed = json.Parse("""{ "foo": "bar", "quux": 42 }""")
    expected = {"foo": "bar", "quux": 42}
    self.assertEqual(parsed, expected)

  def testSimpleList(self):
    parsed = json.Parse("""[4, 8, 15, 16, 23, 42]""")
    expected = [4, 8, 15, 16, 23, 42]
    self.assertEqual(parsed, expected)

  def testComplexDict(self):
    parsed = json.Parse("""{
      "foo.bar": {
        "quux": [108, 1337],
        "thud": ["blargh", "norf"]
      },
      "foo.baz": [3.14, 1.62]
    }""")
    expected = {
        "foo.bar": {
            "quux": [108, 1337],
            "thud": ["blargh", "norf"],
        },
        "foo.baz": [3.14, 1.62],
    }
    self.assertEqual(parsed, expected)

  def testUnicode(self):
    parsed = json.Parse("""{
      "gęsi (🦆)": ["zbożowa", "krótkodzioba", "białoczelna"],
      "grzebiące (🐔)": ["jarząbek", "głuszec", "bażant"]
    }""")
    expected = {
        "gęsi (🦆)": ["zbożowa", "krótkodzioba", "białoczelna"],
        "grzebiące (🐔)": ["jarząbek", "głuszec", "bażant"],
    }
    self.assertEqual(parsed, expected)

  def testStringsAreUnicodeObjects(self):
    self.assertIsInstance("\"foo\"", Text)


class ReadFromFileTest(absltest.TestCase):

  def testSimple(self):
    buf = io.StringIO("""{
      "foo": "bar"
    }""")

    expected = {
        "foo": "bar",
    }
    self.assertEqual(json.ReadFromFile(buf), expected)

  def testUnicode(self):
    buf = io.StringIO("""["🐊", "🐢", "🦎", "🐍"]""")
    self.assertEqual(json.ReadFromFile(buf), ["🐊", "🐢", "🦎", "🐍"])


class ReadFromPathTest(absltest.TestCase):

  def testSimple(self):
    with temp.AutoTempFilePath() as filepath:
      with io.open(filepath, mode="w", encoding="utf-8") as filedesc:
        filedesc.write("""{
          "foo": "bar",
          "quux": "norf",
          "thud": "blargh"
        }""")

      expected = {
          "foo": "bar",
          "quux": "norf",
          "thud": "blargh",
      }
      self.assertEqual(json.ReadFromPath(filepath), expected)

  def testUnicode(self):
    with temp.AutoTempFilePath() as filepath:
      with io.open(filepath, mode="w", encoding="utf-8") as filedesc:
        filedesc.write("""["🐋", "🐬", "🐟"]""")

      self.assertEqual(json.ReadFromPath(filepath), ["🐋", "🐬", "🐟"])


class DumpTest(absltest.TestCase):

  def testSimpleDict(self):
    data = collections.OrderedDict()
    data["foo"] = "bar"
    data["quux"] = 42
    dumped = json.Dump(data)

    expected = """{
  "foo": "bar",
  "quux": 42
}"""

    self.assertEqual(dumped, expected)

  def testSimpleList(self):
    dumped = json.Dump([4, 8, 15, 16, 23, 42])
    expected = """[
  4,
  8,
  15,
  16,
  23,
  42
]"""
    self.assertEqual(dumped, expected)

  def testComplexOrderedDict(self):
    data = collections.OrderedDict()
    data["foo.bar"] = collections.OrderedDict()
    data["foo.bar"]["quux"] = [4, 8, 15, 16, 23, 42]
    data["foo.bar"]["thud"] = ["blargh", "norf"]
    data["foo.baz"] = [3.14, 1.62]
    dumped = json.Dump(data)

    expected = """{
  "foo.bar": {
    "quux": [
      4,
      8,
      15,
      16,
      23,
      42
    ],
    "thud": [
      "blargh",
      "norf"
    ]
  },
  "foo.baz": [
    3.14,
    1.62
  ]
}"""

    self.assertEqual(dumped, expected)

  def testUnorderedDictWithSortKeys(self):
    data = {}
    data["foo.bar"] = collections.OrderedDict()
    data["foo.bar"]["quux"] = 1
    data["foo.bar"]["thud"] = 2
    data["foo.baz"] = 4
    dumped = json.Dump(data, sort_keys=True)

    expected = """{
  "foo.bar": {
    "quux": 1,
    "thud": 2
  },
  "foo.baz": 4
}"""
    self.assertEqual(dumped, expected)

  def testUnicode(self):
    data = collections.OrderedDict()
    data["gęsi (🦆)"] = ["zbożowa", "krótkodzioba", "białoczelna"]
    data["grzebiące (🐔)"] = ["jarząbek", "głuszec", "bażant"]
    dumped = json.Dump(data)

    expected = """{
  "gęsi (🦆)": [
    "zbożowa",
    "krótkodzioba",
    "białoczelna"
  ],
  "grzebiące (🐔)": [
    "jarząbek",
    "głuszec",
    "bażant"
  ]
}"""

    self.assertEqual(dumped, expected)

  def testEncoder(self):

    class Foo(object):

      def __init__(self, foo):
        self.foo = foo

    class FooEncoder(json.Encoder):

      def default(self, obj):
        if isinstance(obj, Foo):
          return obj.foo
        else:
          return super(FooEncoder, self).default(obj)

    data = [Foo("quux"), Foo("norf"), Foo("thud")]
    dumped = json.Dump(data, encoder=FooEncoder)
    self.assertEqual(dumped, """[
  "quux",
  "norf",
  "thud"
]""")


if __name__ == "__main__":
  absltest.main()
