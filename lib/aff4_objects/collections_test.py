#!/usr/bin/env python
"""Test the various collection objects."""


from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestCollections(test_lib.FlowTestsBaseclass):

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
