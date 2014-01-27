#!/usr/bin/env python
"""Test the various collection objects."""


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

  def testVersionedCollection(self):
    urn = "aff4:/test/versioned_collection"
    fd = aff4.FACTORY.Create(urn, "VersionedCollection",
                             mode="w", token=self.token)

    for i in range(5):
      item = rdfvalue.GrrMessage(request_id=i, age=i*1e8 + 1)
      fd.Add(item)

    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    j = 0

    # Make sure items are stored in order.
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 4)

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveMulti(
        fd.urn, [fd.Schema.DATA.predicate], token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))

    self.assertEqual(len(items), 5)

    # This should only select message 2, 3, and 4.
    x = None

    # Make sure items are stored in order.
    for j, x in enumerate(fd.GenerateItems(timestamp=(1.1e8, 4.1e8))):
      self.assertEqual(j + 2, x.request_id)

    self.assertAlmostEqual(int(x.age), 4e8 + 1)

  def testPackedVersionedCollection(self):
    urn = "aff4:/test/packed_collection"
    fd = aff4.FACTORY.Create(urn, "PackedVersionedCollection",
                             mode="w", token=self.token)
    for i in range(5):
      fd.Add(rdfvalue.GrrMessage(request_id=i))

    fd.Close()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    j = 0

    # Make sure items are stored in order.
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 4)

    # In a PackedVersionedCollection the size represents only the packed number
    # of records.
    self.assertEqual(fd.size, 0)

    # Check that items are stored in the versions.
    items = list(data_store.DB.ResolveMulti(
        fd.urn, [fd.Schema.DATA.predicate], token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))

    self.assertEqual(len(items), 5)

    # Run the compactor.
    for _ in test_lib.TestFlowHelper("PackedVersionedCollectionCompactor",
                                     token=self.token):
      pass

    fd = aff4.FACTORY.Open(urn, token=self.token)
    j = 0
    # Make sure items are stored in order.
    for j, x in enumerate(fd):
      self.assertEqual(j, x.request_id)

    self.assertEqual(j, 4)

    # Check that no items are stored in the versions.
    items = list(data_store.DB.ResolveMulti(
        fd.urn, [fd.Schema.DATA.predicate], token=self.token,
        timestamp=data_store.DB.ALL_TIMESTAMPS))

    self.assertEqual(len(items), 0)

    # In a PackedVersionedCollection the size represents only the packed number
    # of records.
    self.assertEqual(fd.size, 5)

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
