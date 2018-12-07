#!/usr/bin/env python
"""Tests for SequentialCollection and related subclasses."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading
import time


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iterkeys

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import data_store
from grr_response_server import sequential_collection
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class TestSequentialCollection(sequential_collection.SequentialCollection):
  RDF_TYPE = rdfvalue.RDFInteger


class SequentialCollectionTest(aff4_test_lib.AFF4ObjectTest):

  def _TestCollection(self, collection_id):
    return TestSequentialCollection(rdfvalue.RDFURN(collection_id))

  def testAddScan(self):
    collection = self._TestCollection("aff4:/sequential_collection/testAddScan")
    with data_store.DB.GetMutationPool() as pool:
      for i in range(100):
        collection.Add(rdfvalue.RDFInteger(i), mutation_pool=pool)

    i = 0
    last_ts = 0
    for (ts, v) in collection.Scan():
      last_ts = ts
      self.assertEqual(i, v)
      i += 1

    with data_store.DB.GetMutationPool() as pool:
      for j in range(100):
        collection.Add(rdfvalue.RDFInteger(j + 100), mutation_pool=pool)

    for (ts, v) in collection.Scan(after_timestamp=last_ts):
      self.assertEqual(i, v)
      i += 1

    self.assertEqual(i, 200)

  def testDuplicateTimestamps(self):
    collection = self._TestCollection(
        "aff4:/sequential_collection/testDuplicateTimestamps")
    t = rdfvalue.RDFDatetime.Now()
    with data_store.DB.GetMutationPool() as pool:
      for i in range(10):
        ts = collection.Add(
            rdfvalue.RDFInteger(i), timestamp=t, mutation_pool=pool)
        self.assertEqual(ts[0], t)

    i = 0
    for (ts, _) in collection.Scan():
      self.assertEqual(ts, t)
      i += 1
    self.assertEqual(i, 10)

  def testMultiResolve(self):
    collection = self._TestCollection("aff4:/sequential_collection/testAddScan")
    records = []
    with data_store.DB.GetMutationPool() as pool:
      for i in range(100):
        ts, suffix = collection.Add(rdfvalue.RDFInteger(i), mutation_pool=pool)
        records.append(
            data_store.Record(
                queue_id=collection.collection_id,
                timestamp=ts,
                suffix=suffix,
                subpath="Results",
                value=None))

    even_results = sorted([r for r in collection.MultiResolve(records[::2])])
    self.assertLen(even_results, 50)
    self.assertEqual(even_results[0], 0)
    self.assertEqual(even_results[49], 98)

  def testDelete(self):
    collection = self._TestCollection("aff4:/sequential_collection/testDelete")
    with data_store.DB.GetMutationPool() as pool:
      for i in range(100):
        collection.Add(rdfvalue.RDFInteger(i), mutation_pool=pool)

    collection.Delete()

    collection = self._TestCollection("aff4:/sequential_collection/testDelete")
    for _ in collection.Scan():
      self.fail("Deleted and recreated SequentialCollection should be empty")


class TestIndexedSequentialCollection(
    sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdfvalue.RDFInteger


class IndexedSequentialCollectionTest(aff4_test_lib.AFF4ObjectTest):

  def _TestCollection(self, collection_id):
    return TestIndexedSequentialCollection(rdfvalue.RDFURN(collection_id))

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
    self.worker_thread = threading.Thread(target=biu.UpdateLoop)
    self.worker_thread.daemon = True
    self.worker_thread.start()

  def tearDown(self):
    super(IndexedSequentialCollectionTest, self).tearDown()
    sequential_collection.BACKGROUND_INDEX_UPDATER.ExitNow()
    self.worker_thread.join()

  def testAddGet(self):
    collection = self._TestCollection("aff4:/sequential_collection/testAddGet")
    self.assertEqual(collection.CalculateLength(), 0)
    with data_store.DB.GetMutationPool() as pool:
      for i in range(100):
        collection.Add(rdfvalue.RDFInteger(i), mutation_pool=pool)
    for i in range(100):
      self.assertEqual(collection[i], i)

    self.assertEqual(collection.CalculateLength(), 100)
    self.assertLen(collection, 100)

  def testStaticAddGet(self):
    aff4_path = "aff4:/sequential_collection/testStaticAddGet"
    collection = self._TestCollection(aff4_path)
    self.assertEqual(collection.CalculateLength(), 0)
    with data_store.DB.GetMutationPool() as pool:
      for i in range(100):
        TestIndexedSequentialCollection.StaticAdd(
            rdfvalue.RDFURN(aff4_path),
            rdfvalue.RDFInteger(i),
            mutation_pool=pool)
    for i in range(100):
      self.assertEqual(collection[i], i)

    self.assertEqual(collection.CalculateLength(), 100)
    self.assertLen(collection, 100)

  def testIndexCreate(self):
    spacing = 10
    with utils.Stubber(sequential_collection.IndexedSequentialCollection,
                       "INDEX_SPACING", spacing):

      urn = "aff4:/sequential_collection/testIndexCreate"
      collection = self._TestCollection(urn)
      # TODO(amoser): Without using a mutation pool, this test is really
      # slow on MySQL data store.
      with data_store.DB.GetMutationPool() as pool:
        for i in range(10 * spacing):
          collection.StaticAdd(urn, rdfvalue.RDFInteger(i), mutation_pool=pool)

      # It is too soon to build an index, check that we don't.
      self.assertEqual(collection._index, None)
      self.assertEqual(collection.CalculateLength(), 10 * spacing)
      self.assertEqual(list(iterkeys(collection._index)), [0])

      now = time.time() * 1e6
      twenty_seconds_ago = (time.time() - 20) * 1e6

      # Push the clock forward 10m, and we should build an index on access.
      with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                             rdfvalue.Duration("10m")):
        # Read from start doesn't rebuild index (lazy rebuild)
        _ = collection[0]
        self.assertEqual(list(iterkeys(collection._index)), [0])

        self.assertEqual(collection.CalculateLength(), 10 * spacing)
        self.assertEqual(
            sorted(iterkeys(collection._index)),
            [i * spacing for i in range(10)])
        for index in collection._index:
          if not index:
            continue
          timestamp, suffix = collection._index[index]
          self.assertLessEqual(twenty_seconds_ago, timestamp)
          self.assertLessEqual(timestamp, now)
          self.assertBetween(suffix, 0, 0xFFFFFF)

      # Now check that the index was persisted to aff4 by re-opening
      # and checking that a read from head does load full index
      # (optimistic load):

      collection = self._TestCollection(
          "aff4:/sequential_collection/testIndexCreate")
      self.assertEqual(collection._index, None)
      _ = collection[0]
      self.assertEqual(
          sorted(iterkeys(collection._index)), [i * spacing for i in range(10)])
      for index in collection._index:
        if not index:
          continue
        timestamp, suffix = collection._index[index]
        self.assertLessEqual(twenty_seconds_ago, timestamp)
        self.assertLessEqual(timestamp, now)
        self.assertBetween(suffix, 0, 0xFFFFFF)

  def testIndexedReads(self):
    spacing = 10
    with utils.Stubber(sequential_collection.IndexedSequentialCollection,
                       "INDEX_SPACING", spacing):
      urn = "aff4:/sequential_collection/testIndexedReads"
      collection = self._TestCollection(urn)
      data_size = 4 * spacing
      # TODO(amoser): Without using a mutation pool, this test is really
      # slow on MySQL data store.
      with data_store.DB.GetMutationPool() as pool:
        for i in range(data_size):
          collection.StaticAdd(
              rdfvalue.RDFURN(urn), rdfvalue.RDFInteger(i), mutation_pool=pool)
      with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                             rdfvalue.Duration("10m")):
        for i in range(data_size - 1, data_size - 20, -1):
          self.assertEqual(collection[i], i)
        for i in [spacing - 1, spacing, spacing + 1]:
          self.assertEqual(collection[i], i)
        for i in range(data_size - spacing + 5, data_size - spacing - 5, -1):
          self.assertEqual(collection[i], i)

  def testListing(self):
    test_urn = "aff4:/sequential_collection/testIndexedListing"
    collection = self._TestCollection(test_urn)
    timestamps = []
    with data_store.DB.GetMutationPool() as pool:
      for i in range(100):
        timestamps.append(
            collection.Add(rdfvalue.RDFInteger(i), mutation_pool=pool))

    with test_lib.Instrument(sequential_collection.SequentialCollection,
                             "Scan") as scan:
      self.assertLen(list(collection), 100)
      # Listing should be done using a single scan but there is another one
      # for calculating the length.
      self.assertEqual(scan.call_count, 2)

  def testAutoIndexing(self):

    indexing_done = threading.Event()

    def UpdateIndex(_):
      indexing_done.set()

    # To reduce the time for the test to run, reduce the delays, so that
    # indexing should happen instantaneously.
    isq = sequential_collection.IndexedSequentialCollection
    biu = sequential_collection.BACKGROUND_INDEX_UPDATER
    with utils.MultiStubber((biu, "INDEX_DELAY", 0),
                            (isq, "INDEX_WRITE_DELAY", rdfvalue.Duration("0s")),
                            (isq, "INDEX_SPACING", 8),
                            (isq, "UpdateIndex", UpdateIndex)):
      urn = "aff4:/sequential_collection/testAutoIndexing"
      collection = self._TestCollection(urn)
      # TODO(amoser): Without using a mutation pool, this test is really
      # slow on MySQL data store.
      with data_store.DB.GetMutationPool() as pool:
        for i in range(2048):
          collection.StaticAdd(
              rdfvalue.RDFURN(urn), rdfvalue.RDFInteger(i), mutation_pool=pool)

      # Wait for the updater thread to finish the indexing.
      if not indexing_done.wait(timeout=10):
        self.fail("Indexing did not finish in time.")


class GeneralIndexedCollectionTest(aff4_test_lib.AFF4ObjectTest):

  def testAddGet(self):
    collection = sequential_collection.GeneralIndexedCollection(
        rdfvalue.RDFURN("aff4:/sequential_collection/testAddGetIndexed"))
    with data_store.DB.GetMutationPool() as pool:
      collection.Add(rdfvalue.RDFInteger(42), mutation_pool=pool)
      collection.Add(
          rdfvalue.RDFString("the meaning of life"), mutation_pool=pool)
    self.assertEqual(collection[0].__class__, rdfvalue.RDFInteger)
    self.assertEqual(collection[0], 42)
    self.assertEqual(collection[1].__class__, rdfvalue.RDFString)
    self.assertEqual(collection[1], "the meaning of life")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
