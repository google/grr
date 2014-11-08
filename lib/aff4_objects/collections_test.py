#!/usr/bin/env python
"""Test the various collection objects."""


import itertools

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import collections


class TypedRDFValueCollection(collections.RDFValueCollection):
  _rdf_type = rdfvalue.PathSpec


class TestCollections(test_lib.AFF4ObjectTest):

  def testRDFValueCollections(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(urn, "RDFValueCollection",
                             mode="w", token=self.token)

    for i in range(5):
      fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    # Make sure items are stored in order.
    j = 0
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 4)

  def testRDFValueCollectionsAppend(self):
    urn = "aff4:/test/collection"
    fd = aff4.FACTORY.Create(urn, "RDFValueCollection",
                             mode="w", token=self.token)

    for i in range(5):
      fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, "RDFValueCollection",
                           mode="rw", token=self.token)

    for i in range(5):
      fd.Add(rdfvalue.GrrMessage(request_id=i+5))

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
    msg = rdfvalue.GrrMessage(request_id=100)
    msg_size = len(rdfvalue.EmbeddedRDFValue(payload=msg).SerializeToString())
    # Write ~500Kb.
    n = 500 * 1024 / msg_size

    fd.AddAll([rdfvalue.GrrMessage(request_id=i) for i in xrange(n)])

    self.assertEqual(fd.fd.Get(fd.fd.Schema._CHUNKSIZE), 1024*1024)
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
    self.assertEqual(fd[0], rdfvalue.PathSpec())

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

  def tearDown(self):
    aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE = self.old_batch_size
    aff4.PackedVersionedCollection.MAX_REVERSED_RESULTS = self.old_max_rev

    super(TestPackedVersionedCollection, self).tearDown()

  def testAddMethodWritesToVersionedAttributeAndNotToStream(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdfvalue.GrrMessage(request_id=1))

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
      fd.AddAll([rdfvalue.GrrMessage(request_id=1),
                 rdfvalue.GrrMessage(request_id=1)])

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), 2)

    # Check that no items are stored in the stream
    fd = aff4.FACTORY.Create(self.collection_urn.Add("Stream"), "AFF4Image",
                             mode="rw", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

  def testUncompactedCollectionIteratesInRightOrderWhenSmall(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(len(list(fd)), 5)
    # Make sure items are stored in correct order.
    for index, item in enumerate(fd):
      self.assertEqual(index, item.request_id)

  def testUncompactedCollectionIteratesInReversedOrderWhenLarge(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(fd.MAX_REVERSED_RESULTS + 1):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(len(list(fd)), fd.MAX_REVERSED_RESULTS + 1)
    # Due to the way uncompacted items are stored, they come back
    # from the data store in reversed order. When there are too
    # many of them, it's too expensive to reverse them, so we
    # give up and return then in reversed order (newest first).
    for index, item in enumerate(reversed(list(fd))):
      self.assertEqual(index, item.request_id)

  def testIteratesOverBothCompactedAndUncompcatedParts(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      for i in range(5, 10):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(len(list(fd)), 10)
    # Make sure items are stored in correct order.
    for index, item in enumerate(fd):
      self.assertEqual(index, item.request_id)

  def testIteratesInSemiReversedOrderWhenUncompcatedPartIsLarge(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      for i in range(5, fd.MAX_REVERSED_RESULTS + 6):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

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

  def testItemsCanBeAddedToCollectionInWriteOnlyMode(self):
    with aff4.FACTORY.Create(self.collection_urn, "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    # Now add 5 more items in "write-only" mode.
    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="w", token=self.token) as fd:
      for i in range(5, 10):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    self.assertEqual(fd.CalculateLength(), 10)

    results = list(fd)
    self.assertEqual(len(results), 10)
    for i in range(10):
      self.assertEqual(i, results[i].request_id)

    # Check that compaction works on items added in write-only mode.
    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
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

      fd.AddAll([rdfvalue.GrrMessage(request_id=i) for i in range(3)])

      self.assertTrue(fd)

    with aff4.FACTORY.Create(collection_urn,
                             "PackedVersionedCollection",
                             mode="rw", token=self.token) as fd:
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
        elements.append(rdfvalue.GrrMessage(request_id=i))
      fd.AddAll(elements)

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveRegex(
        fd.urn, fd.Schema.DATA.predicate, token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))
    self.assertEqual(len(items), num_elements)

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
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

  def testCompactsLargeCollectionSuccessfully(self):
    # When number of versioned attributes is too big, compaction
    # happens in batches. Ensure that 2 batches are created.
    self._testCompactsCollectionSuccessfully(
        aff4.PackedVersionedCollection.COMPACTION_BATCH_SIZE + 1)

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
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 5)

    # On second attempt, nothing should get compacted.
    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 0)

  def testSecondCompactionOfLargeCollectionDoesNothing(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(fd.COMPACTION_BATCH_SIZE + 1):
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, fd.COMPACTION_BATCH_SIZE + 1)

    # On second attempt, nothing should get compacted.
    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
      num_compacted = fd.Compact()
      self.assertEqual(num_compacted, 0)

  def testTimestampsArePreservedAfterCompaction(self):
    with aff4.FACTORY.Create(self.collection_urn,
                             "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      for i in range(5):
        with test_lib.FakeTime(i * 1000):
          fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd = aff4.FACTORY.Open(self.collection_urn, token=self.token)
    for index, item in enumerate(fd):
      self.assertEqual(int(item.age.AsSecondsFromEpoch()), 1000 * index)

    with aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                           mode="rw", token=self.token) as fd:
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
        fd.Add(rdfvalue.GrrMessage(request_id=i))

    with test_lib.FakeTime(3000):
      fd.Close()

    with test_lib.FakeTime(3500):
      fd = aff4.FACTORY.Open(self.collection_urn, "PackedVersionedCollection",
                             mode="rw", token=self.token)

    # Imitating that another element was added in parallel while compaction
    # is in progress.
    with test_lib.FakeTime(4000):
      with aff4.FACTORY.Create(self.collection_urn,
                               "PackedVersionedCollection",
                               mode="rw", token=self.token) as write_fd:
        write_fd.Add(rdfvalue.GrrMessage(request_id=4))

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
