#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_core.lib.util import compatibility


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


if __name__ == "__main__":
  absltest.main()
