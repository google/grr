#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest
from future.builtins import int
from future.builtins import str

from grr_response_core.lib.util import precondition


class AssertTypeTest(absltest.TestCase):

  def testIntCorrect(self):
    del self  # Unused.
    precondition.AssertType(108, int)
    precondition.AssertType(0xABC, int)
    precondition.AssertType(2**1024, int)

  def testIntIncorrect(self):
    with self.assertRaises(TypeError):
      precondition.AssertType(1.23, int)

    with self.assertRaises(TypeError):
      precondition.AssertType("123", int)

  def testStringCorrect(self):
    precondition.AssertType("foo", str)
    precondition.AssertType("gżegżółka", str)

  def testStringIncorrect(self):
    with self.assertRaises(TypeError):
      precondition.AssertType(b"foo", str)


class AssertOptionalTypeTest(absltest.TestCase):

  def testIntCorrect(self):
    del self  # Unused.
    precondition.AssertOptionalType(1337, int)
    precondition.AssertOptionalType(None, int)

  def testIntIncorrect(self):
    with self.assertRaises(TypeError):
      precondition.AssertOptionalType(13.37, int)

  def testStringCorrect(self):
    del self  # Unused.
    precondition.AssertOptionalType("foo", str)
    precondition.AssertOptionalType(None, str)

  def testStringIncorrect(self):
    with self.assertRaises(TypeError):
      precondition.AssertOptionalType(b"foo", str)

  def testBytesCorrect(self):
    del self  # Unused.
    precondition.AssertOptionalType(b"quux", bytes)
    precondition.AssertOptionalType(None, bytes)

  def testBytesIncorrect(self):
    with self.assertRaises(TypeError):
      precondition.AssertOptionalType("quux", bytes)


class AssertIterableTypeTest(absltest.TestCase):

  def testAssertEmptyCorrect(self):
    del self  # Unused.
    precondition.AssertIterableType([], int)
    precondition.AssertIterableType({}, str)

  def testStringSetCorrect(self):
    del self  # Unused.
    precondition.AssertIterableType({"foo", "bar", "baz"}, str)

  def testNonHomogeneousIntList(self):
    with self.assertRaises(TypeError):
      precondition.AssertIterableType([4, 8, 15, 16.0, 23, 42], int)

  def testIteratorIsNotIterable(self):
    with self.assertRaises(TypeError):
      precondition.AssertIterableType(iter(["foo", "bar", "baz"]), str)

  def testGeneratorIsNotIterable(self):

    def Generator():
      yield 1
      yield 2
      yield 3

    with self.assertRaises(TypeError):
      precondition.AssertIterableType(Generator(), int)


class AssertDictTypeTest(absltest.TestCase):

  def testIntStringDictCorrect(self):
    del self  # Unused.
    dct = {1: "foo", 2: "bar", 3: "baz"}
    precondition.AssertDictType(dct, int, str)

  def testNotADictIncorrect(self):
    dct = [(1, "foo"), (2, "bar"), (3, "baz")]
    with self.assertRaises(TypeError):
      precondition.AssertDictType(dct, int, str)

  def testWrongKeyType(self):
    dct = {"foo": 1, b"bar": 2, "baz": 3}
    with self.assertRaises(TypeError):
      precondition.AssertDictType(dct, str, int)

  def testWrongValueType(self):
    dct = {"foo": 1, "bar": 2, "baz": 3.14}
    with self.assertRaises(TypeError):
      precondition.AssertDictType(dct, str, int)


if __name__ == "__main__":
  absltest.main()
