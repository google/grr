#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import platform

from absl.testing import absltest
from typing import Text

from grr_response_core.lib.util import compatibility


class ReprTest(absltest.TestCase):

  def testListOfIntegers(self):
    string = compatibility.Repr([4, 8, 15, 16, 23, 42])
    self.assertIsInstance(string, Text)
    self.assertEqual(string, "[4, 8, 15, 16, 23, 42]")

  def testNonUnicodeBytes(self):
    string = compatibility.Repr(b"\xfa\xfb\xfc\xfe\xff")
    self.assertIsInstance(string, Text)
    # We `assertEndsWith` instead of `assertEquals` to account for string having
    # or not having `b` prefix depending on the Python version being used.
    self.assertEndsWith(string, "'\\xfa\\xfb\\xfc\\xfe\\xff'")


class GetNameTest(absltest.TestCase):

  def testClass(self):

    class Foo(object):
      pass

    self.assertEqual(compatibility.GetName(Foo), "Foo")

  def testFunction(self):

    def Bar():
      pass

    self.assertEqual(compatibility.GetName(Bar), "Bar")


class SetNameTest(absltest.TestCase):

  def testClass(self):

    class Foo(object):
      pass

    compatibility.SetName(Foo, "Bar")
    self.assertEqual(compatibility.GetName(Foo), "Bar")

  def testFunction(self):

    def Baz():
      pass

    compatibility.SetName(Baz, "Thud")
    self.assertEqual(compatibility.GetName(Baz), "Thud")


class ListAttrsTest(absltest.TestCase):

  def testProperties(self):

    class Foo(object):

      BAR = 1
      BAZ = 2

    attrs = compatibility.ListAttrs(Foo)
    self.assertIn("BAR", attrs)
    self.assertIn("BAZ", attrs)

  def testMethods(self):

    class Bar(object):

      def Quux(self):
        pass

      def Thud(self):
        pass

    attrs = compatibility.ListAttrs(Bar)
    self.assertIn("Quux", attrs)
    self.assertIn("Thud", attrs)


class MakeTypeTest(absltest.TestCase):

  def testSimple(self):

    cls = compatibility.MakeType("Foo", (object,), {})
    self.assertEqual(compatibility.GetName(cls), "Foo")
    self.assertIsInstance(cls(), cls)

  def testWithBaseTypes(self):

    class Bar(object):
      pass

    class Baz(object):
      pass

    cls = compatibility.MakeType("Foo", (Bar, Baz), {})
    self.assertEqual(compatibility.GetName(cls), "Foo")
    self.assertTrue(issubclass(cls, Bar))
    self.assertTrue(issubclass(cls, Baz))

  def testWithNamespace(self):

    namespace = {
        "Bar": lambda self: 42,
        "Baz": lambda self, x: x * 2,
    }

    cls = compatibility.MakeType("Foo", (object,), namespace)
    self.assertEqual(compatibility.GetName(cls), "Foo")

    foo = cls()
    self.assertEqual(foo.Bar(), 42)
    self.assertEqual(foo.Baz(42), 84)


class FormatTimeTest(absltest.TestCase):

  def testDate(self):
    stime = datetime.date(year=2012, month=3, day=4).timetuple()
    self.assertEqual(compatibility.FormatTime("%Y-%m-%d", stime), "2012-03-04")

  def testTime(self):
    stime = datetime.datetime.combine(
        date=datetime.date.today(),
        time=datetime.time(hour=13, minute=47, second=58)).timetuple()
    self.assertEqual(compatibility.FormatTime("%H:%M:%S", stime), "13:47:58")

  def testDefault(self):
    self.assertRegex(
        compatibility.FormatTime("%Y-%m-%d %H:%M"),
        "^\\d{4}\\-\\d{2}\\-\\d{2} \\d{2}:\\d{2}$")


class ShlexSplitTest(absltest.TestCase):

  def testNormal(self):
    self.assertEqual(
        compatibility.ShlexSplit("foo bar baz"), ["foo", "bar", "baz"])

  def testUnicode(self):
    self.assertEqual(
        compatibility.ShlexSplit("żółć jaźń gąskę"), ["żółć", "jaźń", "gąskę"])

  def testQuoted(self):
    string = "'Лев Николаевич Толсто́й' 'Сергей Александрович Есенин'"
    parts = ["Лев Николаевич Толсто́й", "Сергей Александрович Есенин"]
    self.assertEqual(compatibility.ShlexSplit(string), parts)


class UnescapeStringTest(absltest.TestCase):

  def testWhitespace(self):
    self.assertEqual(compatibility.UnescapeString("\\n"), "\n")
    self.assertEqual(compatibility.UnescapeString("\\r"), "\r")

  def testQuotemark(self):
    self.assertEqual(compatibility.UnescapeString("\\'"), "'")
    self.assertEqual(compatibility.UnescapeString("\\\""), "\"")

  def testMany(self):
    self.assertEqual(
        compatibility.UnescapeString("foo\\n\\'bar\\'\nbaz"), "foo\n'bar'\nbaz")


class EnvironTest(absltest.TestCase):

  def testStandard(self):
    if platform.system() == "Windows":
      key = "HOMEPATH"
    else:
      key = "HOME"
    self.assertIsInstance(compatibility.Environ(key, default=None), Text)

    self.assertIsInstance(compatibility.Environ("PATH", default=None), Text)

  def testDefault(self):
    variable = "__GRR_SECRET_VARIABLE_THAT_SHOULD_NOT_EXIST__"
    self.assertIsNone(compatibility.Environ(variable, default=None))
    self.assertEqual(compatibility.Environ(variable, default="foo"), "foo")


if __name__ == "__main__":
  absltest.main()
