#!/usr/bin/env python
"""Tests for MultiTypeCollection."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server import multi_type_collection
from grr_response_server.data_stores import fake_data_store
from grr.test_lib import aff4_test_lib

from grr.test_lib import test_lib


class MultiTypeCollectionTest(aff4_test_lib.AFF4ObjectTest):

  def setUp(self):
    super(MultiTypeCollectionTest, self).setUp()
    self.pool = data_store.DB.GetMutationPool()
    self.collection = multi_type_collection.MultiTypeCollection(
        rdfvalue.RDFURN("aff4:/mt_collection/testAddScan"))

  def testWrapsValueInGrrMessageIfNeeded(self):
    with self.pool:
      self.collection.Add(rdfvalue.RDFInteger(42), mutation_pool=self.pool)

    items = list(self.collection)
    self.assertIsInstance(items[0], rdf_flows.GrrMessage)
    self.assertEqual(items[0].payload, 42)

  def testValuesOfSingleTypeAreAddedAndIterated(self):
    with self.pool:
      for i in range(100):
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(i)),
            mutation_pool=self.pool)

    for index, v in enumerate(self.collection):
      self.assertEqual(index, v.payload)

  def testExtractsTypesFromGrrMessage(self):
    with self.pool:
      self.collection.Add(
          rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(0)),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(payload=rdfvalue.RDFString("foo")),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(payload=rdfvalue.RDFURN("aff4:/foo/bar")),
          mutation_pool=self.pool)

    self.assertEqual(
        set([
            rdfvalue.RDFInteger.__name__, rdfvalue.RDFString.__name__,
            rdfvalue.RDFURN.__name__
        ]), set(self.collection.ListStoredTypes()))

  def testStoresEmptyGrrMessage(self):
    with self.pool:
      self.collection.Add(rdf_flows.GrrMessage(), mutation_pool=self.pool)

    self.assertListEqual([rdf_flows.GrrMessage.__name__],
                         list(self.collection.ListStoredTypes()))

  def testValuesOfMultipleTypesCanBeIteratedTogether(self):
    with self.pool:
      original_values = set()
      for i in range(100):
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(i)),
            mutation_pool=self.pool)
        original_values.add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(i)))

        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFString(unicode(i))),
            mutation_pool=self.pool)
        original_values.add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFString(unicode(i))))

    self.assertCountEqual([v.payload for v in original_values],
                          [v.payload for v in self.collection])

  def testLengthOfCollectionIsCorrectWhenMultipleTypesAreUsed(self):
    with self.pool:
      for i in range(100):
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(i)),
            mutation_pool=self.pool)
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFString(unicode(i))),
            mutation_pool=self.pool)

    self.assertLen(self.collection, 200)

  def testValuesOfMultipleTypesCanBeIteratedPerType(self):
    with self.pool:
      for i in range(100):
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(i)),
            mutation_pool=self.pool)
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFString(unicode(i))),
            mutation_pool=self.pool)

    for index, (_, v) in enumerate(
        self.collection.ScanByType(rdfvalue.RDFInteger.__name__)):
      self.assertEqual(index, v.payload)

    for index, (_, v) in enumerate(
        self.collection.ScanByType(rdfvalue.RDFString.__name__)):
      self.assertEqual(str(index), v.payload)

  def testLengthIsReportedCorrectlyForEveryType(self):
    with self.pool:
      for i in range(99):
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(i)),
            mutation_pool=self.pool)

      for i in range(101):
        self.collection.Add(
            rdf_flows.GrrMessage(payload=rdfvalue.RDFString(unicode(i))),
            mutation_pool=self.pool)

    self.assertEqual(99,
                     self.collection.LengthByType(rdfvalue.RDFInteger.__name__))
    self.assertEqual(101,
                     self.collection.LengthByType(rdfvalue.RDFString.__name__))

  def testDeletingCollectionDeletesAllSubcollections(self):
    if not isinstance(data_store.DB, fake_data_store.FakeDataStore):
      self.skipTest("Only supported on FakeDataStore.")
    with self.pool:
      self.collection.Add(
          rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(0)),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(payload=rdfvalue.RDFString("foo")),
          mutation_pool=self.pool)
      self.collection.Add(
          rdf_flows.GrrMessage(payload=rdfvalue.RDFURN("aff4:/foo/bar")),
          mutation_pool=self.pool)

    self.collection.Delete()

    for urn in data_store.DB.subjects:
      self.assertNotIn(utils.SmartStr(self.collection.collection_id), urn)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
