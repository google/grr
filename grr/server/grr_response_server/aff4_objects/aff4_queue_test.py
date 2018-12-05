#!/usr/bin/env python
"""Tests for Queue."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server.aff4_objects import aff4_queue
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class TestQueue(aff4_queue.Queue):
  rdf_type = rdfvalue.RDFInteger


class QueueTest(aff4_test_lib.AFF4ObjectTest):

  def setUp(self):
    super(QueueTest, self).setUp()
    self.pool = data_store.DB.GetMutationPool()

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

    self.assertLen(results, 100)
    self.assertEqual(0, results[0].value)
    self.assertEqual(99, results[99].value)

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

    self.assertLen(results, 100)

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      no_results = queue.ClaimRecords()
    self.assertEmpty(no_results)

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

    self.assertLen(results_1, 100)

    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                           rdfvalue.Duration("45m")):
      with aff4.FACTORY.OpenWithLock(
          queue_urn, lease_time=200, token=self.token) as queue:
        results_2 = queue.ClaimRecords()
        self.assertLen(results_2, 100)

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
      queue.DeleteRecord(results[0], token=self.token)
      queue.DeleteRecords(results[1:], token=self.token)

    # Wait past the default claim length, to make sure that delete actually did
    # something.
    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                           rdfvalue.Duration("45m")):
      with aff4.FACTORY.OpenWithLock(
          queue_urn, lease_time=200, token=self.token) as queue:
        results = queue.ClaimRecords()
        self.assertEmpty(results)

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
      odd_ids = [record for record in results if int(record.value) % 2 == 1]
      queue.ReleaseRecord(odd_ids[0], token=self.token)
      queue.ReleaseRecords(odd_ids[1:], token=self.token)

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      odd_results = queue.ClaimRecords()

    self.assertLen(odd_results, 50)
    self.assertEqual(1, odd_results[0].value)
    self.assertEqual(99, odd_results[49].value)

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
    self.assertLen(results, 50)
    self.assertEqual(1, results[0].value)
    self.assertEqual(99, results[49].value)

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

    self.assertLen(results, 50)
    self.assertEqual(50, results[0].value)

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
    self.assertLen(results, 100)

    for record in results:
      subject, _, _ = data_store.DataStore.CollectionMakeURN(
          record.queue_id, record.timestamp, record.suffix, record.subpath)
      data_store.DB.DeleteAttributes(
          subject, [data_store.DataStore.COLLECTION_ATTRIBUTE], sync=True)
    data_store.DB.Flush()

    self.assertEqual(
        100,
        sum(1 for _ in data_store.DB.ScanAttribute(
            unicode(queue.urn.Add("Records")),
            data_store.DataStore.QUEUE_LOCK_ATTRIBUTE)))

    with aff4.FACTORY.OpenWithLock(
        queue_urn, lease_time=200, token=self.token) as queue:
      queue.ClaimRecords()
    data_store.DB.Flush()

    self.assertEqual(
        0,
        sum(1 for _ in data_store.DB.ScanAttribute(
            unicode(queue.urn.Add("Records")),
            data_store.DataStore.QUEUE_LOCK_ATTRIBUTE)))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
