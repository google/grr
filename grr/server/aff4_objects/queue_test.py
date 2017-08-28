#!/usr/bin/env python
"""Tests for Queue."""

from grr.lib import flags
from grr.lib import rdfvalue
from grr.server import aff4
from grr.server import data_store
from grr.server.aff4_objects import queue as aff4_queue
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class TestQueue(aff4_queue.Queue):
  rdf_type = rdfvalue.RDFInteger


class QueueTest(aff4_test_lib.AFF4ObjectTest):

  def setUp(self):
    super(QueueTest, self).setUp()
    self.pool = data_store.DB.GetMutationPool(token=self.token)

  def testClaimReturnsRecordsInOrder(self):
    queue_urn = "aff4:/queue_test/testClaimReturnsRecordsInOrder"
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

      data_store.DB.Flush()

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results = queue.ClaimRecords()

    self.assertEqual(100, len(results))
    self.assertEqual(0, results[0][1])
    self.assertEqual(99, results[99][1])

  def testClaimIgnoresClaimedRecords(self):
    queue_urn = "aff4:/queue_test/testClaimReturnsRecordsInOrder"
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

      data_store.DB.Flush()

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results = queue.ClaimRecords()

    self.assertEqual(100, len(results))

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      no_results = queue.ClaimRecords()
    self.assertEqual(0, len(no_results))

  def testClaimReturnsPreviouslyClaimedRecordsAfterTimeout(self):
    queue_urn = (
        "aff4:/queue_test/testClaimReturnsPreviouslyClaimedRecordsAfterTimeout")
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

      data_store.DB.Flush()

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results_1 = queue.ClaimRecords()

    self.assertEqual(100, len(results_1))

    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                           rdfvalue.Duration("45m")):
      with aff4.FACTORY.OpenWithLock(
          queue_urn, lease_time=200, token=self.token) as queue:
        results_2 = queue.ClaimRecords()
        self.assertEqual(100, len(results_2))

  def testDeleteRemovesRecords(self):
    queue_urn = "aff4:/queue_test/testDeleteRemovesRecords"
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

      data_store.DB.Flush()

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results = queue.ClaimRecords()

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      queue.DeleteRecord(results[0][0], token=self.token)
      queue.DeleteRecords(
          [record_id for (record_id, _) in results][1:], token=self.token)

    # Wait past the default claim length, to make sure that delete actually did
    # something.
    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                           rdfvalue.Duration("45m")):
      with aff4.FACTORY.OpenWithLock(
          queue_urn, lease_time=200, token=self.token) as queue:
        results = queue.ClaimRecords()
        self.assertEqual(0, len(results))

  def testClaimReturnsPreviouslyReleasedRecords(self):
    queue_urn = "aff4:/queue_test/testClaimReturnsPreviouslyReleasedRecords"
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

      data_store.DB.Flush()

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results = queue.ClaimRecords()
      odd_ids = [
          record_id for (record_id, value) in results if int(value) % 2 == 1
      ]
      queue.ReleaseRecord(odd_ids[0], token=self.token)
      queue.ReleaseRecords(odd_ids[1:], token=self.token)

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      odd_results = queue.ClaimRecords()

    self.assertEqual(50, len(odd_results))
    self.assertEqual(1, odd_results[0][1])
    self.assertEqual(99, odd_results[49][1])

  def testClaimFiltersRecordsIfFilterIsSpecified(self):
    queue_urn = "aff4:/queue_test/testClaimFiltersRecordsIfFilterIsSpecified"
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

    # Filters all even records.
    def EvenFilter(i):
      return int(i) % 2 == 0

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results = queue.ClaimRecords(record_filter=EvenFilter)

    # Should have all the odd records.
    self.assertEqual(50, len(results))
    self.assertEqual(1, results[0][1])
    self.assertEqual(99, results[49][1])

  def testClaimFiltersByStartTime(self):
    queue_urn = "aff4:/queue_test/testClaimFiltersByStartTime"
    middle = None
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          if i == 50:
            middle = rdfvalue.RDFDatetime.Now()
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results = queue.ClaimRecords(start_time=middle)

    self.assertEqual(50, len(results))
    self.assertEqual(50, results[0][1])

  def testClaimCleansSpuriousLocks(self):
    queue_urn = "aff4:/queue_test/testClaimCleansSpuriousLocks"
    with self.pool:
      with aff4.FACTORY.Create(queue_urn, TestQueue, token=self.token) as queue:
        for i in range(100):
          queue.Add(rdfvalue.RDFInteger(i), mutation_pool=self.pool)

    data_store.DB.Flush()

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      results = queue.ClaimRecords()
    self.assertEqual(100, len(results))

    for subject, _ in results:
      data_store.DB.DeleteAttributes(
          subject, [data_store.DataStore.COLLECTION_ATTRIBUTE],
          sync=True,
          token=self.token)
    data_store.DB.Flush()

    self.assertEqual(100,
                     sum(1
                         for _ in data_store.DB.ScanAttribute(
                             queue.urn.Add("Records"),
                             data_store.DataStore.QUEUE_LOCK_ATTRIBUTE,
                             token=self.token)))

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      queue.ClaimRecords()
    data_store.DB.Flush()

    self.assertEqual(0,
                     sum(1
                         for _ in data_store.DB.ScanAttribute(
                             queue.urn.Add("Records"),
                             data_store.DataStore.QUEUE_LOCK_ATTRIBUTE,
                             token=self.token)))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
