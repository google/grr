#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest
from grr_response_core.lib import factory
from grr_response_core.lib import flags
from grr.test_lib import test_lib


class FactoryTest(absltest.TestCase):

  def testRegisterAndUnregister(self):
    del self  # Unused.

    obj_factory = factory.Factory(object)

    # First, we check whether registering works.
    obj_factory.Register("foo", object)
    obj_factory.Register("bar", object)

    # Now, we should be able to unregister these constructors.
    obj_factory.Unregister("foo")
    obj_factory.Unregister("bar")

    # Once they are unregistered, names are free to be bound again.
    obj_factory.Register("foo", object)
    obj_factory.Register("bar", object)

  def testRegisterDuplicateThrows(self):
    obj_factory = factory.Factory(object)
    obj_factory.Register("foo", object)
    obj_factory.Register("bar", object)

    with self.assertRaisesRegexp(ValueError, "foo"):
      obj_factory.Register("foo", object)

  def testUnregisterThrowsForUnknown(self):
    obj_factory = factory.Factory(object)

    with self.assertRaisesRegexp(ValueError, "foo"):
      obj_factory.Unregister("foo")

  def testCreateString(self):
    str_factory = factory.Factory(unicode)
    str_factory.Register("foo", lambda: "FOO")
    str_factory.Register("bar", lambda: "BAR")
    str_factory.Register("baz", lambda: "BAZ")

    self.assertEqual(str_factory.Create("foo"), "FOO")
    self.assertEqual(str_factory.Create("bar"), "BAR")
    self.assertEqual(str_factory.Create("baz"), "BAZ")

  def testCreateClass(self):

    class Foo(object):
      pass

    class Bar(object):
      pass

    cls_factory = factory.Factory(object)
    cls_factory.Register("Foo", Foo)
    cls_factory.Register("Bar", Bar)

    self.assertIsInstance(cls_factory.Create("Foo"), Foo)
    self.assertIsInstance(cls_factory.Create("Bar"), Bar)

  def testCreateUnregisteredThrows(self):
    int_factory = factory.Factory(int)

    with self.assertRaisesRegexp(ValueError, "foo"):
      int_factory.Create("foo")

  def testCreateWrongTypeThrows(self):
    int_factory = factory.Factory(int)
    int_factory.Register("foo", lambda: "Foo")

    with self.assertRaises(TypeError):
      int_factory.Create("foo")

  def testCreateAllEmpty(self):
    obj_factory = factory.Factory(object)

    self.assertCountEqual(list(obj_factory.CreateAll()), [])

  def testCreateAllSome(self):
    int_factory = factory.Factory(int)
    int_factory.Register("foo", lambda: 1337)
    int_factory.Register("bar", lambda: 101)
    int_factory.Register("baz", lambda: 108)

    self.assertCountEqual(list(int_factory.CreateAll()), [1337, 101, 108])


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
