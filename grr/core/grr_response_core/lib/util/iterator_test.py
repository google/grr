#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.util import iterator


class CountedTest(absltest.TestCase):

  def testCountEmpty(self):
    empty = iterator.Counted(iter([]))
    self.assertEqual(empty.count, 0)

    with self.assertRaises(StopIteration):
      next(empty)

  def testCountSimple(self):
    items = iterator.Counted(iter(["foo", "bar", "baz"]))
    self.assertEqual(items.count, 0)
    self.assertEqual(next(items), "foo")
    self.assertEqual(items.count, 1)
    self.assertEqual(next(items), "bar")
    self.assertEqual(items.count, 2)
    self.assertEqual(next(items), "baz")
    self.assertEqual(items.count, 3)

    with self.assertRaises(StopIteration):
      next(items)

  def testCountInterrupted(self):

    def Generator():
      yield "foo"
      raise ValueError()
      yield "bar"  # pylint: disable=unreachable

    items = iterator.Counted(Generator())
    self.assertEqual(items.count, 0)
    self.assertEqual(next(items), "foo")
    self.assertEqual(items.count, 1)

    with self.assertRaises(ValueError):
      next(items)

    # The counter should not increase if the item was not retrieved.
    self.assertEqual(items.count, 1)

  def testResetEmpty(self):
    empty = iterator.Counted(iter([]))
    empty.Reset()
    self.assertEqual(empty.count, 0)

  def testResetSimple(self):
    items = iterator.Counted(iter(["foo", "bar", "baz"]))

    next(items)
    self.assertEqual(items.count, 1)

    items.Reset()
    self.assertEqual(items.count, 0)

    next(items)
    next(items)
    self.assertEqual(items.count, 2)

    items.Reset()
    self.assertEqual(items.count, 0)


if __name__ == "__main__":
  absltest.main()
