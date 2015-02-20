#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""These are basic tests for the data store abstraction.

Implementations should be able to pass these tests to be conformant.
"""


import csv
import functools
import hashlib
import inspect
import logging
import operator
import os
import random
import string
import tempfile
import thread
import threading
import time


# pylint: disable=unused-import, g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import threadpool
from grr.lib import utils
from grr.lib import worker


def DeletionTest(f):
  """This indicates a test that uses deletion."""
  @functools.wraps(f)
  def Decorator(testinstance):
    if testinstance.TEST_DELETION:
      return f(testinstance)
    else:
      return testinstance.skipTest("Tests that use deletion are disabled "
                                   "for this data store.")

  return Decorator


def TransactionTest(f):
  """This indicates a test that uses transactions."""
  @functools.wraps(f)
  def Decorator(testinstance):
    if testinstance.TEST_TRANSACTIONS:
      return f(testinstance)
    else:
      return testinstance.skipTest("Tests that use transactions are disabled "
                                   "for this data store.")

  return Decorator


class _DataStoreTest(test_lib.GRRBaseTest):
  """Test the data store abstraction."""
  test_row = "aff4:/row:foo"

  # This flag controls if tests can also delete data. Some data stores don't
  # support deletion so those tests will fail for them.
  TEST_DELETION = True
  # The same applies to transactions.
  TEST_TRANSACTIONS = True

  def setUp(self):
    super(_DataStoreTest, self).setUp()
    self.InitDatastore()

    data_store.DB.DeleteSubject(self.test_row, token=self.token)
    for i in range(20):
      data_store.DB.DeleteSubject("aff4:/row:%s" % i, token=self.token)

    data_store.DB.Flush()

    self.acls_installed = False

  def tearDown(self):
    super(_DataStoreTest, self).tearDown()
    self.DestroyDatastore()

  def InitDatastore(self):
    """Initiates custom data store."""

  def DestroyDatastore(self):
    """Destroys custom data store."""

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

    # Test setting values with timestamp.
    data_store.DB.MultiSet(self.test_row,
                           {"aff4:size": [(1, 100)],
                            "aff4:stored": [(unicode_string, 200)]},
                           token=self.token)

    (stored, ts) = data_store.DB.Resolve(self.test_row, "aff4:size",
                                         token=self.token)
    self.assertEqual(stored, 1)
    self.assertEqual(ts, 100)

    (stored, ts) = data_store.DB.Resolve(self.test_row, "aff4:stored",
                                         token=self.token)
    self.assertEqual(stored, unicode_string)
    self.assertEqual(ts, 200)

    # Test giving a broken timestamp definition.
    with test_lib.FakeTime(555):
      data_store.DB.MultiSet(self.test_row,
                             {"aff4:size": [(1, None)],
                              "aff4:stored": [(unicode_string, 200)]},
                             token=self.token)

    (stored, ts) = data_store.DB.Resolve(self.test_row, "aff4:size",
                                         token=self.token)
    self.assertEqual(stored, 1)
    self.assertEqual(ts, 555000000)

    (stored, ts) = data_store.DB.Resolve(self.test_row, "aff4:stored",
                                         token=self.token)
    self.assertEqual(stored, unicode_string)
    self.assertEqual(ts, 200)

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

  def testMultiSetSetsTimestapWhenReplacing(self):
    data_store.DB.MultiSet(self.test_row,
                           {"aff4:size": [(1, 100)]},
                           replace=True,
                           token=self.token)

    (stored, ts) = data_store.DB.Resolve(self.test_row, "aff4:size",
                                         token=self.token)
    self.assertEqual(stored, 1)
    self.assertEqual(ts, 100)

  def testMultiSetRemovesOtherValuesWhenReplacing(self):
    data_store.DB.MultiSet(self.test_row,
                           {"aff4:stored": [("2", 100), ("3", 200)]},
                           replace=False, token=self.token)

    values = data_store.DB.ResolveRegex(self.test_row, "aff4:stored",
                                        timestamp=data_store.DB.ALL_TIMESTAMPS,
                                        token=self.token)
    self.assertListEqual(
        values, [("aff4:stored", "3", 200), ("aff4:stored", "2", 100)])

    data_store.DB.MultiSet(self.test_row,
                           {"aff4:stored": [("4", 150)]},
                           replace=True, token=self.token)
    values = data_store.DB.ResolveRegex(self.test_row, "aff4:stored",
                                        timestamp=data_store.DB.ALL_TIMESTAMPS,
                                        token=self.token)
    self.assertListEqual(
        values, [("aff4:stored", "4", 150)])

  @DeletionTest
  def testDeleteAttributes(self):
    """Test we can delete an attribute."""
    predicate = "metadata:predicate"

    data_store.DB.Set(self.test_row, predicate, "hello", token=self.token)

    # Check its there
    (stored, _) = data_store.DB.Resolve(self.test_row, predicate,
                                        token=self.token)

    self.assertEqual(stored, "hello")

    data_store.DB.DeleteAttributes(self.test_row, [predicate], sync=True,
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

  @DeletionTest
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
                                   sync=True, token=self.token)

    self.CheckLast(predicate, "hello400", 400)
    self.CheckLength(predicate, 3)

    # Delete timestamps between 350 and 450.
    data_store.DB.DeleteAttributes(self.test_row, [predicate],
                                   start=350, end=450, sync=True,
                                   token=self.token)

    self.CheckLast(predicate, "hello300", 300)
    self.CheckLength(predicate, 2)

    # Delete everything.
    data_store.DB.DeleteAttributes(self.test_row, [predicate],
                                   start=0, end=500, sync=True,
                                   token=self.token)

    self.CheckLast(predicate, None, 0)
    self.CheckLength(predicate, 0)

  @DeletionTest
  def testDeleteSubjects(self):
    predicate = "metadata:tspredicate"

    data_store.DB.Set(self.test_row, predicate, "hello100", timestamp=100,
                      replace=False, token=self.token)
    data_store.DB.DeleteSubject(self.test_row, token=self.token)
    data_store.DB.Flush()
    self.CheckLength(predicate, 0)

    # This should work with the sync argument too.
    data_store.DB.Set(self.test_row, predicate, "hello100", timestamp=100,
                      replace=False, token=self.token)
    data_store.DB.DeleteSubject(self.test_row, token=self.token, sync=True)
    self.CheckLength(predicate, 0)

  def testMultiResolveRegex(self):
    """tests MultiResolveRegex."""
    rows = self._MakeTimestampedRows()

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
    # Make some rows.
    rows = []
    for i in range(10):
      row_name = "aff4:/row:%s" % i
      data_store.DB.Set(
          row_name, "metadata:%s" % i, "v%d" % i, timestamp=i + 10,
          replace=False, token=self.token)
      data_store.DB.Set(
          row_name, "metadata:%s" % i, "v%d" % i, timestamp=i + 20,
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

  def _MakeTimestampedRows(self):
    # Make some rows.
    rows = []
    for i in range(5):
      row_name = "aff4:/row:%s" % i
      timestamp = rdfvalue.RDFDatetime(100 + i)
      data_store.DB.Set(row_name, "metadata:%s" % i, i, timestamp=timestamp,
                        token=self.token)
      rows.append(row_name)

    for i in range(5, 10):
      row_name = "aff4:/row:%s" % i
      timestamp = rdfvalue.RDFDatetime(100 + i)
      data_store.DB.MultiSet(row_name, {"metadata:%s" % i: [i]},
                             timestamp=timestamp, token=self.token)
      rows.append(row_name)

    return rows

  def _CheckResultTimestamps(self, result, expected_timestamps):
    timestamps = []
    for predicates in result.itervalues():
      for predicate in predicates:
        timestamps.append(predicate[2])

    self.assertListEqual(sorted(timestamps), sorted(expected_timestamps))

  def testResolveRegexResultsOrderedInDecreasingTimestampOrder1(self):
    predicate1 = "metadata:predicate1"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order1"

    # Set 1000 values with increasing timestamps.
    for i in range(1000):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False,
          token=self.token)

    # Check that results will be returned in decreasing timestamp order.
    # This test along with a next one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = data_store.DB.ResolveRegex(
        subject, predicate1, timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token)
    for result_index, i in enumerate(reversed(range(1000))):
      self.assertEqual(result[result_index], (predicate1, str(i), i * 1000))

  def testResolveRegexResultsOrderedInDecreasingTimestampOrder2(self):
    predicate1 = "metadata:predicate1"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order2"

    # Set 1000 values with timestamps starting in the future and going to
    # the past.
    for i in reversed(range(1000)):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False,
          token=self.token)

    # Check that results will be returned in decreasing timestamp order.
    # This test along with a previous one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = data_store.DB.ResolveRegex(
        subject, predicate1, timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token)
    for result_index, i in enumerate(reversed(range(1000))):
      self.assertEqual(result[result_index], (predicate1, str(i), i * 1000))

  def testResolveRegexResultsOrderedInDecreasingTimestampOrderPerColumn1(self):
    predicate1 = "metadata:predicate1"
    predicate2 = "metadata:predicate2"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order_per_column1"

    # Set 1000 values with increasing timestamps for each predicate.
    for i in range(1000):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False,
          token=self.token)
      data_store.DB.Set(
          subject, predicate2, str(i), timestamp=i * 1000, replace=False,
          token=self.token)

    # Check that results will be returned in decreasing timestamp order
    # per column.
    # This test along with a previous one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = list(data_store.DB.ResolveRegex(
        subject, "metadata:predicate.*", timestamp=data_store.DB.ALL_TIMESTAMPS,
        limit=10000, token=self.token))

    predicate1_results = [r for r in result if r[0] == predicate1]
    for result_index, i in enumerate(reversed(range(1000))):
      self.assertEqual(predicate1_results[result_index],
                       (predicate1, str(i), i * 1000))

    predicate2_results = [r for r in result if r[0] == predicate2]
    for result_index, i in enumerate(reversed(range(1000))):
      self.assertEqual(predicate2_results[result_index],
                       (predicate2, str(i), i * 1000))

  def testResolveRegexResultsOrderedInDecreasingTimestampOrderPerColumn2(self):
    predicate1 = "metadata:predicate1"
    predicate2 = "metadata:predicate2"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order_per_column2"

    # Set 1000 values for each predicate with timestamps starting in the
    # future and going to the past.
    for i in reversed(range(1000)):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False,
          token=self.token)
      data_store.DB.Set(
          subject, predicate2, str(i), timestamp=i * 1000, replace=False,
          token=self.token)

    # Check that results will be returned in decreasing timestamp order
    # per column.
    # This test along with a previous one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = list(data_store.DB.ResolveRegex(
        subject, "metadata:predicate.*", timestamp=data_store.DB.ALL_TIMESTAMPS,
        limit=10000, token=self.token))

    predicate1_results = [r for r in result if r[0] == predicate1]
    for result_index, i in enumerate(reversed(range(1000))):
      self.assertEqual(predicate1_results[result_index],
                       (predicate1, str(i), i * 1000))

    predicate2_results = [r for r in result if r[0] == predicate2]
    for result_index, i in enumerate(reversed(range(1000))):
      self.assertEqual(predicate2_results[result_index],
                       (predicate2, str(i), i * 1000))

  def testRDFDatetimeTimestamps(self):

    test_rows = self._MakeTimestampedRows()

    # Make sure all timestamps are set correctly.
    result = dict(data_store.DB.MultiResolveRegex(
        test_rows, ["metadata:.*"], token=self.token))

    self._CheckResultTimestamps(result, range(100, 110))

    # Now MultiResolve by timestamp.

    timestamp = (rdfvalue.RDFDatetime(103), rdfvalue.RDFDatetime(108))
    result = dict(data_store.DB.MultiResolveRegex(
        test_rows, ["metadata:.*"], token=self.token, timestamp=timestamp))

    # Timestamp selection is inclusive so we should have 103-108.
    self._CheckResultTimestamps(result, range(103, 109))

    # Now test timestamped attributes.
    row_name = "aff4:/attribute_test_row"
    attribute_name = "metadata:test_attribute"
    attributes_to_set = {attribute_name: [
        (i, rdfvalue.RDFDatetime(i)) for i in xrange(100, 110)]}
    data_store.DB.MultiSet(row_name, attributes_to_set, replace=False,
                           token=self.token)

    # Make sure all timestamps are set correctly.
    result = dict(data_store.DB.MultiResolveRegex(
        [row_name], ["metadata:.*"], timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token))

    self._CheckResultTimestamps(result, range(100, 110))

    if self.TEST_DELETION:
      # Delete some of them.
      data_store.DB.DeleteAttributes(row_name, [attribute_name],
                                     start=rdfvalue.RDFDatetime(102),
                                     end=rdfvalue.RDFDatetime(104),
                                     token=self.token)
      # Make sure that passing start==end deletes that version.
      data_store.DB.DeleteAttributes(row_name, [attribute_name],
                                     start=rdfvalue.RDFDatetime(106),
                                     end=rdfvalue.RDFDatetime(106),
                                     token=self.token)

      result = dict(data_store.DB.MultiResolveRegex(
          [row_name], ["metadata:.*"], timestamp=data_store.DB.ALL_TIMESTAMPS,
          token=self.token))

      expected_timestamps = [100, 101, 105, 107, 108, 109]
      self._CheckResultTimestamps(result, expected_timestamps)

  @TransactionTest
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
    self.assertEqual(t1.Resolve(predicate)[0], "1")
    t1.Commit()

    self.assertEqual(
        data_store.DB.Resolve(subject, predicate, token=self.token)[0], "1")

    t2 = data_store.DB.Transaction(subject, token=self.token)
    t2.Set(predicate, "2")
    t2.Commit()

    self.assertEqual(
        data_store.DB.Resolve(subject, predicate, token=self.token)[0], "2")

    # Check that ResolveRegex works correctly.
    predicate1 = u"metadata:attribute10"
    predicate1regex = "metadata:attribute1[0-9]"
    predicate2 = u"metadata:attribute20"

    t3 = data_store.DB.Transaction(subject, token=self.token)
    t3.Set(predicate1, "10")
    t3.Set(predicate2, "20")

    self.assertEqual(t3.ResolveRegex(predicate1regex)[0][1], "10")
    self.assertEqual(
        t3.ResolveRegex(predicate1regex,
                        timestamp=data_store.DB.NEWEST_TIMESTAMP)[0][1], "10")
    t3.Commit()

    self.assertEqual(t3.Resolve(predicate1)[0], "10")
    self.assertEqual(t3.Resolve(predicate2)[0], "20")
    self.assertEqual(t3.ResolveRegex(predicate1regex)[0][1], "10")
    self.assertEqual(
        t3.ResolveRegex(predicate1regex,
                        timestamp=data_store.DB.NEWEST_TIMESTAMP)[0][1], "10")

    t4 = data_store.DB.Transaction(subject, token=self.token)

    t4.DeleteAttribute(predicate1)

    self.assertEqual(t4.Resolve(predicate1), (None, 0))
    self.assertEqual(len(t4.ResolveRegex(predicate1regex)), 0)
    self.assertEqual(t4.Resolve(predicate2)[0], "20")
    t4.Commit()

    self.assertEqual(t4.Resolve(predicate1), (None, 0))
    self.assertEqual(len(t4.ResolveRegex(predicate1regex)), 0)

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

  @TransactionTest
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

  @TransactionTest
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

  @TransactionTest
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

  @TransactionTest
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
    with utils.Stubber(time, "sleep", MockSleep):
      data_store.DB.RetryWrapper(subject, Callback, token=self.token)

  def testTimestamps(self):
    """Check that timestamps are reasonable."""
    predicate = "metadata:predicate"
    subject = "aff4:test_timestamps"

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
    subject = "aff4:/test_specific_timestamps"

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
    subject = "aff4:/test_newest_timestamps"

    # Check we can specify a timestamp
    data_store.DB.Set(
        subject, predicate1, "1.1", timestamp=1000, replace=False,
        token=self.token)
    data_store.DB.Set(
        subject, predicate1, "1.2", timestamp=2000, replace=False,
        token=self.token)
    data_store.DB.Set(
        subject, predicate2, "2.1", timestamp=1010, replace=False,
        token=self.token)
    data_store.DB.Set(
        subject, predicate2, "2.2", timestamp=2020, replace=False,
        token=self.token)

    result = data_store.DB.ResolveRegex(
        subject, predicate1, timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token)

    # Should return 2 results. Newest should be first.
    values = [x[1] for x in result]
    self.assertEqual(len(values), 2)
    self.assertListEqual(values, ["1.2", "1.1"])
    times = [x[2] for x in result]
    self.assertListEqual(times, [2000, 1000])

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

    self.assertEqual(len(result), 4)
    self.assertListEqual([r for r in result if r[0] == "metadata:predicate1"], [
        (u"metadata:predicate1", "1.2", 2000),
        (u"metadata:predicate1", "1.1", 1000)])
    self.assertListEqual([r for r in result if r[0] == "metadata:predicate2"], [
        (u"metadata:predicate2", "2.2", 2020),
        (u"metadata:predicate2", "2.1", 1010)])

    result = list(data_store.DB.ResolveRegex(
        subject, "metadata:.*", timestamp=data_store.DB.NEWEST_TIMESTAMP,
        token=self.token))

    # Should only return the latest version.
    self.assertItemsEqual(result, [
        (u"metadata:predicate1", "1.2", 2000),
        (u"metadata:predicate2", "2.2", 2020)])

  def testResolveRegEx(self):
    """Test regex Resolving works."""
    predicate = "metadata:predicate"
    subject = "aff4:/resolve_regex"

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
    subject = "aff4:/test_resolve_regex_prefix"

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
    subject = "aff4:/resolve_multi"

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
    fd.SetChunksize(512 * 1024)
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
  @TransactionTest
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

  def _InstallACLChecks(self, forbidden_access):
    if self.acls_installed:
      raise RuntimeError("Seems like _InstallACLChecks was called twice in one "
                         "test")

    self.acls_installed = True
    data_store.DB.security_manager = test_lib.MockSecurityManager(
        forbidden_datastore_access=forbidden_access)

  def _ListedMultiResolveRegex(self, *args, **kwargs):
    return list(data_store.DB.MultiResolveRegex(*args, **kwargs))

  def _ListedResolveMulti(self, *args, **kwargs):
    return list(data_store.DB.ResolveMulti(*args, **kwargs))

  def _ListedResolveRegex(self, *args, **kwargs):
    return list(data_store.DB.ResolveRegex(*args, **kwargs))

  def _FlushedDeleteSubject(self, *args, **kwargs):
    # DeleteSubject is not guaranteed to be synchronous. Make sure that
    # we flush data store when testing it.
    data_store.DB.DeleteSubject(*args, **kwargs)
    data_store.DB.Flush()

  def testSetChecksWriteAccess(self):
    self._InstallACLChecks("w")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        data_store.DB.Set,
        self.test_row, "task:00000001", rdfvalue.GrrMessage(), token=self.token)

  @DeletionTest
  def testDeleteSubjectChecksWriteAccess(self):
    self._InstallACLChecks("w")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._FlushedDeleteSubject,
        self.test_row, token=self.token)

  def testMultiSetChecksWriteAccess(self):
    self._InstallACLChecks("w")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        data_store.DB.MultiSet,
        self.test_row, {"aff4:size": [(1, 100)],
                        "aff4:stored": [("foo", 200)]},
        token=self.token)

  @DeletionTest
  def testDeleteAttributesChecksWriteAccess(self):
    self._InstallACLChecks("w")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        data_store.DB.DeleteAttributes,
        self.test_row, ["metadata:predicate"], sync=True, token=self.token)

  def testMultiResolveRegexChecksReadAccess(self):
    self._InstallACLChecks("r")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedMultiResolveRegex,
        [self.test_row], ["task:.*"], token=self.token)

  def testMultiResolveRegexChecksQueryAccessWhenAccessingIndex(self):
    self._InstallACLChecks("q")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedMultiResolveRegex,
        [self.test_row], ["index:.*"], token=self.token)

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedMultiResolveRegex,
        [self.test_row], ["task:.*", "index:.*"], token=self.token)

    # Check that simple resolve doesn't require query access.
    self._ListedMultiResolveRegex(
        [self.test_row], ["task:.*"], token=self.token)

  def testResolveMultiChecksReadAccess(self):
    self._InstallACLChecks("r")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedResolveMulti,
        self.test_row, ["task:000000001"], token=self.token)

  def testResolveMultiChecksQueryAccessWhenAccessingIndex(self):
    self._InstallACLChecks("q")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedResolveMulti,
        self.test_row, ["index:dir/foo"], token=self.token)

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedResolveMulti,
        self.test_row, ["task:00000001", "index:dir/foo"], token=self.token)

    # Check that simple resolve doesn't require query access.
    self._ListedResolveMulti(
        self.test_row, ["task:00000001"], token=self.token)

  def testResolveRegexChecksReadAccess(self):
    self._InstallACLChecks("r")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedResolveRegex,
        self.test_row, "task:.*", token=self.token)

  def testResolveRegexChecksQueryAccessWhenAccessingIndex(self):
    self._InstallACLChecks("q")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        self._ListedResolveRegex,
        self.test_row, "index:.*", token=self.token)

    # Check that simple resolve doesn't require query access.
    self._ListedResolveRegex(
        self.test_row, "task:.*", token=self.token)

  def testResolveChecksReadAccess(self):
    self._InstallACLChecks("r")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        data_store.DB.Resolve,
        self.test_row, "task:000000001", token=self.token)

  def testResolveChecksQueryAccessWhenAccessingIndex(self):
    self._InstallACLChecks("q")

    self.assertRaises(
        access_control.UnauthorizedAccess,
        data_store.DB.Resolve,
        self.test_row, "index:dir/foo", token=self.token)

    # Check that simple resolve doesn't require query access.
    data_store.DB.Resolve(
        self.test_row, "task:00000001", token=self.token)

  def testLimits(self):

    # Create 10 rows with 10 attributes each.
    subjects = ["aff4:limittest_%d" % i for i in xrange(10)]
    attributes = ["metadata:limittest_%d" % i for i in xrange(10)]

    value_idx = 0
    for subject in subjects:
      for attribute in attributes:
        value = "value_%d" % value_idx
        value_idx += 1
        data_store.DB.Set(subject, attribute, value, token=self.token)

    # ResolveRegex.
    for limit in [1, 2, 5, 10, 100]:
      results = data_store.DB.ResolveRegex(
          subjects[0], "metadata:.*", limit=limit, token=self.token)
      self.assertEqual(len(results), min(limit, 10))

    # MultiResolveRegex.
    for limit in [1, 2, 5, 9, 10, 11, 25, 100, 120]:
      results = dict(data_store.DB.MultiResolveRegex(
          subjects, "metadata:.*", limit=limit, token=self.token))
      all_results = []
      for subect_res in results.itervalues():
        all_results.extend(subect_res)

      self.assertEqual(len(all_results), min(limit, 100))

    for limit in [1, 2, 5, 9, 10, 11, 25]:
      results = dict(data_store.DB.MultiResolveRegex(
          subjects, "metadata:limittest_7", limit=limit, token=self.token))
      all_results = []
      for subect_res in results.itervalues():
        all_results.extend(subect_res)

      self.assertEqual(len(all_results), min(limit, 10))

    # ResolveMulti.
    for limit in [1, 2, 5, 9, 10, 11, 25]:
      results = list(data_store.DB.ResolveMulti(
          subjects[2], attributes, limit=limit, token=self.token))

      self.assertEqual(len(results), min(limit, 10))

  def testApi(self):
    api = ["DeleteAttributes",
           "DeleteSubject",
           "MultiResolveRegex",
           "MultiSet",
           "Resolve",
           "ResolveMulti",
           "ResolveRegex",
           "Set",
           "Transaction"]

    implementation = data_store.DB
    reference = data_store.DataStore

    for f in api:
      implementation_spec = inspect.getargspec(getattr(implementation, f))
      reference_spec = inspect.getargspec(getattr(reference, f))
      self.assertEqual(
          implementation_spec, reference_spec,
          "Signatures for function %s not matching: \n%s !=\n%s" %(
              f, implementation_spec, reference_spec))


class DataStoreCSVBenchmarks(test_lib.MicroBenchmarks):
  """Long running benchmarks where the results are dumped to a CSV file.

  These tests are deliberately not named with the test prefix, since they need
  to be run individually to get true performance data. Run by specifying the
  testname with --test and setting --labels=benchmark.

  The CSV output filename will be printed in a log message at the end of the
  test.
  """

  # What we consider as a big number of attributes.
  BIG_NUM_ATTRIBUTES = 1000

  units = "s"

  # Database counters.
  subjects = 0
  predicates = 0
  values = 0
  queries_total = 0  # Total queries.
  queries_last_timestep = 0  # Number of the queries up to the last timestep.
  steps = 0  # How many steps so far.

  query_interval = 3000  # A step is composed of this many queries.

  test_name = ""  # Current operation being run.
  start_time = None
  last_time = None
  predicate_template = "task:flow%d"

  def setUp(self):
    super(DataStoreCSVBenchmarks, self).setUp(["DB Size (KB)", "Queries",
                                               "Subjects", "Predicates",
                                               "Values"],
                                              ["<20", "<10", "<10", "<10",
                                               "<10"])
    self.InitDatastore()
    self.start_time = time.time()
    self.last_time = self.start_time

  def tearDown(self):
    self.Register(force=True)
    super(DataStoreCSVBenchmarks, self).tearDown()
    self.WriteCSV()
    self.DestroyDatastore()

  def Register(self, force=False):
    """Add a new result line to the benchmark result."""
    self.queries_total += 1
    if self.queries_total % self.query_interval == 0 or force:
      data_store.DB.Flush()
      this_time = time.time()
      queries_diff = self.queries_total - self.queries_last_timestep
      self.queries_last_timestep = self.queries_total
      self.last_time = this_time
      self.steps += 1
      self.AddResult(self.test_name, this_time - self.start_time, self.steps,
                     data_store.DB.Size() / 1024, queries_diff, self.subjects,
                     self.predicates, self.values)

  def WriteCSV(self, remove=False):
    """Write results to a CSV file."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fp:
      writer = csv.writer(fp, delimiter=" ")
      writer.writerow(["Benchmark", "Time", "DBSize", "Queries", "Subjects",
                       "Predicates", "Values"])
      for row in self.scratchpad[2:]:
        writer.writerow([row[0], row[1], row[3], row[4], row[5],
                         row[6], row[7]])

      logging.info("CSV File is in %s", fp.name)
      if remove:
        os.unlink(fp.name)

  def _RandomlyReadSubject(self, subject, predicates):
    """Read certain parts of a given subject."""
    for j, timestamps in predicates.items():
      which = self.rand.randint(0, 2)
      if which == 0:
        # Read all timestamps.
        data_store.DB.ResolveRegex(subject, self.predicate_template % j,
                                   timestamp=data_store.DB.ALL_TIMESTAMPS,
                                   token=self.token)
      elif which == 1:
        # Read a specific timestamp.
        if timestamps:
          ts = self.rand.choice(timestamps)
          data_store.DB.ResolveRegex(subject, self.predicate_template % j,
                                     timestamp=(ts, ts), token=self.token)
      elif which == 2:
        # Read latest.
        data_store.DB.Resolve(subject, self.predicate_template % j,
                              token=self.token)
      self.Register()
    if self.rand.randint(0, 1) == 0:
      # Find all attributes.
      data_store.DB.ResolveRegex(subject, "task:flow.*",
                                 timestamp=data_store.DB.NEWEST_TIMESTAMP,
                                 token=self.token)
      self.Register()

  def _ReadRandom(self, subjects, fraction, change_test=True):
    """Randomly read the database."""
    if change_test:
      self.test_name = "read random %d%%" % fraction
    for _ in range(0, int(float(len(subjects)) * float(fraction) / 100.0)):
      i = self.rand.choice(subjects.keys())
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      self._RandomlyReadSubject(subject, predicates)

  def _UpdateRandom(self, subjects, fraction, change_test=True):
    """Update values/predicates for a given fraction of the subjects."""
    if change_test:
      self.test_name = "update %d%%" % fraction
    new_value = os.urandom(100)
    for i in subjects:
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      if self.rand.randint(0, 100) > fraction:
        continue
      which = self.rand.randint(0, 2)
      if which == 0 or which == 1:
        for j, timestamp_info in predicates.items():
          number_timestamps = len(timestamp_info)
          if which == 0 and len(timestamp_info):
            # Update one timestamp'ed value.
            data_store.DB.Set(subject, self.predicate_template % j, new_value,
                              timestamp=timestamp_info[-1], token=self.token)
            self.Register()
          elif which == 1:
            # Add another timestamp.
            timestamp_info.append(100 * number_timestamps + 1)
            data_store.DB.Set(subject, self.predicate_template % j, new_value,
                              timestamp=timestamp_info[-1], token=self.token)
            self.values += 1
            self.Register()
      elif which == 2:
        # Add an extra predicate.
        j = len(predicates)
        number_timestamps = self.rand.randrange(1, 3)
        ts = [100 * (ts + 1) for ts in xrange(number_timestamps)]
        predicates[j] = ts
        self.values += number_timestamps
        self.predicates += 1
        values = [(new_value, t) for t in ts]
        data_store.DB.MultiSet(subject, {self.predicate_template % j: values},
                               timestamp=100, token=self.token)
        self.Register()
    data_store.DB.Flush()

  def _DeleteRandom(self, subjects, fraction, change_test=True):
    """Delete predicates/subjects/values at random."""
    if change_test:
      self.test_name = "delete %d%%" % fraction
    subjects_to_delete = []
    for i, info in subjects.items():
      subject = info["name"]
      predicates = info["attrs"]
      number_predicates = len(predicates)
      do_it = (self.rand.randint(0, 100) <= fraction)
      which = self.rand.randint(0, 2)
      count_values = 0
      predicates_to_delete = []
      for j, timestamp_info in predicates.items():
        number_timestamps = len(timestamp_info)
        count_values += number_timestamps
        if do_it:
          if which == 0:
            # Delete one timestamp'ed value.
            if timestamp_info:
              ts = timestamp_info[0]
              data_store.DB.DeleteAttributes(subject,
                                             [self.predicate_template % j],
                                             start=ts, end=ts,
                                             token=self.token)
              self.values -= 1
              timestamp_info.pop(0)
              self.Register()
            else:
              which = 1
          if which == 1:
            # Delete the attribute itself.
            data_store.DB.DeleteAttributes(subject,
                                           [self.predicate_template % j],
                                           token=self.token)
            self.values -= number_timestamps
            self.predicates -= 1
            predicates_to_delete.append(j)
            self.Register()
      if do_it and which == 1:
        for j in predicates_to_delete:
          del predicates[j]
      if do_it and which == 2:
        # Delete subject.
        data_store.DB.DeleteSubject(subject, token=self.token)
        self.predicates -= number_predicates
        self.values -= count_values
        self.subjects -= 1
        subjects_to_delete.append(i)
        self.Register()
    for i in subjects_to_delete:
      del subjects[i]
    data_store.DB.Flush()

  def _GrowRandomly(self, subjects, fraction, nclients, change_test=True):
    """Adds new clients/subjects to the database."""
    if change_test:
      self.test_name = "add %d%%" % fraction
    how_many = int(float(len(subjects)) * float(fraction) / 100)
    new_value = os.urandom(100)
    new_subject = max(subjects.iteritems(),
                      key=operator.itemgetter(0))[0] + 1
    # Generate client names.
    clients = [self._GenerateRandomClient() for _ in xrange(nclients)]
    for i in xrange(new_subject, new_subject + how_many):
      client = clients[self.rand.randint(0, nclients - 1)]
      self._AddNewSubject(client, subjects, i, new_value)
    data_store.DB.Flush()

  def _GenerateRandomSubject(self):
    n = self.rand.randint(1, 5)
    seps = [self._GenerateRandomString(self.rand.randint(5, 10))
            for _ in xrange(n)]
    return "/".join(seps)

  def _AddNewSubject(self, client, subjects, i, value, max_attributes=3):
    """Add a new subject to the database."""
    number_predicates = self.rand.randrange(1, max_attributes)
    self.subjects += 1
    predicates = dict.fromkeys(xrange(number_predicates))
    self.predicates += number_predicates
    subject = str(client.Add(self._GenerateRandomSubject()))
    for j in xrange(number_predicates):
      number_timestamps = self.rand.randrange(1, 3)
      self.values += number_timestamps
      ts = [100 * (ts + 1) for ts in xrange(number_timestamps)]
      predicates[j] = ts
      values = [(value, t) for t in ts]
      data_store.DB.MultiSet(subject, {self.predicate_template % j: values},
                             timestamp=100, sync=False, token=self.token)
      self.Register()
    info = {"name": subject, "attrs": predicates}
    subjects[i] = info

  def _ReadLinear(self, subjects, fraction):
    """Linearly read subjects from the database."""
    self.test_name = "read linear %d%%" % fraction
    for i in subjects:
      if self.rand.randint(0, 100) > fraction:
        return
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      self._RandomlyReadSubject(subject, predicates)

  def _AddManyAttributes(self, subjects, many):
    """Add lots of predicates to a given number of subjects."""
    self.test_name = "add +attrs %d" % many
    new_value = os.urandom(100)
    for _ in range(0, many):
      i = self.rand.choice(subjects.keys())
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      how_many = self.rand.randint(self.BIG_NUM_ATTRIBUTES,
                                   self.BIG_NUM_ATTRIBUTES + 1000)
      self.predicates += how_many
      new_predicate = max(predicates.iteritems(),
                          key=operator.itemgetter(0))[0] + 1
      for j in xrange(new_predicate, new_predicate + how_many):
        number_timestamps = self.rand.randrange(1, 3)
        ts = [100 * (ts + 1) for ts in xrange(number_timestamps)]
        self.values += number_timestamps
        values = [(new_value, t) for t in ts]
        predicates[j] = ts
        data_store.DB.MultiSet(subject, {self.predicate_template % j: values},
                               timestamp=100, sync=False, token=self.token)
        self.Register()
    data_store.DB.Flush()

  def _RemoveManyAttributes(self, subjects, fraction):
    """Delete all predicates (except 1) from subjects with many predicates."""
    self.test_name = "del +attrs %d%%" % fraction
    often = 100 / fraction
    count = 0
    for i in subjects:
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      number_predicates = len(predicates)
      if number_predicates >= self.BIG_NUM_ATTRIBUTES:
        count += 1
        if count == often:
          count = 0
          predicates_to_delete = [j for j in predicates.keys()[1:]]
          values_deleted = sum(len(predicates[x])
                               for x in predicates_to_delete)
          self.values -= values_deleted
          self.predicates -= len(predicates_to_delete)
          for j in predicates_to_delete:
            del predicates[j]
            data_store.DB.DeleteAttributes(subject,
                                           [self.predicate_template % j],
                                           sync=False, token=self.token)
            self.Register()
    data_store.DB.Flush()

  def _Wipeout(self, subjects):
    """Delete every subject from the database."""
    self.test_name = "wipeout"
    for i in subjects:
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      number_predicates = len(predicates)
      count_values = 0
      for j in predicates:
        count_values += len(predicates[j])
      data_store.DB.DeleteSubject(subject, token=self.token)
      self.predicates -= number_predicates
      self.values -= count_values
      self.subjects -= 1
      self.Register()
    subjects = {}
    data_store.DB.Flush()

  def _DoMix(self, subjects):
    """Do a mix of database operations."""
    self.test_name = "mix"
    for _ in xrange(0, len(subjects) / 2000):
      # Do random operations.
      op = self.rand.randint(0, 3)
      if op == 0:
        self._ReadRandom(subjects, 14, False)
      elif op == 1:
        self._GrowRandomly(subjects, 5, 20, False)
      elif op == 2:
        self._UpdateRandom(subjects, 10, False)
      elif op == 3:
        self._DeleteRandom(subjects, 4, False)

  def _GenerateRandomClient(self):
    return rdfvalue.ClientURN("C.%016d" % self.rand.randint(0, (10 ** 16) - 1))

  def _FillDatabase(self, nsubjects, nclients,
                    max_attributes=3):
    """Fill the database with a certain number of subjects and clients."""
    self.rand = random.Random(0)
    self.test_name = "fill"
    self.AddResult(self.test_name, 0, self.steps, data_store.DB.Size(),
                   0, 0, 0, 0)
    subjects = dict.fromkeys(xrange(nsubjects))
    value = os.urandom(100)
    clients = [self._GenerateRandomClient() for _ in xrange(nclients)]
    for i in subjects:
      client = self.rand.choice(clients)
      self._AddNewSubject(client, subjects, i, value, max_attributes)
    data_store.DB.Flush()
    return subjects

  def _GenerateRandomString(self, chars):
    return "".join([self.rand.choice(string.ascii_letters)
                    for _ in xrange(chars)])

  def _AddBlobs(self, howmany, size):
    """Adds 'howmany' blobs with size 'size' kbs."""
    self.test_name = "add blobs %dx%dk" % (howmany, size)
    blob_info = []
    count = 0
    often = howmany / 10

    for count in xrange(howmany):
      data = self._GenerateRandomString(1024 * size)

      # Create a blob.
      digest = hashlib.sha256(data).digest()
      code = digest.encode("hex")
      urn = aff4.ROOT_URN.Add("blobs").Add(code)
      blob_fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", mode="w",
                                    token=self.token)
      blob_fd.Write(data)
      blob_fd.Close(sync=True)

      blob_info.append(urn)

      if count % often == 0:
        # Because adding blobs, takes too long we force the output of
        # new results.
        self.Register(force=True)

    self.Register(force=True)
    data_store.DB.Flush()
    return blob_info

  @test_lib.SetLabel("benchmark")
  def manySubjectsFewAttrs(self):
    """Database with many subjects with few attributes."""
    subjects = self._FillDatabase(25000, 500)
    self._ReadLinear(subjects, 50)
    self._UpdateRandom(subjects, 50)
    self._ReadRandom(subjects, 70)
    self._DeleteRandom(subjects, 40)
    self._GrowRandomly(subjects, 40, 50)
    self._ReadRandom(subjects, 100)
    self._DoMix(subjects)
    self._Wipeout(subjects)

  @test_lib.SetLabel("benchmark")
  def manySubjectsFewWithManyAttrs(self):
    """Database where a few subjects have many attributes."""
    subjects = self._FillDatabase(25000, 500)
    self._UpdateRandom(subjects, 50)
    self._AddManyAttributes(subjects, 100)
    self._ReadRandom(subjects, 30)

    # For 1/2 of the subjects with many attributes, remove all but
    # one of the attributes.
    self._RemoveManyAttributes(subjects, 50)

    self._ReadRandom(subjects, 30)
    self._UpdateRandom(subjects, 50)
    self._Wipeout(subjects)

  @test_lib.SetLabel("benchmark")
  def fewSubjectsManyAttrs(self):
    """Database with a few subjects with many attributes."""
    subjects = self._FillDatabase(100, 5)
    self._UpdateRandom(subjects, 100)
    self._AddManyAttributes(subjects, 50)
    self._ReadRandom(subjects, 30)
    self._RemoveManyAttributes(subjects, 50)
    self._ReadRandom(subjects, 50)
    self._Wipeout(subjects)

  @test_lib.SetLabel("benchmark")
  def blobs(self):
    """Database that stores blobs of increasing size."""
    subjects = self._FillDatabase(10000, 200)

    def _ReadUpdate():
      self._ReadRandom(subjects, 75)
      self._UpdateRandom(subjects, 20)

    _ReadUpdate()

    self._AddBlobs(50, 512)
    _ReadUpdate()

    self._AddBlobs(50, 2048)
    _ReadUpdate()

    self._AddBlobs(50, 10240)
    _ReadUpdate()

    self._AddBlobs(20, 10240 * 10)
    _ReadUpdate()

  @test_lib.SetLabel("benchmark")
  def manySubjectsManyAttrs(self):
    """Database with many subjects with many attributes."""
    subjects = self._FillDatabase(25000, 500, 50)
    self._ReadLinear(subjects, 50)
    self._UpdateRandom(subjects, 50)
    self._ReadRandom(subjects, 50)
    self._DeleteRandom(subjects, 40)
    self._GrowRandomly(subjects, 40, 50)
    self._ReadRandom(subjects, 50)
    self._DoMix(subjects)
    self._Wipeout(subjects)


