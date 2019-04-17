#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import io

from absl.testing import absltest
from typing import Text


from grr_response_core.lib.util.compat import yaml  # pylint: disable=g-import-not-at-top


# TODO: Add tests with 4-byte unicode characters once we switch to
# a proper YAML library.


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


class ParseManyTest(absltest.TestCase):

  def testMultipleDicts(self):
    parsed = yaml.ParseMany("""
foo: 42
bar: 108
---
quux: norf
thud: blargh
    """)

    expected = [
        {
            "foo": 42,
            "bar": 108,
        },
        {
            "quux": "norf",
            "thud": "blargh",
        },
    ]

    self.assertEqual(parsed, expected)

  def testUnicode(self):
    parsed = yaml.ParseMany("""
gąszcz: żuk
---
gęstwina: chrabąszcz
    """)

    expected = [
        {
            "gąszcz": "żuk"
        },
        {
            "gęstwina": "chrabąszcz"
        },
    ]

    self.assertEqual(parsed, expected)


class ReadFromFileTest(absltest.TestCase):

  def testSimple(self):
    buf = io.StringIO("""
foo: bar
    """)

    expected = {
        "foo": "bar",
    }
    self.assertEqual(yaml.ReadFromFile(buf), expected)

  def testUnicode(self):
    buf = io.StringIO("['Ł', 'Ż', 'Ź', 'Ó']")
    self.assertEqual(yaml.ReadFromFile(buf), ["Ł", "Ż", "Ź", "Ó"])


class ReadManyFromFileTest(absltest.TestCase):

  def testSimple(self):
    buf = io.StringIO("""
foo: bar
---
quux: norf
---
thud: blargh
    """)

    expected = [
        {
            "foo": "bar",
        },
        {
            "quux": "norf",
        },
        {
            "thud": "blargh",
        },
    ]
    self.assertEqual(yaml.ReadManyFromFile(buf), expected)

  def testUnicode(self):
    buf = io.StringIO("""
- Ą
- Ę
---
- Ś
- Ć
  """)
    self.assertEqual(yaml.ReadManyFromFile(buf), [["Ą", "Ę"], ["Ś", "Ć"]])


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


class DumpManyTest(absltest.TestCase):

  def testMultipleDicts(self):
    dumped = yaml.DumpMany([
        collections.OrderedDict([("foo", 42), ("bar", 108)]),
        collections.OrderedDict([("quux", "norf"), ("thud", "blargh")]),
    ])

    expected = """\
foo: 42
bar: 108
---
quux: norf
thud: blargh
"""

    self.assertEqual(dumped, expected)

  def testUnicode(self):
    dumped = yaml.DumpMany([
        {
            "gąszcz": "żuk"
        },
        {
            "gęstwina": "chrabąszcz"
        },
    ])

    expected = """\
gąszcz: żuk
---
gęstwina: chrabąszcz
"""

    self.assertEqual(dumped, expected)


class WriteToFileTest(absltest.TestCase):

  def testSimple(self):
    buf = io.StringIO()
    yaml.WriteToFile(["foo", "bar", "baz"], buf)

    expected = """\
- foo
- bar
- baz
"""
    self.assertEqual(buf.getvalue(), expected)

  def testUnicode(self):
    buf = io.StringIO()
    yaml.WriteToFile({"śpiączka": "własność"}, buf)

    expected = """\
śpiączka: własność
"""
    self.assertEqual(buf.getvalue(), expected)


class WriteManyToFileTest(absltest.TestCase):

  def testSimple(self):
    buf = io.StringIO()
    yaml.WriteManyToFile([["foo", "bar"], ["quux", "norf"]], buf)

    expected = """\
- foo
- bar
---
- quux
- norf
"""
    self.assertEqual(buf.getvalue(), expected)

  def testUnicode(self):
    buf = io.StringIO()
    yaml.WriteManyToFile([{"żałość": "nędza"}, {"ból": "udręka"}], buf)

    expected = """\
żałość: nędza
---
ból: udręka
"""
    self.assertEqual(buf.getvalue(), expected)


if __name__ == "__main__":
  absltest.main()
