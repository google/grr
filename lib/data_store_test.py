#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""These are basic tests for the data store abstraction.

Implementations should be able to pass these tests to be conformant.
"""


import hashlib
import logging
import os
import thread
import threading
import time

# pylint: disable=unused-import, g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import threadpool
from grr.lib import worker


class DataStoreTest(test_lib.GRRBaseTest):
  """Test the data store abstraction."""
  test_row = "aff4:/row:foo"

  def setUp(self):
    super(DataStoreTest, self).setUp()

    data_store.DB.DeleteSubject(self.test_row, token=self.token)
    for i in range(20):
      data_store.DB.DeleteSubject("aff4:/row:%s" % i, token=self.token)

    data_store.DB.Flush()

  def testSetResolve(self):
    """Test the Set() and Resolve() methods."""
    predicate = "task:00000001"
    value = rdfvalue.GrrMessage(session_id="session")

    # Ensure that setting a value is immediately available.
    data_store.DB.Set(self.test_row, predicate, value, token=self.token)
    time.sleep(1)
    data_store.DB.Set(self.test_row + "X", predicate, value, token=self.token)
    (stored_proto, _) = data_store.DB.Resolve(
        self.test_row, predicate, token=self.token)

    stored_proto = rdfvalue.GrrMessage(stored_proto)
    self.assertEqual(stored_proto.session_id, value.session_id)

  def testMultiSet(self):
    """Test the MultiSet() methods."""
    unicode_string = u"this is a uñîcödé string"
    data_store.DB.MultiSet(self.test_row,
                           {"aff4:size": [1],
                            "aff4:stored": [unicode_string],
                            "aff4:unknown_attribute": ["hello"]},
                           token=self.token)

    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:size",
                                        token=self.token)
    self.assertEqual(stored, 1)

    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:stored",
                                        token=self.token)
    self.assertEqual(stored, unicode_string)

    # Make sure that unknown attributes are stored as bytes.
    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:unknown_attribute",
                                        token=self.token)
    self.assertEqual(stored, "hello")
    self.assertEqual(type(stored), str)

  def testMultiSetAsync(self):
    """Test the async MultiSet() methods."""
    unicode_string = u"this is a uñîcödé string"

    data_store.DB.MultiSet(self.test_row,
                           {"aff4:size": [3],
                            "aff4:stored": [unicode_string],
                            "aff4:unknown_attribute": ["hello"]},
                           sync=False, token=self.token)

    # Force the flusher thread to flush.
    data_store.DB.flusher_thread.target()

    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:size",
                                        token=self.token)
    self.assertEqual(stored, 3)

    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:stored",
                                        token=self.token)

    self.assertEqual(stored, unicode_string)

    # Make sure that unknown attributes are stored as bytes.
    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:unknown_attribute",
                                        token=self.token)
    self.assertEqual(stored, "hello")
    self.assertEqual(type(stored), str)

  def testMultiSet2(self):
    """Test the MultiSet() methods."""
    # Specify a per element timestamp
    data_store.DB.MultiSet(self.test_row,
                           {"aff4:size": [(1, 100)],
                            "aff4:stored": [("2", 200)]},
                           token=self.token)

    (stored, ts) = data_store.DB.Resolve(self.test_row, "aff4:size",
                                         token=self.token)
    self.assertEqual(stored, 1)
    self.assertEqual(ts, 100)

    (stored, ts) = data_store.DB.Resolve(self.test_row, "aff4:stored",
                                         token=self.token)
    self.assertEqual(stored, "2")
    self.assertEqual(ts, 200)

  def testMultiSet3(self):
    """Test the MultiSet() delete methods."""
    data_store.DB.MultiSet(self.test_row,
                           {"aff4:size": [1],
                            "aff4:stored": ["2"]},
                           token=self.token)

    data_store.DB.MultiSet(self.test_row, {"aff4:stored": ["2"]},
                           to_delete=["aff4:size"],
                           token=self.token)

    # This should be gone now
    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:size",
                                        token=self.token)
    self.assertEqual(stored, None)

    (stored, _) = data_store.DB.Resolve(self.test_row, "aff4:stored",
                                        token=self.token)
    self.assertEqual(stored, "2")

  def testMultiSet4(self):
    """Test the MultiSet() delete methods when deleting the same predicate."""
    data_store.DB.MultiSet(self.test_row,
                           {"aff4:size": [1],
                            "aff4:stored": ["2"]},
                           token=self.token)

    data_store.DB.MultiSet(self.test_row, {"aff4:size": [4]},
                           to_delete=["aff4:size"],
                           token=self.token)

    # This should only produce a single result
    count = 0
    for count, (predicate, value, _) in enumerate(data_store.DB.ResolveRegex(
        self.test_row, "aff4:size", timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token)):
      self.assertEqual(value, 4)
      self.assertEqual(predicate, "aff4:size")

    self.assertEqual(count, 0)

  def testDeleteAttributes(self):
    """Test we can delete an attribute."""
    predicate = "metadata:predicate"

    data_store.DB.Set(self.test_row, predicate, "hello", token=self.token)

    # Check its there
    (stored, _) = data_store.DB.Resolve(self.test_row, predicate,
                                        token=self.token)

    self.assertEqual(stored, "hello")

    data_store.DB.DeleteAttributes(self.test_row, [predicate], token=self.token)
    (stored, _) = data_store.DB.Resolve(self.test_row, predicate,
                                        token=self.token)

    self.assertEqual(stored, None)

  def testDeleteAttributesRegex(self):
    """Test we can delete an attribute."""
    predicate = "metadata:predicate"

    data_store.DB.Set(self.test_row, predicate, "hello", token=self.token)

    # Check its there
    (stored, _) = data_store.DB.Resolve(self.test_row, predicate,
                                        token=self.token)

    self.assertEqual(stored, "hello")

    data_store.DB.DeleteAttributesRegex(self.test_row, ["metadata:.+"],
                                        token=self.token)
    (stored, _) = data_store.DB.Resolve(self.test_row, predicate,
                                        token=self.token)

    self.assertEqual(stored, None)

  def CheckLength(self, predicate, l):
    all_attributes = data_store.DB.ResolveMulti(
        self.test_row, [predicate], timestamp=(0, 500),
        token=self.token)

    self.assertEqual(len(list(all_attributes)), l)

  def CheckLast(self, predicate, expected_value, exptected_ts):
    stored, ts = data_store.DB.Resolve(self.test_row, predicate,
                                       token=self.token)
    self.assertEqual(stored, expected_value)
    self.assertEqual(ts, exptected_ts)

  def testDeleteAttributesTimestamps(self):
    """Test we can delete an attribute in a time range."""
    predicate = "metadata:tspredicate"

    data_store.DB.Set(self.test_row, predicate, "hello100", timestamp=100,
                      replace=False, token=self.token)
    data_store.DB.Set(self.test_row, predicate, "hello200", timestamp=200,
                      replace=False, token=self.token)
    data_store.DB.Set(self.test_row, predicate, "hello300", timestamp=300,
                      replace=False, token=self.token)
    data_store.DB.Set(self.test_row, predicate, "hello400", timestamp=400,
                      replace=False, token=self.token)

    # Check its there
    self.CheckLast(predicate, "hello400", 400)
    self.CheckLength(predicate, 4)

    # Delete timestamps between 0 and 150.
    data_store.DB.DeleteAttributes(self.test_row, [predicate], start=0, end=150,
                                   token=self.token)

    self.CheckLast(predicate, "hello400", 400)
    self.CheckLength(predicate, 3)

    # Delete timestamps between 350 and 450.
    data_store.DB.DeleteAttributes(self.test_row, [predicate],
                                   start=350, end=450,
                                   token=self.token)

    self.CheckLast(predicate, "hello300", 300)
    self.CheckLength(predicate, 2)

    # Delete everything.
    data_store.DB.DeleteAttributes(self.test_row, [predicate],
                                   start=0, end=500,
                                   token=self.token)

    self.CheckLast(predicate, None, 0)
    self.CheckLength(predicate, 0)

  def testMultiResolveRegex(self):
    """tests MultiResolveRegex."""
    # Make some rows
    rows = []
    for i in range(10):
      row_name = "aff4:/row:%s" % i
      data_store.DB.Set(row_name, "metadata:%s" % i, i, timestamp=5,
                        token=self.token)
      rows.append(row_name)

    subjects = dict(data_store.DB.MultiResolveRegex(
        rows, ["metadata:[34]", "metadata:[78]"], token=self.token))

    subject_names = subjects.keys()
    subject_names.sort()

    self.assertEqual(len(subjects), 4)
    self.assertEqual(
        subject_names,
        [u"aff4:/row:3", u"aff4:/row:4", u"aff4:/row:7", u"aff4:/row:8"])

  def testMultiResolveRegexTimestamp(self):
    """tests MultiResolveRegex with a timestamp."""
    # Make some rows
    rows = []
    for i in range(10):
      row_name = "aff4:/row:%s" % i
      data_store.DB.Set(row_name, "metadata:%s" % i, "v%d" % i, timestamp=i+10,
                        replace=False, token=self.token)
      data_store.DB.Set(row_name, "metadata:%s" % i, "v%d" % i, timestamp=i+20,
                        replace=False, token=self.token)
      rows.append(row_name)

    # Query for newest ts.
    subjects = dict(data_store.DB.MultiResolveRegex(
        rows, ["metadata:[34]", "metadata:[78]"],
        timestamp=data_store.DB.NEWEST_TIMESTAMP,
        token=self.token))

    subject_names = subjects.keys()
    subject_names.sort()

    self.assertEqual(len(subjects), 4)
    self.assertEqual(
        subject_names,
        [u"aff4:/row:3", u"aff4:/row:4", u"aff4:/row:7", u"aff4:/row:8"])

    self.assertEqual(len(subjects[u"aff4:/row:3"]), 1)
    self.assertEqual(len(subjects[u"aff4:/row:4"]), 1)
    self.assertEqual(len(subjects[u"aff4:/row:7"]), 1)
    self.assertEqual(len(subjects[u"aff4:/row:8"]), 1)

    # Query for all ts.
    subjects = dict(data_store.DB.MultiResolveRegex(
        rows, ["metadata:[34]", "metadata:[78]"],
        timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token))

    subject_names = subjects.keys()
    subject_names.sort()

    self.assertEqual(len(subjects), 4)
    self.assertEqual(
        subject_names,
        [u"aff4:/row:3", u"aff4:/row:4", u"aff4:/row:7", u"aff4:/row:8"])

    self.assertEqual(len(subjects[u"aff4:/row:3"]), 2)
    self.assertEqual(len(subjects[u"aff4:/row:4"]), 2)
    self.assertEqual(len(subjects[u"aff4:/row:7"]), 2)
    self.assertEqual(len(subjects[u"aff4:/row:8"]), 2)

    # Query such that not all subjects yield results.
    subjects = dict(data_store.DB.MultiResolveRegex(
        rows, ["metadata:[34]", "metadata:[78]"], timestamp=(12, 17),
        token=self.token))

    subject_names = subjects.keys()
    subject_names.sort()

    self.assertEqual(len(subjects), 3)
    self.assertEqual(
        subject_names,
        [u"aff4:/row:3", u"aff4:/row:4", u"aff4:/row:7"])

    self.assertEqual(len(subjects[u"aff4:/row:3"]), 1)
    self.assertEqual(len(subjects[u"aff4:/row:4"]), 1)
    self.assertEqual(len(subjects[u"aff4:/row:7"]), 1)

    # Query such that some subjects yield more results.
    subjects = dict(data_store.DB.MultiResolveRegex(
        rows, ["metadata:[34]", "metadata:[78]"], timestamp=(14, 27),
        token=self.token))

    subject_names = subjects.keys()
    subject_names.sort()

    self.assertEqual(len(subjects), 4)
    self.assertEqual(
        subject_names,
        [u"aff4:/row:3", u"aff4:/row:4", u"aff4:/row:7", u"aff4:/row:8"])

    self.assertEqual(len(subjects[u"aff4:/row:3"]), 1)
    self.assertEqual(len(subjects[u"aff4:/row:4"]), 2)
    self.assertEqual(len(subjects[u"aff4:/row:7"]), 2)
    self.assertEqual(len(subjects[u"aff4:/row:8"]), 1)

  def testTransactions(self):
    """Test transactions raise."""
    predicate = u"metadata:predicateÎñţér"
    subject = u"aff4:/metadata:rowÎñţér"
    subject2 = u"aff4:/metadata:rowÎñţér2"

    # t1 is holding a transaction on this row.
    t1 = data_store.DB.Transaction(subject, token=self.token)
    t1.Resolve(predicate)

    # This means that modification of this row will fail using a different
    # transaction.
    self.assertRaises(
        data_store.TransactionError, data_store.DB.Transaction,
        subject, token=self.token)

    # We should still be able to modify using the first transaction:
    t1.Set(predicate, "1")
    t1.Commit()

    self.assertEqual(
        data_store.DB.Resolve(subject, predicate, token=self.token)[0], "1")

    t2 = data_store.DB.Transaction(subject, token=self.token)
    t2.Set(predicate, "2")
    t2.Commit()

    self.assertEqual(
        data_store.DB.Resolve(subject, predicate, token=self.token)[0], "2")

    # Check that locks don't influence each other.

    # t1 is holding a transaction on this row.
    t1 = data_store.DB.Transaction(subject, token=self.token)
    t1.Resolve(predicate)

    # This means that modification of this row will fail using a different
    # transaction.
    self.assertRaises(
        data_store.TransactionError, data_store.DB.Transaction,
        subject, token=self.token)

    # t2 is holding a transaction on this row.
    t2 = data_store.DB.Transaction(subject2, token=self.token)
    t2.Resolve(predicate)

    # This means that modification of this row will fail using a different
    # transaction.
    self.assertRaises(
        data_store.TransactionError, data_store.DB.Transaction,
        subject2, token=self.token)
    t2.Commit()

    # Subject 1 should still be locked.
    self.assertRaises(
        data_store.TransactionError, data_store.DB.Transaction,
        subject, token=self.token)

    t1.Commit()

  def testTransactionLease(self):
    subject = u"aff4:/leasetest"
    predicate = "metadata:pred"

    t = data_store.DB.Transaction(subject, token=self.token)
    t.Resolve(predicate)
    t.Set(predicate, "1")
    t.UpdateLease(100)
    res = t.Resolve(predicate)
    t.Set(predicate, "2")
    t.Commit()
    self.assertEqual(res[0], "1")
    t = data_store.DB.Transaction(subject, token=self.token)
    self.assertEqual(t.Resolve(predicate)[0], "2")

  def testAbortTransaction(self):
    predicate = u"metadata:predicate_Îñţér"
    row = u"metadata:row1Îñţér"
    data_store.DB.DeleteSubject(row, token=self.token)

    t1 = data_store.DB.Transaction(row, token=self.token)
    # Now this should not raise since t1 and t2 are on different subjects
    t1.Set(predicate, "1")
    t1.Abort()

    t2 = data_store.DB.Transaction(row, token=self.token)
    self.assertEqual(t2.Resolve(predicate)[0], None)
    t2.Set(predicate, "2")
    t2.Commit()

    self.assertEqual(t2.Resolve(predicate)[0], "2")

  def testTransactions2(self):
    """Test that transactions on different rows do not interfere."""
    predicate = u"metadata:predicate_Îñţér"
    t1 = data_store.DB.Transaction(u"metadata:row1Îñţér", lease_time=100,
                                   token=self.token)

    # Our lease should be between 0 and 100 seconds.
    self.assertLess(t1.CheckLease(), 100)
    self.assertGreater(t1.CheckLease(), 0)

    t2 = data_store.DB.Transaction(u"metadata:row2Îñţér", token=self.token)

    # This grabs read locks on these transactions
    t1.Resolve(predicate)
    t2.Resolve(predicate)

    # Now this should not raise since t1 and t2 are on different subjects
    t1.Set(predicate, "1")
    t1.Commit()
    t2.Set(predicate, "2")
    t2.Commit()

  def testRetryWrapper(self):
    subject = "aff4:/subject"
    data_store.DB.DeleteSubject(subject, token=self.token)

    call_count = stats.STATS.GetMetricValue("datastore_retries")

    def MockSleep(_):
      pass

    def Callback(unused_transaction):
      # Now that we have a transaction, lets try to get another one on the same
      # subject. Since it is locked this should retry.
      try:
        data_store.DB.RetryWrapper(subject, lambda _: None,
                                   token=self.token)
        self.fail("Transaction error not raised.")
      except data_store.TransactionError as e:
        self.assertEqual("Retry number exceeded.", str(e))
        self.assertEqual(
            stats.STATS.GetMetricValue("datastore_retries") - call_count,
            10)

    # By mocking out sleep we can ensure all retries are exhausted.
    with test_lib.Stubber(time, "sleep", MockSleep):
      data_store.DB.RetryWrapper(subject, Callback, token=self.token)

  def testTimestamps(self):
    """Check that timestamps are reasonable."""
    predicate = "metadata:predicate"
    subject = "aff4:/metadata:8"

    # Extend the range of valid timestamps returned from the table to account
    # for potential clock skew.
    start = long(time.time() - 60) * 1e6
    data_store.DB.Set(subject, predicate, "1", token=self.token)

    (stored, ts) = data_store.DB.Resolve(subject, predicate, token=self.token)

    # Check the time is reasonable
    end = long(time.time() + 60) * 1e6

    self.assert_(ts >= start and ts <= end)
    self.assertEqual(stored, "1")

  def testSpecificTimestamps(self):
    """Check arbitrary timestamps can be specified."""
    predicate = "metadata:predicate"
    subject = "aff4:/metadata:9"

    # Check we can specify a timestamp
    data_store.DB.Set(subject, predicate, "2", timestamp=1000, token=self.token)
    (stored, ts) = data_store.DB.Resolve(subject, predicate, token=self.token)

    # Check the time is reasonable
    self.assertEqual(ts, 1000)
    self.assertEqual(stored, "2")

  def testNewestTimestamps(self):
    """Check that NEWEST_TIMESTAMP works as expected."""
    predicate1 = "metadata:predicate1"
    predicate2 = "metadata:predicate2"
    subject = "aff4:/metadata:9.1"

    # Check we can specify a timestamp
    data_store.DB.Set(
        subject, predicate1, "1.1", timestamp=1000, replace=False,
        token=self.token)
    data_store.DB.Set(
        subject, predicate1, "1.2", timestamp=2000, replace=False,
        token=self.token)
    data_store.DB.Set(
        subject, predicate2, "2.1", timestamp=1000, replace=False,
        token=self.token)
    data_store.DB.Set(
        subject, predicate2, "2.2", timestamp=2000, replace=False,
        token=self.token)

    result = data_store.DB.ResolveRegex(
        subject, predicate1, timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token)

    # Should return 2 results.
    values = [x[1] for x in result]
    self.assertEqual(len(values), 2)
    self.assertItemsEqual(values, ["1.1", "1.2"])
    times = [x[2] for x in result]
    self.assertItemsEqual(times, [1000, 2000])

    result = data_store.DB.ResolveRegex(
        subject, predicate1, timestamp=data_store.DB.NEWEST_TIMESTAMP,
        token=self.token)

    # Should return 1 result - the most recent.
    self.assertEqual(len(result), 1)
    self.assertEqual(result[0][1], "1.2")
    self.assertEqual(result[0][2], 2000)

    result = list(data_store.DB.ResolveRegex(
        subject, "metadata:.*", timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token))

    self.assertItemsEqual(result, [
        (u"metadata:predicate1", "1.1", 1000),
        (u"metadata:predicate1", "1.2", 2000),
        (u"metadata:predicate2", "2.1", 1000),
        (u"metadata:predicate2", "2.2", 2000)])

    result = list(data_store.DB.ResolveRegex(
        subject, "metadata:.*", timestamp=data_store.DB.NEWEST_TIMESTAMP,
        token=self.token))

    # Should only return the latest version.
    self.assertItemsEqual(result, [
        (u"metadata:predicate1", "1.2", 2000),
        (u"metadata:predicate2", "2.2", 2000)])

  def testResolveRegEx(self):
    """Test regex Resolving works."""
    predicate = "metadata:predicate"
    subject = "aff4:/metadata:10"

    # Check we can specify a timestamp
    data_store.DB.Set(subject, predicate, "3", timestamp=1000, token=self.token)
    results = [x for x in data_store.DB.ResolveRegex(subject, "metadata:pred.*",
                                                     timestamp=(0, 2000),
                                                     token=self.token)]

    self.assertEqual(len(results), 1)
    # Timestamp
    self.assertEqual(results[0][2], 1000)
    # Value
    self.assertEqual(results[0][1], "3")
    # Predicate
    self.assertEqual(results[0][0], predicate)

  def testResolveRegExPrefix(self):
    """Test resolving with .* works (basically a prefix search)."""
    predicate = "metadata:predicate"
    subject = "aff4:/metadata:101"

    # Check we can specify a timestamp
    data_store.DB.Set(subject, predicate, "3", token=self.token)
    results = [x for x in data_store.DB.ResolveRegex(subject, "metadata:.*",
                                                     token=self.token)]

    self.assertEqual(len(results), 1)
    # Value
    self.assertEqual(results[0][1], "3")
    # Predicate
    self.assertEqual(results[0][0], predicate)

  def testResolveMulti(self):
    """Test regex Multi Resolving works."""
    subject = "aff4:/metadata:11"

    predicates = []
    for i in range(0, 100):
      predicate = "metadata:predicate" + str(i)
      predicates.append(predicate)
      data_store.DB.Set(subject, predicate, "Cell " + predicate, timestamp=1000,
                        token=self.token)

    results = [x for x in data_store.DB.ResolveMulti(subject, predicates,
                                                     token=self.token)]

    self.assertEqual(len(results), 100)

    # Value
    for i in range(0, 100):
      self.assertEqual(results[i][1], "Cell " + predicates[i])
      self.assertEqual(results[i][0], predicates[i])

    # Now try to query for non existent predicates.
    predicates = predicates[:10]
    for i in range(10):
      predicates.append("metadata:not_existing" + str(i))

    results = [x for x in data_store.DB.ResolveMulti(subject, predicates,
                                                     token=self.token)]

    self.assertEqual(10, len(results))
    for i in range(0, 10):
      self.assertEqual(results[i][1], "Cell " + predicates[i])
      self.assertEqual(results[i][0], predicates[i])

  def testAFF4Image(self):
    # 500k
    data = "randomdata" * 50 * 1024

    # Create a blob.
    digest = hashlib.sha256(data).digest()
    urn = aff4.ROOT_URN.Add("blobs").Add(digest.encode("hex"))
    blob_fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", mode="w",
                                  token=self.token)
    blob_fd.Write(data)
    blob_fd.Close(sync=True)

    # Now create the image containing the blob.
    fd = aff4.FACTORY.Create("aff4:/C.1235/image", "HashImage",
                             token=self.token)
    fd.SetChunksize(512*1024)
    fd.Set(fd.Schema.STAT())

    fd.AddBlob(digest, len(data))
    fd.Close(sync=True)

    # Chunks are written async, we have to flush here.
    data_store.DB.Flush()

    # Check if we can read back the data.
    fd = aff4.FACTORY.Open("aff4:/C.1235/image", token=self.token)
    self.assertEqual(fd.read(len(data)), data)
    fd.Close()

  def testDotsInDirectory(self):
    """Dots are special in MongoDB, check that they work in rows/indexes."""

    for directory in ["aff4:/C.1240/dir",
                      "aff4:/C.1240/dir/a.b",
                      "aff4:/C.1240/dir/a.b/c",
                      "aff4:/C.1240/dir/b"]:
      aff4.FACTORY.Create(directory, "VFSDirectory", token=self.token).Close()

    # We want the indexes to be written now.
    data_store.DB.Flush()

    # This must not raise.
    aff4.FACTORY.Open("aff4:/C.1240/dir/a.b/c", "VFSDirectory",
                      token=self.token)

    index = data_store.DB.ResolveRegex("aff4:/C.1240/dir",
                                       "index:dir/.+",
                                       token=self.token)
    subjects = [s for (s, _, _) in index]
    self.assertTrue("index:dir/b" in subjects)
    self.assertTrue("index:dir/a.b" in subjects)
    directory = aff4.FACTORY.Open("aff4:/C.1240/dir", token=self.token)
    self.assertEqual(2, len(list(directory.OpenChildren())))
    self.assertEqual(2, len(list(directory.ListChildren())))

  OPEN_WITH_LOCK_NUM_THREADS = 10
  OPEN_WITH_LOCK_TRIES_PER_THREAD = 3
  OPEN_WITH_LOCK_SYNC_LOCK_SLEEP = 0.2

  @test_lib.SetLabel("large")
  def testAFF4OpenWithLock(self):
    self.opened = False
    self.client_urn = "aff4:/C.0000000000000001"

    client = aff4.FACTORY.Create(self.client_urn, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Set(
        client.Schema.LEASED_UNTIL(
            rdfvalue.RDFDatetime().FromSecondsFromEpoch(0)))
    client.Close()

    self.open_failures = 0
    self.close_failures = 0
    self.results = []

    def ParallelThread():
      for _ in xrange(self.OPEN_WITH_LOCK_TRIES_PER_THREAD):
        t = time.time()
        try:
          with aff4.FACTORY.OpenWithLock(
              self.client_urn, token=self.token, blocking=True,
              blocking_sleep_interval=self.OPEN_WITH_LOCK_SYNC_LOCK_SLEEP,
              blocking_lock_timeout=10):

            # We fail if another thread has the object already opened here.
            if self.opened:
              self.open_failures += 1
              self.fail("Double open!")

            self.opened = True
            logging.info("Thread %s holding lock for 0.5 seconds.",
                         thread.get_ident())
            time.sleep(0.5)

            # We fail if someone has closed the object while we are holding it
            # opened.
            if not self.opened:
              self.close_failures += 1
              self.fail("Double close!")

            self.results.append(thread.get_ident())

            self.opened = False
            return

        except aff4.LockError:
          logging.info("Lock failed after %s seconds - retying.",
                       (time.time() - t))

    threads = []
    for _ in range(self.OPEN_WITH_LOCK_NUM_THREADS):
      t = threading.Thread(target=ParallelThread)
      threads.append(t)

    for t in threads:
      t.start()

    for t in threads:
      t.join()

    self.assertEqual(self.open_failures, 0)
    self.assertEqual(self.close_failures, 0)

    # Make sure all threads got it eventually.
    self.assertEqual(len(self.results), self.OPEN_WITH_LOCK_NUM_THREADS)


class DataStoreBenchmarks(test_lib.MicroBenchmarks):

  queue = rdfvalue.RDFURN("BENCHMARK")
  units = "s"

  def setUp(self):
    super(DataStoreBenchmarks, self).setUp()
    self.tp = threadpool.ThreadPool.Factory("test_pool", 50)
    self.tp.Start()

  def tearDown(self):
    super(DataStoreBenchmarks, self).tearDown()
    self.tp.Stop()

  def GenerateFiles(self, client_id, n, directory="dir/dir"):
    res = []
    for i in xrange(n):
      res.append(rdfvalue.StatEntry(
          aff4path="aff4:/%s/fs/os/%s/file%d" % (client_id, directory, i),
          st_mode=33261,
          st_ino=1026267,
          st_dev=51713,
          st_nlink=1,
          st_uid=0,
          st_gid=0,
          st_size=60064,
          st_atime=1308964274,
          st_mtime=1285093975,
          st_ctime=1299502221,
          st_blocks=128,
          st_blksize=4096,
          st_rdev=0,
          pathspec=rdfvalue.PathSpec(path="/dir/dir/file%d" % i,
                                     pathtype=0)))
    return res

  def StartFlow(self, client_id):
    flow_id = flow.GRRFlow.StartFlow(client_id=client_id,
                                     flow_name="RecursiveListDirectory",
                                     max_depth=5, queue=self.queue,
                                     token=self.token)
    self.flow_ids.append(flow_id)

    messages = []
    for d in range(self.nr_dirs):
      messages += self.GenerateFiles(client_id, self.files_per_dir,
                                     "dir/dir%d" % d)

    messages.append(rdfvalue.GrrStatus())

    with queue_manager.QueueManager(token=self.token) as flow_manager:
      for i, payload in enumerate(messages):
        msg = rdfvalue.GrrMessage(
            session_id=flow_id,
            request_id=1, response_id=1+i,
            auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
            payload=payload)
        if isinstance(payload, rdfvalue.GrrStatus):
          msg.type = 1
        flow_manager.QueueResponse(flow_id, msg)

  nr_clients = 4
  nr_dirs = 4
  files_per_dir = 500

  @test_lib.SetLabel("benchmark")
  def testSimulateFlows(self):
    self.flow_ids = []
    self.units = "s"

    client_ids = ["C.%016X" % j for j in range(1, self.nr_clients + 1)]

    start_time = time.time()

    for client_id in client_ids:
      self.tp.AddTask(self.StartFlow, (client_id,))
    self.tp.Join()

    priorities = dict([(f, 1) for f in self.flow_ids])
    queue_manager.QueueManager(token=self.token).MultiNotifyQueue(
        self.flow_ids, priorities)

    time_used = time.time() - start_time

    self.AddResult("Generate Messages (%d clients, %d files)" % (
        self.nr_clients, self.nr_dirs * self.files_per_dir), time_used, 1)

    my_worker = worker.GRRWorker(queue=self.queue, token=self.token)

    start_time = time.time()

    while my_worker.RunOnce():
      pass
    my_worker.thread_pool.Join()

    time_used = time.time() - start_time

    self.AddResult("Process Messages", time_used, 1)

  @test_lib.SetLabel("benchmark")
  def testMicroBenchmarks(self):

    # Tests run in arbitrary order but for the benchmarks, the order makes a
    # difference so we call them all from one test here.
    self.n = 1000
    self.small_n = self.n / 100
    self.units = "ms"
    self.BenchmarkWriting()
    self.BenchmarkReading()

    self.BenchmarkWritingThreaded()
    self.BenchmarkReadingThreaded()

    self.BenchmarkAFF4Locks()

  def BenchmarkWriting(self):

    subject_template = "aff4:/row%d"
    predicate_template = "task:flow%d"
    value = os.urandom(100)
    large_value = os.urandom(10 * 1024 * 1024)

    start_time = time.time()
    for i in xrange(self.n):
      data_store.DB.Set(subject_template % i, "task:flow", value,
                        token=self.token)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set rows", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.n):
      data_store.DB.Set("aff4:/somerow", predicate_template % i,
                        value, token=self.token)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set attributes", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.n):
      data_store.DB.Set("aff4:/somerow", "task:someflow", value,
                        replace=False, token=self.token)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set versions", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.small_n):
      data_store.DB.Set("aff4:/largerow%d" % i, "task:largeflow",
                        large_value, replace=False, token=self.token)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set large values", (end_time - start_time) / self.small_n,
                   self.small_n)

  def BenchmarkReading(self):

    subject_template = "aff4:/row%d"
    predicate_template = "task:flow%d"

    start_time = time.time()
    for i in xrange(self.n):
      data_store.DB.Resolve(subject_template % i, "task:flow", token=self.token)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Get rows", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.n):
      data_store.DB.Resolve("aff4:/somerow", predicate_template % i,
                            token=self.token)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Get attributes", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.small_n):
      data_store.DB.ResolveRegex("aff4:/somerow", "task:someflow",
                                 timestamp=data_store.DB.ALL_TIMESTAMPS,
                                 token=self.token)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Get all versions", (end_time - start_time) / self.small_n,
                   self.small_n)

    start_time = time.time()
    for i in xrange(self.small_n):
      res = data_store.DB.ResolveRegex("aff4:/largerow%d" % i, "task:largeflow",
                                       timestamp=data_store.DB.ALL_TIMESTAMPS,
                                       token=self.token)
      self.assertEqual(len(res), 1)
      self.assertEqual(len(res[0][1]), 10 * 1024 * 1024)

    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Get large values", (end_time - start_time) / self.small_n,
                   self.small_n)

  def BenchmarkWritingThreaded(self):

    subject_template = "aff4:/threadedrow%d"
    predicate_template = "task:threadedflow%d"
    value = os.urandom(100)
    large_value = os.urandom(10 * 1024 * 1024)

    start_time = time.time()
    for i in xrange(self.n):
      self.tp.AddTask(data_store.DB.Set, (subject_template % i,
                                          "task:threadedflow",
                                          value, None, self.token))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set rows",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.n):
      self.tp.AddTask(data_store.DB.Set, ("aff4:/somerowthreaded",
                                          predicate_template % i,
                                          value, None, self.token))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set attributes",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.n):
      self.tp.AddTask(data_store.DB.Set, ("aff4:/somerowthreaded",
                                          "task:someflowthreaded",
                                          value, None,
                                          self.token, False))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set versions",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.small_n):
      self.tp.AddTask(data_store.DB.Set, ("aff4:/threadedlargerow%d" % i,
                                          "task:largeflowthreaded", large_value,
                                          None, self.token, False))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set large values",
                   (end_time - start_time) / self.small_n, self.small_n)

  def ResolveRegexAndCheck(self, subject, predicate, expected_items=1000):
    res = data_store.DB.ResolveRegex(subject, predicate, token=self.token,
                                     timestamp=data_store.DB.ALL_TIMESTAMPS)
    self.assertEqual(len(list(res)), expected_items)

  def BenchmarkReadingThreaded(self):

    subject_template = "aff4:/threadedrow%d"
    predicate_template = "task:threadedflow%d"

    start_time = time.time()
    for i in xrange(self.n):
      self.tp.AddTask(data_store.DB.Resolve, (
          subject_template % i, "task:threadedflow", self.token))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get rows",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.n):
      self.tp.AddTask(data_store.DB.Resolve, (
          "aff4:/somerowthreaded", predicate_template % i, self.token))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get attributes",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in xrange(self.small_n):
      self.tp.AddTask(self.ResolveRegexAndCheck, ("aff4:/somerowthreaded",
                                                  "task:someflowthreaded"))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get all versions",
                   (end_time - start_time) / self.small_n, self.small_n)

    start_time = time.time()
    for i in xrange(self.small_n):
      self.tp.AddTask(self.ResolveRegexAndCheck, (
          "aff4:/threadedlargerow%d" % i,
          "task:largeflowthreaded", 1))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get large values",
                   (end_time - start_time) / self.small_n, self.small_n)

  def BenchmarkAFF4Locks(self):

    self.client_id = "C.%016X" % 999

    # Write some data to read.
    client = aff4.FACTORY.Create(self.client_id, "VFSGRRClient", mode="w",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Close()

    cl = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertEqual(cl.Get(cl.Schema.HOSTNAME), "client1")

    # Collect exceptions in threads.
    self.fails = []

    def Thread():
      try:
        # Using blocking_lock_timeout of 10 minutes to avoid possible
        # timeouts when running tests on slow hardware.
        with aff4.FACTORY.OpenWithLock(self.client_id, token=self.token,
                                       blocking=True,
                                       blocking_sleep_interval=0.2,
                                       blocking_lock_timeout=600) as client:
          self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")

      except Exception as e:  # pylint: disable=broad-except
        self.fails.append(e)

    start_time = time.time()
    for _ in xrange(self.n):
      Thread()
    end_time = time.time()

    self.AddResult("OpenWithLock",
                   (end_time - start_time) / self.n, self.n)

    self.assertEqual(len(self.fails), 0)

    start_time = time.time()
    for _ in xrange(self.n):
      self.tp.AddTask(Thread, ())
    self.tp.Join()
    end_time = time.time()

    self.AddResult("Multithreaded: OpenWithLock",
                   (end_time - start_time) / self.n, self.n)

    self.assertEqual(len(self.fails), 0)
