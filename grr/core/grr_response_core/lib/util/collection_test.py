#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest
from future.builtins import range

from grr_response_core.lib.util import collection


class FlattenTest(absltest.TestCase):

  def testList(self):
    flattened = collection.Flatten([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    self.assertListEqual(list(flattened), [1, 2, 3, 4, 5, 6, 7, 8, 9])

  def testTuple(self):
    flattened = collection.Flatten(((4, 8, 15), (16, 23, 42)))
    self.assertListEqual(list(flattened), [4, 8, 15, 16, 23, 42])

  def testGenerator(self):

    def Foo():
      yield "foo"
      yield "bar"

    def Quux():
      yield "baz"
      yield "quux"

    def Norf():
      yield Foo()
      yield Quux()

    flattened = collection.Flatten(Norf())
    self.assertListEqual(list(flattened), ["foo", "bar", "baz", "quux"])


class TrimTest(absltest.TestCase):

  def testEmpty(self):
    lst = []
    clipping = collection.Trim(lst, limit=3)
    self.assertEqual(lst, [])
    self.assertEqual(clipping, [])

  def testSomeClipping(self):
    lst = [1, 2, 3, 4, 5, 6, 7]
    clipping = collection.Trim(lst, limit=4)
    self.assertEqual(lst, [1, 2, 3, 4])
    self.assertEqual(clipping, [5, 6, 7])

  def testNoClipping(self):
    lst = [1, 2, 3, 4]
    clipping = collection.Trim(lst, limit=10)
    self.assertEqual(lst, [1, 2, 3, 4])
    self.assertEqual(clipping, [])

  def testLimit0(self):
    lst = [1, 2, 3]
    clipping = collection.Trim(lst, limit=0)
    self.assertEqual(lst, [])
    self.assertEqual(clipping, [1, 2, 3])

  def testLimitNegative(self):
    lst = [1, 2, 3]
    clipping = collection.Trim(lst, limit=-3)
    self.assertEqual(lst, [])
    self.assertEqual(clipping, [1, 2, 3])


class GroupTest(absltest.TestCase):

  def testEmpty(self):
    result = collection.Group([], key=lambda _: None)
    expected = {}
    self.assertEqual(result, expected)

  def testByIdentity(self):
    result = collection.Group([3, 2, 1, 1, 5, 3, 1, 5], key=lambda num: num)
    expected = {1: [1, 1, 1], 2: [2], 3: [3, 3], 5: [5, 5]}
    self.assertEqual(result, expected)

  def testByFirstLetter(self):
    result = collection.Group(["foo", "bar", "baz"], key=lambda text: text[0])
    expected = {"f": ["foo"], "b": ["bar", "baz"]}
    self.assertEqual(result, expected)

  def testGenerator(self):

    def Generate():
      yield 4
      yield 8
      yield 15
      yield 16
      yield 23
      yield 42

    result = collection.Group(Generate(), key=lambda num: num % 2)
    expected = {0: [4, 8, 16, 42], 1: [15, 23]}
    self.assertEqual(result, expected)


class BatchTest(absltest.TestCase):

  def testEmpty(self):
    batches = list(collection.Batch([], 10))
    self.assertEqual(batches, [])

  def testUneven(self):
    batches = list(collection.Batch(range(10), size=4))
    self.assertEqual(batches, [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]])

  def testSmallSize(self):
    batches = list(collection.Batch([None] * 100, size=1))
    self.assertEqual(batches, [[None]] * 100)

  def testBigSize(self):
    batches = list(collection.Batch([None] * 20, size=100))
    self.assertEqual(batches, [[None] * 20])


class StartsWithTest(absltest.TestCase):

  def testEmptyStartsWithEmpty(self):
    self.assertTrue(collection.StartsWith([], []))

  def testNonEmptyStartsWithEmpty(self):
    self.assertTrue(collection.StartsWith([1, 2, 3], []))

  def testEmptyDoesNotStartWithNonEmpty(self):
    self.assertFalse(collection.StartsWith([], [1, 2, 3]))

  def testEqual(self):
    self.assertTrue(collection.StartsWith([1, 2, 3], [1, 2, 3]))

  def testProperPrefix(self):
    self.assertTrue(collection.StartsWith([1, 2, 3], [1, 2]))
    self.assertTrue(collection.StartsWith([1, 2, 3], [1]))

  def testDifferentElement(self):
    self.assertFalse(collection.StartsWith([1, 2, 3], [1, 4, 5]))

  def testStringList(self):
    self.assertTrue(collection.StartsWith(["a", "b", "c"], ["a", "b"]))

  def testString(self):
    self.assertTrue(collection.StartsWith("foobar", "foo"))

  def testNonListIterable(self):
    self.assertTrue(collection.StartsWith((5, 4, 3), (5, 4)))


class UnzipTest(absltest.TestCase):

  def testEmpty(self):
    left, right = collection.Unzip([])
    self.assertEmpty(left)
    self.assertEmpty(right)

  def testList(self):
    left, right = collection.Unzip([(1, 2), (3, 4), (5, 6)])
    self.assertSequenceEqual(left, [1, 3, 5])
    self.assertSequenceEqual(right, [2, 4, 6])

  def testGenerator(self):

    def Foo():
      yield 1, "foo"
      yield 2, "bar"
      yield 3, "baz"

    left, right = collection.Unzip(Foo())
    self.assertSequenceEqual(left, [1, 2, 3])
    self.assertSequenceEqual(right, ["foo", "bar", "baz"])

  def testStrings(self):
    left, right = collection.Unzip(zip("fooquux", "barnorf"))
    self.assertSequenceEqual(left, "fooquux")
    self.assertSequenceEqual(right, "barnorf")


class DictProductTest(absltest.TestCase):

  def testEmptyDict(self):
    in_dict = {}
    self.assertEqual(list(collection.DictProduct(in_dict)), [{}])

  def testEmptyValues(self):
    in_dict = {"a": [1, 2], "b": [], "c": [5, 6]}
    self.assertEqual(list(collection.DictProduct(in_dict)), [])

  def testSingleKeys(self):
    in_dict = {"a": [1], "b": [2], "c": [3]}
    out_dicts = [{"a": 1, "b": 2, "c": 3}]
    self.assertEqual(list(collection.DictProduct(in_dict)), out_dicts)

  def testMultipleKeys(self):
    in_dicts = {"a": [1, 2], "b": [3, 4], "c": [5, 6]}
    out_dicts = [
        {
            "a": 1,
            "b": 3,
            "c": 5
        },
        {
            "a": 1,
            "b": 3,
            "c": 6
        },
        {
            "a": 1,
            "b": 4,
            "c": 5
        },
        {
            "a": 1,
            "b": 4,
            "c": 6
        },
        {
            "a": 2,
            "b": 3,
            "c": 5
        },
        {
            "a": 2,
            "b": 3,
            "c": 6
        },
        {
            "a": 2,
            "b": 4,
            "c": 5
        },
        {
            "a": 2,
            "b": 4,
            "c": 6
        },
    ]

    self.assertCountEqual(list(collection.DictProduct(in_dicts)), out_dicts)


if __name__ == "__main__":
  absltest.main()
