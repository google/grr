#!/usr/bin/env python
"""Test the various collection objects."""


import itertools
import math

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import collections
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict


class TypedRDFValueCollection(collections.RDFValueCollection):
  _rdf_type = rdf_paths.PathSpec


class TestCollections(test_lib.AFF4ObjectTest):

  def testRDFValueCollections(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(urn, "RDFValueCollection",
                             mode="w", token=self.token)

    for i in range(5):
      fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    # Make sure items are stored in order.
    j = 0
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 4)

    for j in range(len(fd)):
      self.assertEqual(fd[j].request_id, j)

    self.assertIsNone(fd[5])

  def testRDFValueCollectionsAppend(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(urn, "RDFValueCollection",
                             mode="w", token=self.token)

    for i in range(5):
      fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, "RDFValueCollection",
                           mode="rw", token=self.token)

    for i in range(5):
      fd.Add(rdf_flows.GrrMessage(request_id=i + 5))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    # Make sure items are stored in order.
    j = 0
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 9)

  def testChunkSize(self):

    urn = "aff4:/test/chunktest"

    fd = aff4.FACTORY.Create(urn, "RDFValueCollection",
                             mode="w", token=self.token)
    fd.SetChunksize(1024 * 1024)

    # Estimate the size of the resulting message.
    msg = rdf_flows.GrrMessage(request_id=100)
    msg_size = len(rdf_protodict.EmbeddedRDFValue(payload=msg)
                   .SerializeToString())
    # Write ~500Kb.
    n = 500 * 1024 / msg_size

    fd.AddAll([rdf_flows.GrrMessage(request_id=i) for i in xrange(n)])

    self.assertEqual(fd.fd.Get(fd.fd.Schema._CHUNKSIZE), 1024 * 1024)
    # There should be 500K of data.
    self.assertGreater(fd.fd.size, 400 * 1024)
    # and there should only be one chunk since 500K is less than the chunk size.
    self.assertEqual(len(fd.fd.chunk_cache._hash), 1)

    fd.Close()

    # Closing the collection empties the chunk_cache.
    self.assertEqual(len(fd.fd.chunk_cache._hash), 0)

    self.assertRaises(ValueError, fd.SetChunksize, (10))

    fd = aff4.FACTORY.Open(urn, "RDFValueCollection",
                           mode="rw", token=self.token)
    self.assertRaises(ValueError, fd.SetChunksize, (2 * 1024 * 1024))

  def testAddingNoneToUntypedCollectionRaises(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(urn, "RDFValueCollection",
                             mode="w", token=self.token)

    self.assertRaises(ValueError, fd.Add, None)
    self.assertRaises(ValueError, fd.AddAll, [None])

  def testAddingNoneViaAddMethodToTypedCollectionWorksCorrectly(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(urn, "TypedRDFValueCollection",
                             mode="w", token=self.token)
    # This works, because Add() accepts keyword arguments and builds _rdf_type
    # instance out of them. In the current case there are no keyword arguments
    # specified, so we get default value.
    fd.Add(None)
    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(len(fd), 1)
    self.assertEqual(fd[0], rdf_paths.PathSpec())

  def testAddingNoneViaAddAllMethodToTypedCollectionRaises(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(urn, "RDFValueCollection",
                             mode="w", token=self.token)

    self.assertRaises(ValueError, fd.AddAll, [None])


class TestPackedVersionedCollection(test_lib.AFF4ObjectTest):
  """Test for PackedVersionedCollection."""

  collection_urn = rdfvalue.RDFURN("aff4:/test/packed_collection")

  def setUp(self):
    super(TestPackedVersionedCollection, self).setUp()

    # For the sake of test's performance, make COMPACTION_BATCH_SIZE and
    # MAX_REVERSED_RESULTS reasonably small.
    self.old_batch_size = aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE
    aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE = 100

    self.old_max_rev = aff4.PackedVersionedCollection.MAX_REVERSED_RESULTS
    aff4.PackedVersionedCollection.MAX_REVERSED_RESULTS = 100

    self.old_index_interval = aff4.PackedVersionedCollection.INDEX_INTERVAL
    aff4.PackedVersionedCollection.INDEX_INTERVAL = 100

  def tearDown(self):
    aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE = self.old_batch_size
    aff4.PackedVersionedCollection.MAX_REVERSED_RESULTS = self.old_max_rev
    aff4.PackedVersionedCollection.INDEX_INTERVAL = self.old_index_interval

    super(TestPackedVersionedCollection, self).tearDown()

  def testAddMethodWritesToVersionedAttributeAndNotToStream(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdf_flows.GrrMessage(request_id=1))

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), 1)

    # Check that no items are stored in the stream
    fd = aff4.FACTORY.Create(self.collection_urn.Add("Stream"), "AFF4Image",
                             mode="rw", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

  def testAddAllMethodWritesToVersionedAttributeAndNotToStream(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.AddAll([rdf_flows.GrrMessage(request_id=1),
                 rdf_flows.GrrMessage(request_id=1)])

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), 2)

    # Check that no items are stored in the stream
    fd = aff4.FACTORY.Create(self.collection_urn.Add("Stream"), "AFF4Image",
                             mode="rw", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

  def testAddToCollectionClassMethodAddsVersionedAttributes(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as _:
      pass

    aff4.PackedVersionedCollection.AddToCollection(
        self.collection_urn, [rdf_flows.GrrMessage(request_id=1),
                              rdf_flows.GrrMessage(request_id=2)],
        token=self.token)

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        self.collection_urn,
        aff4.PackedVersionedCollection.SchemaCls.DATA.predicate,
        token=self.token, timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), 2)

    # Check that no items are stored in the stream
    fd = aff4.FACTORY.Create(self.collection_urn.Add("Stream"), "AFF4Image",
                             mode="rw", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

    # Check that collection reports correct size.
    fd = aff4.FACTORY.Open(self.collection_urn,
                           aff4_type="PackedVersionedCollection",
                           token=self.token)
    self.assertEqual(len(fd), 2)
    self.assertEqual(len(list(fd.GenerateUncompactedItems())), 2)

  def _testRandomAccessEqualsIterator(self):
    # Check that random access works correctly for different age modes.
    for age in [aff4.NEWEST_TIME, aff4.ALL_TIMES]:
      fd = aff4.FACTORY.Open(self.collection_urn, age=age, token=self.token)

      model_data = list(fd.GenerateItems())
      for index, model_item in enumerate(model_data):
        self.assertEqual(fd[index], model_item)

        self.assertListEqual(list(fd.GenerateItems(offset=index)),
                             model_data[index:])

      self.assertFalse(list(fd.GenerateItems(offset=len(model_data))))

  def testUncompactedCollectionIteratesInRightOrderWhenSmall(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(len(list(fd)), 5)
    # Make sure items are stored in correct order.
    for index, item in enumerate(fd):
      self.assertEqual(index, item.request_id)

  def testRandomAccessWorksCorrectlyForSmallUncompactedCollection(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    self._testRandomAccessEqualsIterator()

  def testUncompactedCollectionIteratesInReversedOrderWhenLarge(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(fd.MAX_REVERSED_RESULTS + 1):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(len(list(fd)), fd.MAX_REVERSED_RESULTS + 1)
    # Due to the way uncompacted items are stored, they come back
    # from the data store in reversed order. When there are too
    # many of them, it's too expensive to reverse them, so we
    # give up and return then in reversed order (newest first).
    for index, item in enumerate(reversed(list(fd))):
      self.assertEqual(index, item.request_id)

  def testRandomAccessWorksCorrectlyForLargeUncompactedCollection(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(fd.MAX_REVERSED_RESULTS + 1):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    self._testRandomAccessEqualsIterator()

  def testIteratesOverBothCompactedAndUncompcatedParts(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      for i in range(5, 10):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(len(list(fd)), 10)
    # Make sure items are stored in correct order.
    for index, item in enumerate(fd):
      self.assertEqual(index, item.request_id)

  def testRandomAccessWorksCorrectlyForSemiCompactedCollection(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      fd.Compact()

    self._testRandomAccessEqualsIterator()

  def testIteratesInSemiReversedOrderWhenUncompcatedPartIsLarge(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(
        self.collection_urn, "PackedVersionedCollection",
        token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      for i in range(5, fd.MAX_REVERSED_RESULTS + 6):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    results = list(fd)
    self.assertEqual(len(results), fd.MAX_REVERSED_RESULTS + 6)

    # We have too many uncompacted values. First the compacted values
    # will be iterated in the correct order. Then uncompacted values
    # will be iterated in reversed order (due to the order of
    # results returned by data_store.DB.ResolveRegex - see
    # data_store.py for details).
    index_list = itertools.chain(
        range(5), reversed(range(5, fd.MAX_REVERSED_RESULTS + 6)))
    for i, index in enumerate(index_list):
      self.assertEqual(index, results[i].request_id)

  def testRandomAccessWorksCorrectlyWhenUncompactedPartIsLarge(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(
        self.collection_urn, "PackedVersionedCollection",
        token=self.token) as fd:
      fd.Compact()

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      for i in range(5, fd.MAX_REVERSED_RESULTS + 6):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    self._testRandomAccessEqualsIterator()

  def testRandomAccessWorksCorrectlyForIndexIntervalsFrom1To10(self):
    for index_interval in range(1, 11):
      aff4.PackedVersionedCollection.INDEX_INTERVAL = index_interval

      aff4.FACTORY.Delete(self.collection_urn, token=self.token)
      with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                               mode="w", token=self.token):
        pass

      for i in range(20):
        with aff4.FACTORY.Open(
            self.collection_urn, "PackedVersionedCollection",
            mode="w", token=self.token) as fd:
          fd.Add(rdf_flows.GrrMessage(request_id=i))

        with aff4.FACTORY.OpenWithLock(
            self.collection_urn, "PackedVersionedCollection",
            token=self.token) as fd:
          fd.Compact()

      fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
      self.assertEqual(len(fd.GetIndex()),
                       int(math.ceil(20.0 / index_interval)))
      self._testRandomAccessEqualsIterator()

  def testIndexIsUsedWhenRandomAccessIsUsed(self):
    aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE = 100
    aff4.PackedVersionedCollection.INDEX_INTERVAL = 1

    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token):
      pass

    for i in range(20):
      with aff4.FACTORY.Open(
          self.collection_urn, "PackedVersionedCollection",
          mode="w", token=self.token) as fd:
        fd.Add(rdf_flows.GrrMessage(request_id=i))

      with aff4.FACTORY.OpenWithLock(
          self.collection_urn, "PackedVersionedCollection",
          token=self.token) as fd:
        fd.Compact()

    collection = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    item_size = collection.fd.size / len(collection)

    # There's no seek expected for the first element
    for i in range(1, 20):
      seek_ops = []
      old_seek = collection.fd.Seek
      def SeekStub(offset):
        seek_ops.append(offset)  #  pylint: disable=cell-var-from-loop
        old_seek(offset)  #  pylint: disable=cell-var-from-loop

      # Check that the stream is seeked to a correct byte offset on every
      # GenerateItems() call with an offset specified.
      with utils.Stubber(collection.fd, "Seek", SeekStub):
        _ = list(collection.GenerateItems(offset=i))
        self.assertListEqual([item_size * i], seek_ops)

  def testItemsCanBeAddedToCollectionInWriteOnlyMode(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(
        self.collection_urn, "PackedVersionedCollection",
        token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    # Now add 5 more items in "write-only" mode.
    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="w", token=self.token) as fd:
      for i in range(5, 10):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(fd.CalculateLength(), 10)

    results = list(fd)
    self.assertEqual(len(results), 10)
    for i in range(10):
      self.assertEqual(i, results[i].request_id)

    # Check that compaction works on items added in write-only mode.
    with aff4.FACTORY.OpenWithLock(
        self.collection_urn, "PackedVersionedCollection",
        token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    # Check that everything works as expected after second compaction.
    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(fd.CalculateLength(), 10)

    results = list(fd)
    self.assertEqual(len(results), 10)
    for i in range(10):
      self.assertEqual(i, results[i].request_id)

  def testBooleanBehavior(self):
    collection_urn = rdfvalue.RDFURN("aff4:/bool_test/packed_collection")
    with aff4.FACTORY.Create(collection_urn,
                             "PackedVersionedCollection",
                             mode="rw", token=self.token) as fd:
      self.assertFalse(fd)

      fd.AddAll([rdf_flows.GrrMessage(request_id=i) for i in range(3)])

      self.assertTrue(fd)

    with aff4.FACTORY.OpenWithLock(collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 3)

      self.assertTrue(fd)

    # Check that no items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), 0)

    with aff4.FACTORY.Create(collection_urn,
                             "PackedVersionedCollection",
                             mode="rw", token=self.token) as fd:
      self.assertTrue(fd)

  def _testCompactsCollectionSuccessfully(self, num_elements):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      elements = []
      for i in range(num_elements):
        elements.append(rdf_flows.GrrMessage(request_id=i))
      fd.AddAll(elements)

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), num_elements)

    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, num_elements)

    # Check that no items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), 0)

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(len(list(fd)), num_elements)
    # Make sure items are stored in correct order.
    for index, item in enumerate(fd):
      self.assertEqual(index, item.request_id)

  def testCompactsSmallCollectionSuccessfully(self):
    self._testCompactsCollectionSuccessfully(5)

  def testIndexIsWritteAfterFirstCompaction(self):
    self._testCompactsCollectionSuccessfully(5)

    collection = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                                   token=self.token)
    index = collection.GetIndex()
    self.assertEqual(len(index), 1)
    self.assertEqual(index[0], (5, collection.fd.size))

  def testCompactsLargeCollectionSuccessfully(self):
    # When number of versioned attributes is too big, compaction
    # happens in batches. Ensure that 2 batches are created.
    self._testCompactsCollectionSuccessfully(
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1)

  def testIndexIsWrittenPerCompactionBatchIfIndexIntervalEqualToBatchSize(self):
    # Index is supposed to be updated every time a compaction batch is written.
    # Index only gets updated if it's empty or more than INDEX_INTERVAL elements
    # got written into the stream.
    #
    # In the current test INDEX_INTERVAL is equal to COMPACTION_BATCH_SIZE. The
    # batches are written in reversed order. So it will be first updated after
    # the batch with 1 element is written and then after a btach with
    # COMPACTION_BATCH_SIZE elements is written.
    self._testCompactsCollectionSuccessfully(
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1)

    collection = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                                   token=self.token)
    index = collection.GetIndex()
    index.reverse()

    self.assertEqual(len(index), 2)

    self.assertEqual(index[0], (1, collection.fd.size / (
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1)))
    self.assertEqual(index[1], (
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1,
        collection.fd.size))

  def testIndexIsWrittenAtMostOncePerCompactionBatch(self):
    aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE = 100
    aff4.PackedVersionedCollection.INDEX_INTERVAL = 1

    self._testCompactsCollectionSuccessfully(
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1)

    collection = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                                   token=self.token)
    index = collection.GetIndex()
    index.reverse()

    # Even though index interval is 1, it gets updated only when each
    # compaction batch is written to a stream.
    self.assertEqual(len(index), 2)

    self.assertEqual(index[0], (1, collection.fd.size / (
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1)))
    self.assertEqual(index[1], (
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1,
        collection.fd.size))

  def testCompactsVeryLargeCollectionSuccessfully(self):
    # When number of versioned attributes is too big, compaction
    # happens in batches. Ensure that 5 batches are created.
    self._testCompactsCollectionSuccessfully(
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE * 5 - 1)

  def testSecondCompactionDoesNothing(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    # On second attempt, nothing should get compacted.
    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 0)

  def testSecondCompactionDoesNotUpdateIndex(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      fd.Compact()
      self.assertEqual(len(fd.GetIndex()), 1)

    # Second compaction did not update the index.
    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      fd.Compact()
      self.assertEqual(len(fd.GetIndex()), 1)

  def testSecondCompactionOfLargeCollectionDoesNothing(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(fd.COMPACTION_BATCH_SIZE + 1):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, fd.COMPACTION_BATCH_SIZE + 1)

    # On second attempt, nothing should get compacted.
    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 0)

  def testSecondCompactionofLargeCollectionDoesNotUpdateIndex(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(fd.COMPACTION_BATCH_SIZE + 1):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      fd.Compact()
      self.assertEqual(len(fd.GetIndex()), 2)

    # Second compaction did not update the index.
    with aff4.FACTORY.OpenWithLock(self.collection_urn,
                                   "PackedVersionedCollection",
                                   token=self.token) as fd:
      fd.Compact()
      self.assertEqual(len(fd.GetIndex()), 2)

  def testTimestampsArePreservedAfterCompaction(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        with test_lib.FakeTime(i * 1000):
          fd.Add(rdf_flows.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    for index, item in enumerate(fd):
      self.assertEqual(int(item.age.AsSecondsFromEpoch()), 1000 * index)

    with aff4.FACTORY.OpenWithLock(
        self.collection_urn, "PackedVersionedCollection",
        token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    for index, item in enumerate(fd):
      self.assertEqual(int(item.age.AsSecondsFromEpoch()), 1000 * index)

  def testItemsAddedWhileCompactionIsInProgressAreNotDeleted(self):
    with test_lib.FakeTime(0):
      fd = aff4.FACTORY.Create(self.collection_urn,
                               "PackedVersionedCollection",
                               mode="w", token=self.token)
    for i in range(4):
      with test_lib.FakeTime(i * 1000):
        fd.Add(rdf_flows.GrrMessage(request_id=i))

    with test_lib.FakeTime(3000):
      fd.Close()

    with test_lib.FakeTime(3500):
      fd = aff4.FACTORY.OpenWithLock(self.collection_urn,
                                     "PackedVersionedCollection",
                                     token=self.token)

    # Imitating that another element was added in parallel while compaction
    # is in progress.
    with test_lib.FakeTime(4000):
      with aff4.FACTORY.Create(self.collection_urn,
                               "PackedVersionedCollection",
                               mode="rw", token=self.token) as write_fd:
        write_fd.Add(rdf_flows.GrrMessage(request_id=4))

    with test_lib.FakeTime(3500):
      num_compacted = fd.Compact()
      fd.Close()

    # One item should be left uncompacted as its' timestamp is 4000,
    # i.e. it was added after the compaction started.
    self.assertEqual(num_compacted, 4)

    # Check that one uncompacted item was left (see the comment above).
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), 1)

    # Check that collection is still properly enumerated and reports the
    # correct size.
    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(fd.CalculateLength(), 5)
    for index, item in enumerate(fd):
      self.assertEqual(int(item.age.AsSecondsFromEpoch()), 1000 * index)

  def testExtendsLeaseIfCompactionTakesTooLong(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      elements = []
      for i in range(10):
        elements.append(rdf_flows.GrrMessage(request_id=i))
      fd.AddAll(elements)

    config_lib.CONFIG.Set("Worker.compaction_lease_time", 42)

    with test_lib.FakeTime(20):
      # Lease time here is much less than compaction_lease_time,
      # collection will have to extend the lease immediately
      # when compaction starts.
      fd = aff4.FACTORY.OpenWithLock(self.collection_urn,
                                     "PackedVersionedCollection",
                                     lease_time=10, token=self.token)

      # This is the expected lease time: time.time() + lease_time
      self.assertEqual(fd.CheckLease(), 10)

    with test_lib.FakeTime(29):
      fd.Compact()
      # Compaction should have updated the lease.
      self.assertEqual(fd.CheckLease(), 42)

  def testNoJournalEntriesAreAddedWhenJournalingIsDisabled(self):
    config_lib.CONFIG.Set(
        "Worker.enable_packed_versioned_collection_journaling", False)

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdf_flows.GrrMessage(request_id=42))
      fd.AddAll([rdf_flows.GrrMessage(request_id=43),
                 rdf_flows.GrrMessage(request_id=44)])

    aff4.PackedVersionedCollection.AddToCollection(
        self.collection_urn, [rdf_flows.GrrMessage(request_id=1),
                              rdf_flows.GrrMessage(request_id=2)],
        token=self.token)

    with aff4.FACTORY.OpenWithLock(self.collection_urn, token=self.token) as fd:
      fd.Compact()

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    self.assertFalse(fd.IsAttributeSet(fd.Schema.ADDITION_JOURNAL))
    self.assertFalse(fd.IsAttributeSet(fd.Schema.COMPACTION_JOURNAL))

  def _EnableJournaling(self):
    config_lib.CONFIG.Set(
        "Worker.enable_packed_versioned_collection_journaling", True)

  def testJournalEntryIsAddedAfterSingeAddCall(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdf_flows.GrrMessage(request_id=42))

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = list(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL))
    self.assertEqual(len(addition_journal), 1)
    self.assertEqual(addition_journal[0], 1)

  def testTwoJournalEntriesAreAddedAfterTwoConsecutiveAddCalls(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdf_flows.GrrMessage(request_id=42))
      fd.Add(rdf_flows.GrrMessage(request_id=43))

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = sorted(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL),
        key=lambda x: x.age)
    self.assertEqual(len(addition_journal), 2)
    self.assertEqual(addition_journal[0], 1)
    self.assertEqual(addition_journal[1], 1)

  def testTwoJournalEntriesAreAddedAfterAddCallsSeparatedByFlush(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdf_flows.GrrMessage(request_id=42))

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdf_flows.GrrMessage(request_id=43))

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = sorted(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL),
        key=lambda x: x.age)
    self.assertEqual(len(addition_journal), 2)
    self.assertEqual(addition_journal[0], 1)
    self.assertEqual(addition_journal[1], 1)

  def testJournalEntryIsAddedAfterSingleAddAllCall(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      elements = []
      for i in range(10):
        elements.append(rdf_flows.GrrMessage(request_id=i))
      fd.AddAll(elements)

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = list(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL))
    self.assertEqual(len(addition_journal), 1)
    self.assertEqual(addition_journal[0], 10)

  def testTwoJournalEntriesAreAddedAfterTwoConsecutiveAddAllCall(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      elements = []
      for i in range(10):
        elements.append(rdf_flows.GrrMessage(request_id=i))
      fd.AddAll(elements)
      fd.AddAll(elements[:5])

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = sorted(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL),
        key=lambda x: x.age)
    self.assertEqual(len(addition_journal), 2)
    self.assertEqual(addition_journal[0], 10)
    self.assertEqual(addition_journal[1], 5)

  def testTwoJournalEntriesAreAddedAfterTwoAddAllCallsSeparatedByFlush(self):
    self._EnableJournaling()

    elements = []
    for i in range(10):
      elements.append(rdf_flows.GrrMessage(request_id=i))

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.AddAll(elements)

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.AddAll(elements[:5])

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = sorted(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL),
        key=lambda x: x.age)
    self.assertEqual(len(addition_journal), 2)
    self.assertEqual(addition_journal[0], 10)
    self.assertEqual(addition_journal[1], 5)

  def testJournalEntryIsAddedAfterSingleAddToCollectionCall(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as _:
      pass

    aff4.PackedVersionedCollection.AddToCollection(
        self.collection_urn, [rdf_flows.GrrMessage(request_id=1),
                              rdf_flows.GrrMessage(request_id=2)],
        token=self.token)
    fd = aff4.FACTORY.Open(self.collection_urn,
                           age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = list(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL))
    self.assertEqual(len(addition_journal), 1)
    self.assertEqual(addition_journal[0], 2)

  def testTwoJournalEntriesAreAddedAfterTwoAddToCollectionCalls(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as _:
      pass

    aff4.PackedVersionedCollection.AddToCollection(
        self.collection_urn, [rdf_flows.GrrMessage(request_id=1),
                              rdf_flows.GrrMessage(request_id=2)],
        token=self.token)
    aff4.PackedVersionedCollection.AddToCollection(
        self.collection_urn, [rdf_flows.GrrMessage(request_id=3)],
        token=self.token)

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    addition_journal = sorted(
        fd.GetValuesForAttribute(fd.Schema.ADDITION_JOURNAL),
        key=lambda x: x.age)
    self.assertEqual(len(addition_journal), 2)
    self.assertEqual(addition_journal[0], 2)
    self.assertEqual(addition_journal[1], 1)

  def testJournalEntryIsAddedAfterSingleCompaction(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.AddAll([rdf_flows.GrrMessage(request_id=42),
                 rdf_flows.GrrMessage(request_id=42)])

    with aff4.FACTORY.OpenWithLock(self.collection_urn, token=self.token) as fd:
      fd.Compact()

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    compaction_journal = list(
        fd.GetValuesForAttribute(fd.Schema.COMPACTION_JOURNAL))
    self.assertEqual(len(compaction_journal), 1)
    self.assertEqual(compaction_journal[0], 2)

  def testTwoJournalEntriesAreAddedAfterTwoCompactions(self):
    self._EnableJournaling()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.AddAll([rdf_flows.GrrMessage(request_id=42),
                 rdf_flows.GrrMessage(request_id=42)])

    with aff4.FACTORY.OpenWithLock(self.collection_urn, token=self.token) as fd:
      fd.Compact()

    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.AddAll([rdf_flows.GrrMessage(request_id=42)])

    with aff4.FACTORY.OpenWithLock(self.collection_urn, token=self.token) as fd:
      fd.Compact()

    fd = aff4.FACTORY.Open(self.collection_urn, age=aff4.ALL_TIMES,
                           token=self.token)
    compaction_journal = sorted(
        fd.GetValuesForAttribute(fd.Schema.COMPACTION_JOURNAL),
        key=lambda x: x.age)
    self.assertEqual(len(compaction_journal), 2)
    self.assertEqual(compaction_journal[0], 2)
    self.assertEqual(compaction_journal[1], 1)
