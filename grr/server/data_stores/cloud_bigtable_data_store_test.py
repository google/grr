#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests grr.server.data_stores.cloud_bigtable_data_store."""


import random
import time
import unittest

from grpc.framework.interfaces.face import face
import mock

from google.cloud import bigtable
from grr import config
from grr.lib import flags
from grr.lib import rdfvalue
from grr.server import data_store
from grr.server import data_store_test
from grr.server.data_stores import cloud_bigtable_data_store
from grr.test_lib import test_lib


class CloudBigTableDataStoreMixin(object):
  """Integration test CloudBigTable with a live bigtable."""

  TEST_BIGTABLE_INSTANCE_PREFIX = "testinggrrbigtable"
  db = None
  btinstance = None
  test_project_id = None
  instance_id = None
  btclient = None

  @classmethod
  def DeleteTestBigtableInstance(cls):
    cls.btinstance.delete()

  @classmethod
  def setUpClass(cls):
    """Create a test bigtable instance."""
    super(CloudBigTableDataStoreMixin, cls).setUpClass()
    data_store_test._DataStoreTest.setUpClass()
    cls.test_project_id = config.CONFIG["CloudBigtable.test_project_id"]

    if not cls.test_project_id:
      raise unittest.SkipTest("No CloudBigtable.test_project_id set, skipping.")

    cls.db = cloud_bigtable_data_store.CloudBigTableDataStore()
    cls.btclient = bigtable.Client(project=cls.test_project_id, admin=True)

    # Ideally we wouldn't stand up a new instance for each test run, but
    # deleting an instance just marks it for delete in 7 days and you can't
    # recreate with the same name. Users can set instance_id=[yourid] to test
    # with an existing instance.
    if not cls.instance_id:
      cls.instance_id = "".join((cls.TEST_BIGTABLE_INSTANCE_PREFIX,
                                 str(random.randrange(1, 1000))))
    cls.db.Initialize(
        project_id=cls.test_project_id, instance_id=cls.instance_id)

    # Hold a reference to the instance in our class level btclient so tests can
    # access it.
    cls.btinstance = cls.btclient.instance(cls.instance_id)
    data_store.DB = cls.db

  @classmethod
  def tearDownClass(cls):
    """Delete the test bigtable instance if we created one."""
    data_store_test._DataStoreTest.tearDownClass()
    # If we auto-created this instance, delete it now
    if cls.btinstance.instance_id.startswith(cls.TEST_BIGTABLE_INSTANCE_PREFIX):
      cls.DeleteTestBigtableInstance()

  def testBigTableExists(self):
    self.assertEqual(self.btinstance.list_tables()[0].table_id,
                     config.CONFIG["CloudBigtable.table_name"])


class CloudBigTableDataStoreIntegrationTest(CloudBigTableDataStoreMixin,
                                            data_store_test._DataStoreTest):

  def _ClearDB(self, subjects):
    data_store.DB.DeleteSubjects(subjects, sync=True, token=self.token)

  def setUp(self):
    super(CloudBigTableDataStoreIntegrationTest, self).setUp()
    # Only make a single retry in tests.
    self.test_config = test_lib.ConfigOverrider({
        "CloudBigtable.retry_max_attempts": 1,
        "CloudBigtable.retry_interval": 1
    })
    self.test_config.Start()

  def tearDown(self):
    super(CloudBigTableDataStoreIntegrationTest, self).tearDown()
    self.test_config.Stop()

  def testMultiSetNoneTimestampIsNow(self):
    unicode_string = u"this is a uñîcödé string"
    # Cloud Bigtable can only handle ms precision
    start_time = time.time() * 1e6
    trunc_start = self._TruncateToMilliseconds(start_time)
    # Test None timestamp is translated to current time.
    data_store.DB.MultiSet(
        self.test_row,
        {"aff4:size": [(1, None)],
         "aff4:stored": [(unicode_string, 2000)]},
        token=self.token)
    end_time = time.time() * 1e6
    trunc_end = self._TruncateToMilliseconds(end_time)
    stored, ts = data_store.DB.Resolve(
        self.test_row, "aff4:size", token=self.token)
    self.assertEqual(stored, 1)
    self.assertGreaterEqual(ts, trunc_start)
    self.assertLessEqual(ts, trunc_end)

    stored, ts = data_store.DB.Resolve(
        self.test_row, "aff4:stored", token=self.token)
    self.assertEqual(stored, unicode_string)
    self.assertEqual(ts, 2000)

  @unittest.skip(
      "https://github.com/GoogleCloudPlatform/google-cloud-python/issues/2397")
  def testAFF4BlobImage(self):
    pass

  @unittest.skip(
      "https://github.com/GoogleCloudPlatform/google-cloud-python/issues/2397")
  def testResolvePrefixResultsOrderedInDecreasingTimestampOrderPerColumn1(self):
    pass

  @unittest.skip(
      "https://github.com/GoogleCloudPlatform/google-cloud-python/issues/2397")
  def testResolvePrefixResultsOrderedInDecreasingTimestampOrderPerColumn2(self):
    pass


