#!/usr/bin/env python
"""Tests for SequentialCollection and related subclasses."""

import threading

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import sequential_collection
from grr.lib import test_lib
from grr.lib import utils


class TestSequentialCollection(sequential_collection.SequentialCollection):
  RDF_TYPE = rdfvalue.RDFInteger


class SequentialCollectionTest(test_lib.AFF4ObjectTest):

  def _TestCollection(self, collection_id):
    return TestSequentialCollection(
        rdfvalue.RDFURN(collection_id), token=self.token)

  def testAddScan(self):
    collection = self._TestCollection("aff4:/sequential_collection/testAddScan")
    for i in range(100):
      collection.Add(rdfvalue.RDFInteger(i))

    i = 0
    last_ts = 0
    for (ts, v) in collection.Scan():
      last_ts = ts
      self.assertEqual(i, v)
      i += 1

    for j in range(100):
      collection.Add(rdfvalue.RDFInteger(j + 100))

    for (ts, v) in collection.Scan(after_timestamp=last_ts):
      self.assertEqual(i, v)
      i += 1

    self.assertEqual(i, 200)

  def testDuplicateTimestamps(self):
    collection = self._TestCollection(
        "aff4:/sequential_collection/testDuplicateTimestamps")
    t = rdfvalue.RDFDatetime.Now()
    for i in range(10):
      ts = collection.Add(rdfvalue.RDFInteger(i), timestamp=t)
      self.assertEqual(ts[0], t)

    i = 0
    for (ts, _) in collection.Scan():
      self.assertEqual(ts, t)
      i += 1
    self.assertEqual(i, 10)

  def testMultiResolve(self):
    collection = self._TestCollection("aff4:/sequential_collection/testAddScan")
    timestamps = []
    for i in range(100):
      timestamps.append(collection.Add(rdfvalue.RDFInteger(i)))

    even_results = sorted([r for r in collection.MultiResolve(timestamps[::2])])
    self.assertEqual(len(even_results), 50)
    self.assertEqual(even_results[0], 0)
    self.assertEqual(even_results[49], 98)

  def testDelete(self):
    collection = self._TestCollection("aff4:/sequential_collection/testDelete")
    for i in range(100):
      collection.Add(rdfvalue.RDFInteger(i))

    collection.Delete()

    collection = self._TestCollection("aff4:/sequential_collection/testDelete")
    for _ in collection.Scan():
      self.fail("Deleted and recreated SequentialCollection should be empty")


