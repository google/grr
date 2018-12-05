#!/usr/bin/env python
"""Tests for grr.lib.keyword_index."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_server import aff4
from grr_response_server import keyword_index
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class AFF4KeywordIndexTest(aff4_test_lib.AFF4ObjectTest):

  def testKeywordIndex(self):
    index = aff4.FACTORY.Create(
        "aff4:/index1/",
        aff4_type=keyword_index.AFF4KeywordIndex,
        mode="rw",
        token=self.token)

    # "popular_keyword1" is relevant for 50 subjects.
    for i in range(50):
      index.AddKeywordsForName("C.%X" % i, ["popular_keyword1"])
    results = index.Lookup(["popular_keyword1"])
    self.assertLen(results, 50)

    # "popular_keyword2" is relevant for 75 subjects.
    for i in range(25, 100):
      index.AddKeywordsForName("C.%X" % i, ["popular_keyword2"])
    results = index.Lookup(["popular_keyword2"])
    self.assertLen(results, 75)

    # "popular_keyword1" is still relevant for 50 subjects.
    results = index.Lookup(["popular_keyword1"])
    self.assertLen(results, 50)

    # There are 25 subjects relevant to both popular keywords.
    results = index.Lookup(["popular_keyword1", "popular_keyword2"])
    self.assertLen(results, 25)

    # A keyword with no subjects does lead to no results returned.
    results = index.Lookup(
        ["popular_keyword1", "popular_keyword2", "unknown_keyword"])
    self.assertEmpty(results)

  def testKeywordIndexTimestamps(self):
    index = aff4.FACTORY.Create(
        "aff4:/index2/",
        aff4_type=keyword_index.AFF4KeywordIndex,
        mode="rw",
        token=self.token)
    for i in range(50):
      with test_lib.FakeTime(1000 + i):
        index.AddKeywordsForName("C.%X" % i, ["popular_keyword1"])
    results = index.Lookup(["popular_keyword1"])
    self.assertLen(results, 50)

    results = index.Lookup(["popular_keyword1"], start_time=1025 * 1000000)
    self.assertLen(results, 25)

    results = index.Lookup(["popular_keyword1"], end_time=1024 * 1000000)
    self.assertLen(results, 25)

    results = index.Lookup(["popular_keyword1"],
                           start_time=1025 * 1000000,
                           end_time=1025 * 1000000)
    self.assertLen(results, 1)

  def testKeywordIndexLastSeen(self):
    index = aff4.FACTORY.Create(
        "aff4:/index2/",
        aff4_type=keyword_index.AFF4KeywordIndex,
        mode="rw",
        token=self.token)
    for i in range(5):
      with test_lib.FakeTime(2000 + i):
        index.AddKeywordsForName("C.000000", ["popular_keyword1"])

    for i in range(10):
      with test_lib.FakeTime(1000 + i):
        index.AddKeywordsForName("C.000000", ["popular_keyword2"])

    ls_map = {}
    index.Lookup(["popular_keyword1", "popular_keyword2"], last_seen_map=ls_map)
    self.assertEqual(2004 * 1000000, ls_map[("popular_keyword1", "C.000000")])
    self.assertEqual(1009 * 1000000, ls_map[("popular_keyword2", "C.000000")])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