class CloudBigTableDataStoreTest(test_lib.GRRBaseTest):
  """Unit test the datastore with mock bigtable client."""

  def setUp(self):
    self.btclient_patcher = mock.patch.object(bigtable, "Client", autospec=True)
    self.btclient_patcher.start()

    self.db = cloud_bigtable_data_store.CloudBigTableDataStore()
    self.db.table = mock.MagicMock()
    self.btclient = bigtable.Client(project="something", admin=True)

  def tearDown(self):
    self.btclient_patcher.stop()

  def testSortResultsByAttrTimestampValue(self):
    input_list = [("metdata:blah", 2, 100), ("aff4:blah", 3, 10),
                  ("metdata:blah", 6, 20)]
    result_list = [("aff4:blah", 3, 10), ("metdata:blah", 2, 100),
                   ("metdata:blah", 6, 20)]
    # Deliberately checking order is equal.
    self.assertEqual(
        self.db._SortResultsByAttrTimestampValue(input_list), result_list)

  def testCommitWithRetryCompleteFailure(self):
    mock_operation = mock.MagicMock()
    mock_operation.commit = mock.Mock(side_effect=face.AbortionError(
        None, None, None, None))
    with self.assertRaises(cloud_bigtable_data_store.AccessError):
      with mock.patch.object(time, "sleep") as mock_time:
        self.db.CallWithRetry(mock_operation.commit, "write")
        self.assertEqual(mock_time.call_count,
                         config.CONFIG["CloudBigtable.retry_max_attempts"])

  def testCommitWithRetryTemporaryFailure(self):
    mock_operation = mock.MagicMock()
    mock_operation.commit = mock.Mock(
        side_effect=[face.AbortionError(None, None, None, None), True])
    with mock.patch.object(time, "sleep") as mock_time:
      self.db.CallWithRetry(mock_operation.commit, "write")
      # 1 failure == 1 sleep
      self.assertEqual(mock_time.call_count, 1)

  def testTimestampRangeFromTupleNoStart(self):
    result = self.db._TimestampRangeFromTuple((None, 1477415013716002))
    self.assertEqual(result.start, None)
    # Truncate ms and add 1ms
    self.assertEqual(result.end.isoformat(), "2016-10-25T17:03:33.717000+00:00")
    self.assertEqual(result.end.tzname(), "UTC")

  def testTimestampRangeFromTupleZeroStart(self):
    result = self.db._TimestampRangeFromTuple((0, 1477413676361251))
    self.assertIsNone(result.start)
    self.assertEqual(result.end.isoformat(), "2016-10-25T16:41:16.362000+00:00")
    self.assertEqual(result.end.tzname(), "UTC")

  def testTimestampRangeFromTupleEpochOnly(self):
    result = self.db._TimestampRangeFromTuple((0, 0))
    self.assertIsNone(result.start)
    self.assertEqual(result.end.isoformat(), "1970-01-01T00:00:00.001000+00:00")
    self.assertEqual(result.end.tzname(), "UTC")

  def testTimestampRangeFromTuple(self):
    result = self.db._TimestampRangeFromTuple((1477405013716002,
                                               1477415013716002))
    self.assertEqual(result.start.isoformat(),
                     "2016-10-25T14:16:53.716000+00:00")
    self.assertEqual(result.start.tzname(), "UTC")
    self.assertEqual(result.end.isoformat(), "2016-10-25T17:03:33.717000+00:00")
    self.assertEqual(result.end.tzname(), "UTC")

  def testTimestampRangeFromRDFDatetimeTuple(self):
    start = rdfvalue.RDFDatetime(1477405013716333)
    end = rdfvalue.RDFDatetime(1477415013716333)
    result = self.db._TimestampRangeFromTuple((start, end))
    self.assertEqual(result.start.isoformat(),
                     "2016-10-25T14:16:53.716000+00:00")
    self.assertEqual(result.start.tzname(), "UTC")
    self.assertEqual(result.end.isoformat(), "2016-10-25T17:03:33.717000+00:00")
    self.assertEqual(result.end.tzname(), "UTC")


def main(argv):
  del argv  # Unused.
  test_lib.main()


if __name__ == "__main__":
  flags.StartMain(main)
