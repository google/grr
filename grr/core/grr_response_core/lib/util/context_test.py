#!/usr/bin/env python
import contextlib
import functools
import io

from absl.testing import absltest

from grr_response_core.lib.util import context
from grr_response_core.lib.util import temp


class MultiContextTest(absltest.TestCase):

  def testEmpty(self):
    with context.MultiContext([]) as values:
      self.assertEqual(values, [])

  def testWithNulls(self):
    foo = contextlib.nullcontext("foo")
    bar = contextlib.nullcontext("bar")
    baz = contextlib.nullcontext("baz")

    with context.MultiContext([foo, bar, baz]) as names:
      self.assertEqual(names, ["foo", "bar", "baz"])

  def testWithFiles(self):
    foo = temp.AutoTempFilePath(suffix="foo")
    bar = temp.AutoTempFilePath(suffix="bar")
    baz = temp.AutoTempFilePath(suffix="baz")

    with context.MultiContext([foo, bar, baz]) as filepaths:
      self.assertLen(filepaths, 3)
      self.assertEndsWith(filepaths[0], "foo")
      self.assertEndsWith(filepaths[1], "bar")
      self.assertEndsWith(filepaths[2], "baz")

      wbopen = functools.partial(io.open, mode="wb")
      with context.MultiContext(list(map(wbopen, filepaths))) as filedescs:
        self.assertLen(filedescs, 3)
        filedescs[0].write(b"FOO")
        filedescs[1].write(b"BAR")
        filedescs[2].write(b"BAZ")

      # At this point all three files should be correctly written, closed and
      # ready for reading.

      rbopen = functools.partial(io.open, mode="rb")
      with context.MultiContext(list(map(rbopen, filepaths))) as filedescs:
        self.assertLen(filedescs, 3)
        self.assertEqual(filedescs[0].read(), b"FOO")
        self.assertEqual(filedescs[1].read(), b"BAR")
        self.assertEqual(filedescs[2].read(), b"BAZ")


if __name__ == "__main__":
  absltest.main()
