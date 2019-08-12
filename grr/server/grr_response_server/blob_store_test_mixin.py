#!/usr/bin/env python
"""Mixin class to be used in tests for BlobStore implementations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import time

from future.utils import with_metaclass
import mock

from grr_response_core.lib import rdfvalue
from grr_response_server import blob_store
from grr_response_server.databases import mysql_blobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib

POSITIONAL_ARGS = 0


class BlobStoreTestMixin(
    with_metaclass(abc.ABCMeta, stats_test_lib.StatsTestMixin)):
  """Mixin providing tests shared by all blob store tests implementations."""

  @abc.abstractmethod
  def CreateBlobStore(self):
    """Create a test blob store.

    Returns:
      A tuple (blob_store, cleanup), where blob_store is an instance of
      blob_store.BlobStore to be tested  and cleanup is a function which
      destroys blob_store, releasing any resources held by it.
    """

  def setUp(self):
    super(BlobStoreTestMixin, self).setUp()
    bs, cleanup = self.CreateBlobStore()
    if cleanup is not None:
      self.addCleanup(cleanup)
    self.blob_store = blob_store.BlobStoreValidationWrapper(bs)

  def testCheckBlobsExistOnEmptyListReturnsEmptyDict(self):
    self.assertEqual(self.blob_store.CheckBlobsExist([]), {})

  def testReadBlobsOnEmptyListReturnsEmptyDict(self):
    self.assertEqual(self.blob_store.ReadBlobs([]), {})

  def testReadingNonExistentBlobReturnsNone(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    result = self.blob_store.ReadBlob(blob_id)
    self.assertIsNone(result)

  def testReadingNonExistentBlobsReturnsNone(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    result = self.blob_store.ReadBlobs([blob_id])
    self.assertEqual(result, {blob_id: None})

  def testSingleBlobCanBeWrittenAndThenRead(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    self.blob_store.WriteBlobs({blob_id: blob_data})

    result = self.blob_store.ReadBlob(blob_id)
    self.assertEqual(result, blob_data)

  def testMultipleBlobsCanBeWrittenAndThenRead(self):
    blob_ids = [rdf_objects.BlobID((b"%d1234567" % i) * 4) for i in range(10)]
    blob_data = [b"a" * i for i in range(10)]

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))

    result = self.blob_store.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testWriting80MbOfBlobsWithSingleCallWorks(self):
    num_blobs = 80
    blob_ids = [
        rdf_objects.BlobID((b"%02d234567" % i) * 4) for i in range(num_blobs)
    ]
    blob_data = [b"a" * 1024 * 1024] * num_blobs

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))

    result = self.blob_store.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testCheckBlobExistsReturnsFalseForMissing(self):
    blob_id = rdf_objects.BlobID(b"11111111" * 4)
    self.assertFalse(self.blob_store.CheckBlobExists(blob_id))

  def testCheckBlobExistsReturnsTrueForExisting(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    self.blob_store.WriteBlobs({blob_id: blob_data})
    self.assertTrue(self.blob_store.CheckBlobExists(blob_id))

  def testCheckBlobsExistCorrectlyReportsPresentAndMissingBlobs(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    self.blob_store.WriteBlobs({blob_id: blob_data})

    other_blob_id = rdf_objects.BlobID(b"abcdefgh" * 4)
    result = self.blob_store.CheckBlobsExist([blob_id, other_blob_id])
    self.assertEqual(result, {blob_id: True, other_blob_id: False})

  @mock.patch.object(mysql_blobs, "BLOB_CHUNK_SIZE", 1)
  def testLargeBlobsAreReassembledInCorrectOrder(self):
    blob_data = b"0123456789"
    blob_id = rdf_objects.BlobID(b"00234567" * 4)
    self.blob_store.WriteBlobs({blob_id: blob_data})
    result = self.blob_store.ReadBlobs([blob_id])
    self.assertEqual({blob_id: blob_data}, result)

  @mock.patch.object(mysql_blobs, "BLOB_CHUNK_SIZE", 3)
  def testNotEvenlyDivisibleBlobsAreReassembledCorrectly(self):
    blob_data = b"0123456789"
    blob_id = rdf_objects.BlobID(b"00234567" * 4)
    self.blob_store.WriteBlobs({blob_id: blob_data})
    result = self.blob_store.ReadBlobs([blob_id])
    self.assertEqual({blob_id: blob_data}, result)

  def testOverwritingExistingBlobDoesNotRaise(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    for _ in range(2):
      self.blob_store.WriteBlobs({blob_id: blob_data})

  @mock.patch.object(time, "sleep")
  def testReadAndWaitForBlobsWorksWithImmediateResults(self, sleep_mock):
    a_id = rdf_objects.BlobID(b"0" * 32)
    b_id = rdf_objects.BlobID(b"1" * 32)
    blobs = {a_id: b"aa", b_id: b"bb"}

    with mock.patch.object(
        self.blob_store, "ReadBlobs", return_value=blobs) as read_mock:
      results = self.blob_store.ReadAndWaitForBlobs(
          [a_id, b_id], timeout=rdfvalue.Duration.From(10, rdfvalue.SECONDS))

    sleep_mock.assert_not_called()
    read_mock.assert_called_once()
    self.assertCountEqual(read_mock.call_args[POSITIONAL_ARGS][0], [a_id, b_id])
    self.assertEqual({a_id: b"aa", b_id: b"bb"}, results)

  @mock.patch.object(time, "sleep")
  def testReadAndWaitForBlobsPollsUntilResultsAreAvailable(self, sleep_mock):
    a_id = rdf_objects.BlobID(b"0" * 32)
    b_id = rdf_objects.BlobID(b"1" * 32)
    effect = [{
        a_id: None,
        b_id: None
    }, {
        a_id: b"aa",
        b_id: None
    }, {
        b_id: None
    }, {
        b_id: b"bb"
    }]

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10)):
      with mock.patch.object(
          self.blob_store, "ReadBlobs", side_effect=effect) as read_mock:
        results = self.blob_store.ReadAndWaitForBlobs(
            [a_id, b_id], timeout=rdfvalue.Duration.From(10, rdfvalue.SECONDS))

    self.assertEqual({a_id: b"aa", b_id: b"bb"}, results)
    self.assertEqual(read_mock.call_count, 4)
    self.assertCountEqual(read_mock.call_args_list[0][POSITIONAL_ARGS][0],
                          [a_id, b_id])
    self.assertCountEqual(read_mock.call_args_list[1][POSITIONAL_ARGS][0],
                          [a_id, b_id])
    self.assertCountEqual(read_mock.call_args_list[2][POSITIONAL_ARGS][0],
                          [b_id])
    self.assertCountEqual(read_mock.call_args_list[3][POSITIONAL_ARGS][0],
                          [b_id])
    self.assertEqual(sleep_mock.call_count, 3)

  def testReadAndWaitForBlobsStopsAfterTimeout(self):
    a_id = rdf_objects.BlobID(b"0" * 32)
    b_id = rdf_objects.BlobID(b"1" * 32)
    effect = [{a_id: b"aa", b_id: None}] + [{b_id: None}] * 3
    time_mock = test_lib.FakeTime(10)
    sleep_call_count = [0]

    def sleep(secs):
      time_mock.time += secs
      sleep_call_count[0] += 1

    with time_mock, mock.patch.object(time, "sleep", sleep):
      with mock.patch.object(
          self.blob_store, "ReadBlobs", side_effect=effect) as read_mock:
        results = self.blob_store.ReadAndWaitForBlobs(
            [a_id, b_id], timeout=rdfvalue.Duration.From(3, rdfvalue.SECONDS))

    self.assertEqual({a_id: b"aa", b_id: None}, results)
    self.assertGreaterEqual(read_mock.call_count, 3)
    self.assertCountEqual(read_mock.call_args_list[0][POSITIONAL_ARGS][0],
                          [a_id, b_id])
    for i in range(1, read_mock.call_count):
      self.assertCountEqual(read_mock.call_args_list[i][POSITIONAL_ARGS][0],
                            [b_id])
    self.assertEqual(read_mock.call_count, sleep_call_count[0] + 1)

  @mock.patch.object(time, "sleep")
  def testReadAndWaitForBlobsPopulatesStats(self, sleep_mock):
    a_id = rdf_objects.BlobID(b"0" * 32)
    b_id = rdf_objects.BlobID(b"1" * 32)
    blobs = {a_id: b"aa", b_id: b"bb"}

    with mock.patch.object(self.blob_store, "ReadBlobs", return_value=blobs):
      with self.assertStatsCounterDelta(2,
                                        blob_store.BLOB_STORE_POLL_HIT_LATENCY):
        with self.assertStatsCounterDelta(
            2, blob_store.BLOB_STORE_POLL_HIT_ITERATION):
          self.blob_store.ReadAndWaitForBlobs([a_id, b_id],
                                              timeout=rdfvalue.Duration.From(
                                                  10, rdfvalue.SECONDS))
