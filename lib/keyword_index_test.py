#!/usr/bin/env python
"""Tests for grr.lib.keyword_index."""


from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib


class KeywordIndexTest(test_lib.AFF4ObjectTest):

  def testKeywordIndex(self):
    index = aff4.FACTORY.Create("aff4:/index1/",
                                aff4_type="AFF4KeywordIndex",
                                mode="rw",
                                token=self.token)

    # "popular_keyword1" is relevant for 50 subjects.
    for i in range(50):
      index.AddKeywordsForName("C.%X" % i,
                               ["popular_keyword1"])
    results = index.Lookup(["popular_keyword1"])
    self.assertEqual(len(results), 50)

    # "popular_keyword2" is relevant for 75 subjects.
    for i in range(25, 100):
      index.AddKeywordsForName("C.%X" % i,
                               ["popular_keyword2"])
    results = index.Lookup(["popular_keyword2"])
    self.assertEqual(len(results), 75)

    # "popular_keyword1" is still relevant for 50 subjects.
    results = index.Lookup(["popular_keyword1"])
    self.assertEqual(len(results), 50)

    # There are 25 subjects relevant to both popular keywords.
    results = index.Lookup(["popular_keyword1", "popular_keyword2"])
    self.assertEqual(len(results), 25)

    # A keyword with no subjects does lead to no results returned.
    results = index.Lookup(["popular_keyword1", "popular_keyword2",
                            "unknown_keyword"])
    self.assertEqual(len(results), 0)

  def testKeywordIndexTimestamps(self):
    index = aff4.FACTORY.Create("aff4:/index2/",
                                aff4_type="AFF4KeywordIndex",
                                mode="rw",
                                token=self.token)
    for i in range(50):
      with test_lib.FakeTime(1000 + i):
        index.AddKeywordsForName("C.%X" % i, ["popular_keyword1"])
    results = index.Lookup(["popular_keyword1"])
    self.assertEqual(len(results), 50)

    results = index.Lookup(["popular_keyword1"], start_time=1025 * 1000000)
    self.assertEqual(len(results), 25)

    results = index.Lookup(["popular_keyword1"], end_time=1024 * 1000000)
    self.assertEqual(len(results), 25)

    results = index.Lookup(["popular_keyword1"],
                           start_time=1025 * 1000000,
                           end_time=1025 * 1000000)
    self.assertEqual(len(results), 1)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
