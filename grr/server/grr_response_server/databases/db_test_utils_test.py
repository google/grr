#!/usr/bin/env python
"""Tests for the hunt database api."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from absl.testing import absltest

from grr_response_server.databases import db_test_utils


class TestOffsetAndCountTest(db_test_utils.QueryTestHelpersMixin,
                             absltest.TestCase):

  def testDoesNotRaiseWhenWorksAsExpected(self):
    items = range(10)
    self.TestOffsetAndCount(
        lambda: items,
        lambda offset, count: items[offset:offset + count],
        error_desc="foo")

  def testRaisesWhenDoesNotWorkAsExpected(self):
    items = range(10)

    def FetchRangeFn(offset, count):
      # Deliberate bug for offset > 5.
      if offset > 5:
        return []
      else:
        return items[offset:offset + count]

    with self.assertRaisesRegex(
        AssertionError,
        re.escape(
            "Results differ from expected (offset 6, count 1, foo): [] vs [6]")
    ):
      self.TestOffsetAndCount(lambda: items, FetchRangeFn, error_desc="foo")


class TestFilterCombinations(db_test_utils.QueryTestHelpersMixin,
                             absltest.TestCase):

  def testDoesNotRaiseWhenWorkingAsExpected(self):

    def FetchFn(bigger_than_3_only=None, less_than_7_only=None, even_only=None):
      result = []
      for i in range(10):
        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      return result

    self.TestFilterCombinations(
        FetchFn,
        dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
        error_desc="foo")

  def testRaisesWhenDoesNotWorkAsExpected(self):

    def FetchFn(bigger_than_3_only=None, less_than_7_only=None, even_only=None):
      result = []
      for i in range(10):
        # This line introduces a bug.
        if bigger_than_3_only and less_than_7_only and i == 4:
          continue

        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      return result

    with self.assertRaisesRegex(
        AssertionError,
        re.escape(
            "Results differ from expected "
            "({'bigger_than_3_only': True, 'less_than_7_only': True}, foo): "
            "[5, 6] vs [4, 5, 6]")):
      self.TestFilterCombinations(
          FetchFn,
          dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
          error_desc="foo")


class TestFilterCombinationsAndOffsetCountTest(
    db_test_utils.QueryTestHelpersMixin, absltest.TestCase):

  def testDoesNotRaiseWhenWorksAsExpected(self):

    def FetchFn(offset,
                count,
                bigger_than_3_only=None,
                less_than_7_only=None,
                even_only=None):
      result = []
      for i in range(10):
        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      return result[offset:offset + count]

    self.TestFilterCombinationsAndOffsetCount(
        FetchFn,
        dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
        error_desc="foo")

  def testRaisesWhenDoesNotWorkAsExpected(self):

    def FetchFn(offset,
                count,
                bigger_than_3_only=None,
                less_than_7_only=None,
                even_only=None):
      del offset  # Unused.

      result = []
      for i in range(10):
        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      # An intentionally buggy line.
      # Should have been: result[offset:offset + count]
      return result[0:count]

    with self.assertRaisesRegex(
        AssertionError,
        re.escape("Results differ from expected "
                  "(offset 1, count 1, {'bigger_than_3_only': True}, foo): "
                  "[4] vs [5]")):
      self.TestFilterCombinationsAndOffsetCount(
          FetchFn,
          dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
          error_desc="foo")


if __name__ == "__main__":
  absltest.main()
