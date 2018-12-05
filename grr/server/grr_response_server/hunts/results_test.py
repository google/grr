#!/usr/bin/env python
"""Tests for grr_response_server.hunts.results."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server.hunts import results as hunts_results
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class ResultTest(aff4_test_lib.AFF4ObjectTest):

  def testEmptyQueue(self):
    # Create and empty HuntResultCollection.
    collection_urn = rdfvalue.RDFURN("aff4:/testEmptyQueue/collection")
    hunts_results.HuntResultCollection(collection_urn)

    # The queue starts empty, and returns no notifications.
    results = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
        token=self.token)
    self.assertEqual(None, results[0])
    self.assertEqual([], results[1])

  def testNotificationsContainTimestamps(self):
    collection_urn = rdfvalue.RDFURN(
        "aff4:/testNotificationsContainTimestamps/collection")
    with data_store.DB.GetMutationPool() as pool:
      for i in range(5):
        hunts_results.HuntResultCollection.StaticAdd(
            collection_urn,
            rdf_flows.GrrMessage(request_id=i),
            mutation_pool=pool)

    # If we claim results, we should get all 5.
    results = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
        token=self.token)
    self.assertEqual(collection_urn, results[0])
    self.assertLen(results[1], 5)

    # Read all the results, using the contained (ts, suffix) pairs.
    values_read = []
    collection = hunts_results.HuntResultCollection(collection_urn)
    for message in collection.MultiResolve(
        [r.value.ResultRecord() for r in results[1]]):
      values_read.append(message.request_id)
    self.assertEqual(sorted(values_read), list(range(5)))

  def testNotificationClaimsTimeout(self):
    collection_urn = rdfvalue.RDFURN(
        "aff4:/testNotificationClaimsTimeout/collection")
    with data_store.DB.GetMutationPool() as pool:
      for i in range(5):
        hunts_results.HuntResultCollection.StaticAdd(
            collection_urn,
            rdf_flows.GrrMessage(request_id=i),
            mutation_pool=pool)

    results_1 = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
        token=self.token)
    self.assertLen(results_1[1], 5)

    # Check that we have a claim - that another read returns nothing.
    results_2 = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
        token=self.token)
    self.assertEmpty(results_2[1])

    # Push time forward past the default claim timeout, then we should be able
    # to re-read (and re-claim).
    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                           rdfvalue.Duration("45m")):
      results_3 = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
          token=self.token)
    self.assertEqual(results_3, results_1)

  def testDelete(self):
    collection_urn = rdfvalue.RDFURN("aff4:/testDelete/collection")
    with data_store.DB.GetMutationPool() as pool:
      for i in range(5):
        hunts_results.HuntResultCollection.StaticAdd(
            collection_urn,
            rdf_flows.GrrMessage(request_id=i),
            mutation_pool=pool)

    results_1 = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
        token=self.token)
    self.assertLen(results_1[1], 5)

    hunts_results.HuntResultQueue.DeleteNotifications(
        results_1[1], token=self.token)

    # Push time forward past the default claim timeout, then we should still
    # read nothing.
    with test_lib.FakeTime(rdfvalue.RDFDatetime.Now() +
                           rdfvalue.Duration("45m")):
      results_2 = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
          token=self.token)
    self.assertEmpty(results_2[1])

  def testNotificationsSplitByCollection(self):
    # Create two HuntResultCollections.
    collection_urn_1 = rdfvalue.RDFURN(
        "aff4:/testNotificationsSplitByCollection/collection_1")
    collection_urn_2 = rdfvalue.RDFURN(
        "aff4:/testNotificationsSplitByCollection/collection_2")

    # Add 100 records to each collection, in an interleaved manner.
    with data_store.DB.GetMutationPool() as pool:
      for i in range(100):
        hunts_results.HuntResultCollection.StaticAdd(
            collection_urn_1,
            rdf_flows.GrrMessage(request_id=i),
            mutation_pool=pool)
        hunts_results.HuntResultCollection.StaticAdd(
            collection_urn_2,
            rdf_flows.GrrMessage(request_id=100 + i),
            mutation_pool=pool)

    # The first result was added to collection 1, so this should return
    # all 100 results for collection 1.
    results_1 = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
        token=self.token)
    self.assertEqual(collection_urn_1, results_1[0])
    self.assertLen(results_1[1], 100)

    # The first call claimed all the notifications for collection 1. These are
    # claimed, so another call should skip them and give all notifications for
    # collection 2.
    results_2 = hunts_results.HuntResultQueue.ClaimNotificationsForCollection(
        token=self.token)
    self.assertEqual(collection_urn_2, results_2[0])
    self.assertLen(results_2[1], 100)

    values_read = []
    collection_2 = hunts_results.HuntResultCollection(collection_urn_2)
    for message in collection_2.MultiResolve(
        [r.value.ResultRecord() for r in results_2[1]]):
      values_read.append(message.request_id)

    self.assertEqual(sorted(values_read), list(range(100, 200)))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