class DataStoreBenchmarks(test_lib.MicroBenchmarks):
  """Datastore micro benchmarks.

  These tests should be run with --labels=benchmark
  """
  queue = rdfvalue.RDFURN("BENCHMARK")
  units = "s"

  def setUp(self):
    super(DataStoreBenchmarks, self).setUp()
    self.InitDatastore()
    self.tp = threadpool.ThreadPool.Factory("test_pool", 50)
    self.tp.Start()

  def tearDown(self):
    super(DataStoreBenchmarks, self).tearDown()
    self.tp.Stop()
    self.DestroyDatastore()

  def InitDatastore(self):
    """Initiates custom data store."""

  def DestroyDatastore(self):
    """Destroys custom data store."""

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
                                     flow_name="ListDirectory",
                                     queue=self.queue,
                                     pathspec=rdfvalue.PathSpec(
                                         path="/",
                                         pathtype="OS",
                                     ),
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
            request_id=1, response_id=1 + i,
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

    notifications = [
        rdfvalue.GrrNotification(session_id=f) for f in self.flow_ids]
    with queue_manager.QueueManager(sync=True, token=self.token) as manager:
      manager.MultiNotifyQueue(notifications)

    time_used = time.time() - start_time

    self.AddResult("Generate Messages (%d clients, %d files)" % (
        self.nr_clients, self.nr_dirs * self.files_per_dir), time_used, 1)

    my_worker = worker.GRRWorker(queues=[self.queue], token=self.token)

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