class TestIndexedSequentialCollection(
    sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdfvalue.RDFInteger


class IndexedSequentialCollectionTest(test_lib.AFF4ObjectTest):

  def _TestCollection(self, collection_id):
    return TestIndexedSequentialCollection(
        rdfvalue.RDFURN(collection_id), token=self.token)

  def setUp(self):
    super(IndexedSequentialCollectionTest, self).setUp()
    # Create a new background thread for each test. In the default
    # configuration, this thread can sleep for quite a long time and
    # might therefore be unavailable in further tests so we just
    # create a new one for each test we run.
    biu = sequential_collection.BackgroundIndexUpdater()
    try:
      sequential_collection.BACKGROUND_INDEX_UPDATER.ExitNow()
    except AttributeError:
      pass
    sequential_collection.BACKGROUND_INDEX_UPDATER = biu
    t = threading.Thread(None, biu.UpdateLoop)
    t.daemon = True
    t.start()

  def testAddGet(self):
    collection = self._TestCollection("aff4:/sequential_collection/testAddGet")
    self.assertEqual(collection.CalculateLength(), 0)
    for i in range(100):
      collection.Add(rdfvalue.RDFInteger(i))
    for i in range(100):
      self.assertEqual(collection[i], i)

    self.assertEqual(collection.CalculateLength(), 100)
    self.assertEqual(len(collection), 100)

  def testStaticAddGet(self):
    collection = self._TestCollection(
        "aff4:/sequential_collection/testStaticAddGet")
    self.assertEqual(collection.CalculateLength(), 0)
    for i in range(100):
      TestIndexedSequentialCollection.StaticAdd(
          "aff4:/sequential_collection/testStaticAddGet", self.token,
          rdfvalue.RDFInteger(i))
    for i in range(100):
      self.assertEqual(collection[i], i)

    self.assertEqual(collection.CalculateLength(), 100)
    self.assertEqual(len(collection), 100)

  def testIndexCreate(self):
    collection = self._TestCollection(
        "aff4:/sequential_collection/testIndexCreate")
    for i in range(10 * 1024):
      collection.Add(rdfvalue.RDFInteger(i))

    # It is too soon to build an index, check that we don't.
    self.assertEqual(collection._index, None)
    self.assertEqual(collection.CalculateLength(), 10 * 1024)
    self.assertEqual(sorted(collection._index.keys()), [0])

    # Push the clock forward 10m, and we should build an index on access.
    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() + rdfvalue.Duration(
        "10m")):
      # Read from start doesn't rebuild index (lazy rebuild)
      _ = collection[0]
      self.assertEqual(sorted(collection._index.keys()), [0])

      self.assertEqual(collection.CalculateLength(), 10 * 1024)
      self.assertEqual(
          sorted(collection._index.keys()),
          [0, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192, 9216])

    # Now check that the index was persisted to aff4 by re-opening and checking
    # that a read from head does load full index (optimistic load):

    collection = self._TestCollection(
        "aff4:/sequential_collection/testIndexCreate")
    self.assertEqual(collection._index, None)
    _ = collection[0]
    self.assertEqual(
        sorted(collection._index.keys()),
        [0, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192, 9216])

  def testIndexedReads(self):
    collection = self._TestCollection(
        "aff4:/sequential_collection/testIndexedReads")
    data_size = 4 * 1024
    for i in range(data_size):
      collection.Add(rdfvalue.RDFInteger(i))
    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() + rdfvalue.Duration(
        "10m")):
      for i in range(data_size - 1, data_size - 20, -1):
        self.assertEqual(collection[i], i)
      self.assertEqual(collection[1023], 1023)
      self.assertEqual(collection[1024], 1024)
      self.assertEqual(collection[1025], 1025)
      for i in range(data_size - 1020, data_size - 1040, -1):
        self.assertEqual(collection[i], i)

  def testListing(self):
    test_urn = "aff4:/sequential_collection/testIndexedListing"
    collection = self._TestCollection(test_urn)
    timestamps = []
    for i in range(100):
      timestamps.append(collection.Add(rdfvalue.RDFInteger(i)))

    with test_lib.Instrument(sequential_collection.SequentialCollection,
                             "Scan") as scan:
      self.assertEqual(len(list(collection)), 100)
      # Listing should be done using a single scan but there is another one
      # for calculating the length.
      self.assertEqual(scan.call_count, 2)

  def testAutoIndexing(self):

    indexing_done = threading.Event()

    def UpdateIndex(self):
      self.UpdateIndex.old_target(self)
      indexing_done.set()

    # To reduce the time for the test to run, reduce the delays, so that
    # indexing should instantaneously.
    isq = sequential_collection.IndexedSequentialCollection
    biu = sequential_collection.BACKGROUND_INDEX_UPDATER
    with utils.MultiStubber((biu, "INDEX_DELAY", 0),
                            (isq, "INDEX_WRITE_DELAY", rdfvalue.Duration("0s")),
                            (isq, "INDEX_SPACING", 8),
                            (isq, "UpdateIndex", UpdateIndex)):
      collection = self._TestCollection(
          "aff4:/sequential_collection/testAutoIndexing")
      for i in range(2048):
        collection.Add(rdfvalue.RDFInteger(i))

      # Wait for the updater thread to finish the indexing.
      if not indexing_done.wait(timeout=10):
        self.fail("Indexing did not finish in time.")

      _ = collection[0]
      self.assertGreater(len(collection._index), 16)


class GeneralIndexedCollectionTest(test_lib.AFF4ObjectTest):

  def testAddGet(self):
    collection = sequential_collection.GeneralIndexedCollection(
        rdfvalue.RDFURN("aff4:/sequential_collection/testAddGetIndexed"),
        token=self.token)
    collection.Add(rdfvalue.RDFInteger(42))
    collection.Add(rdfvalue.RDFString("the meaning of life"))
    self.assertEqual(collection[0].__class__, rdfvalue.RDFInteger)
    self.assertEqual(collection[0], 42)
    self.assertEqual(collection[1].__class__, rdfvalue.RDFString)
    self.assertEqual(collection[1], "the meaning of life")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
