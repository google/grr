#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""These are basic tests for the data store abstraction.

Implementations should be able to pass these tests to be conformant.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import inspect
import logging
import operator
import os
import random
import string
import tempfile
import threading
import time


import _thread
from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues
import mock
import pytest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import csv
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import queue_manager
from grr_response_server import sequential_collection
from grr_response_server import threadpool
from grr_response_server import worker_lib
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import standard
from grr_response_server.flows.general import filesystem
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import benchmark_test_lib
from grr.test_lib import test_lib


class StringSequentialCollection(
    sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdfvalue.RDFString


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


def DBSubjectLockTest(f):
  """This indicates a test that uses locks."""

  @functools.wraps(f)
  def Decorator(testinstance):
    if testinstance.TEST_DBSUBJECTLOCKS:
      return f(testinstance)
    else:
      return testinstance.skipTest("Tests that use locks are disabled "
                                   "for this data store.")

  return Decorator


class DataStoreTestMixin(object):
  """Test the data store abstraction.

  Note that when testing timestamp behavior the cloud bigtable datastore only
  has ms precision.
  """
  test_row = "aff4:/row:foo"
  lease_row = u"aff4:/leasetest"

  # This flag controls if tests can also delete data. Some data stores don't
  # support deletion so those tests will fail for them.
  TEST_DELETION = True
  # The same applies to locks.
  TEST_DBSUBJECTLOCKS = True

  def setUp(self):
    super(DataStoreTestMixin, self).setUp()
    data_store.DB.ClearTestDB()

  def _TruncateToMilliseconds(self, timestamp_int):
    timestamp_int -= (timestamp_int % 1000)
    return timestamp_int

  def testSetResolve(self):
    """Test the Set() and Resolve() methods."""
    predicate = "task:00000001"
    value = rdf_flows.GrrMessage(session_id="session")

    # Ensure that setting a value is immediately available.
    data_store.DB.Set(self.test_row, predicate, value)
    time.sleep(1)
    data_store.DB.Set(self.test_row + "X", predicate, value)
    stored_proto, _ = data_store.DB.Resolve(self.test_row, predicate)

    stored_proto = rdf_flows.GrrMessage.FromSerializedString(stored_proto)
    self.assertEqual(stored_proto.session_id, value.session_id)

  def testSetResolveNegativeInteger(self):
    data_store.DB.Set(self.test_row, "aff4:lastchunk", -1)
    value, _ = data_store.DB.Resolve(self.test_row, "aff4:lastchunk")
    self.assertEqual(value, -1)

  def testMultiSet(self):
    """Test the MultiSet() methods."""
    unicode_string = u"this is a uñîcödé string"
    data_store.DB.MultiSet(
        self.test_row, {
            "aff4:size": [1],
            "aff4:stored": [unicode_string],
            "aff4:unknown_attribute": ["hello"]
        })

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertEqual(stored, 1)

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:stored")
    self.assertEqual(stored, unicode_string)

    # Make sure that unknown attributes are stored as bytes.
    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:unknown_attribute")
    self.assertEqual(stored, "hello")
    self.assertEqual(type(stored), str)

  def testMultiSetTimestamps(self):
    unicode_string = u"this is a uñîcödé string"
    data_store.DB.MultiSet(self.test_row, {
        "aff4:size": [(1, 1000)],
        "aff4:stored": [(unicode_string, 2000)]
    })

    stored, ts = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertEqual(stored, 1)
    self.assertEqual(ts, 1000)

    stored, ts = data_store.DB.Resolve(self.test_row, "aff4:stored")
    self.assertEqual(stored, unicode_string)
    self.assertEqual(ts, 2000)

  def testMultiSetNoneTimestampIsNow(self):
    unicode_string = u"this is a uñîcödé string"
    start_time = time.time() * 1e6
    # Test None timestamp is translated to current time.
    data_store.DB.MultiSet(self.test_row, {
        "aff4:size": [(1, None)],
        "aff4:stored": [(unicode_string, 2000)]
    })
    end_time = time.time() * 1e6
    stored, ts = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertEqual(stored, 1)
    self.assertGreaterEqual(ts, start_time)
    self.assertLessEqual(ts, end_time)

    stored, ts = data_store.DB.Resolve(self.test_row, "aff4:stored")
    self.assertEqual(stored, unicode_string)
    self.assertEqual(ts, 2000)

  def testMultiSetAsync(self):
    """Test the async MultiSet() methods."""
    unicode_string = u"this is a uñîcödé string"

    data_store.DB.MultiSet(
        self.test_row, {
            "aff4:size": [3],
            "aff4:stored": [unicode_string],
            "aff4:unknown_attribute": ["hello"]
        },
        sync=False)
    data_store.DB.Flush()

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertEqual(stored, 3)

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:stored")

    self.assertEqual(stored, unicode_string)

    # Make sure that unknown attributes are stored as bytes.
    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:unknown_attribute")
    self.assertEqual(stored, "hello")
    self.assertEqual(type(stored), str)

  def testMultiSet2(self):
    """Test the MultiSet() methods."""
    # Specify a per element timestamp
    data_store.DB.MultiSet(self.test_row, {
        "aff4:size": [(1, 1000)],
        "aff4:stored": [("2", 2000)]
    })

    stored, ts = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertEqual(stored, 1)
    self.assertEqual(ts, 1000)

    stored, ts = data_store.DB.Resolve(self.test_row, "aff4:stored")
    self.assertEqual(stored, "2")
    self.assertEqual(ts, 2000)

  def testMultiSet3(self):
    """Test the MultiSet() delete methods."""
    data_store.DB.MultiSet(self.test_row, {
        "aff4:size": [1],
        "aff4:stored": ["2"]
    })

    data_store.DB.MultiSet(
        self.test_row, {"aff4:stored": ["2"]}, to_delete=["aff4:size"])

    # This should be gone now
    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertIsNone(stored)

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:stored")
    self.assertEqual(stored, "2")

  def testMultiSet4(self):
    """Test the MultiSet() delete methods when deleting the same predicate."""
    data_store.DB.MultiSet(self.test_row, {
        "aff4:size": [1],
        "aff4:stored": ["2"]
    })

    data_store.DB.MultiSet(
        self.test_row, {"aff4:size": [4]}, to_delete=["aff4:size"])

    # This should only produce a single result
    count = 0
    for count, (predicate, value, _) in enumerate(
        data_store.DB.ResolvePrefix(
            self.test_row, "aff4:size",
            timestamp=data_store.DB.ALL_TIMESTAMPS)):
      self.assertEqual(value, 4)
      self.assertEqual(predicate, "aff4:size")

    self.assertEqual(count, 0)

  def testMultiSetSetsTimestapWhenReplacing(self):
    data_store.DB.MultiSet(
        self.test_row, {"aff4:size": [(1, 1000)]}, replace=True)

    stored, ts = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertEqual(stored, 1)
    self.assertEqual(ts, 1000)

  def testMultiSetRemovesOtherValuesWhenReplacing(self):
    data_store.DB.MultiSet(
        self.test_row, {"aff4:stored": [("2", 1000), ("3", 4000)]},
        replace=False)

    values = data_store.DB.ResolvePrefix(
        self.test_row, "aff4:stored", timestamp=data_store.DB.ALL_TIMESTAMPS)
    self.assertListEqual(values, [("aff4:stored", "3", 4000),
                                  ("aff4:stored", "2", 1000)])

    data_store.DB.MultiSet(
        self.test_row, {"aff4:stored": [("4", 3000)]}, replace=True)
    values = data_store.DB.ResolvePrefix(
        self.test_row, "aff4:stored", timestamp=data_store.DB.ALL_TIMESTAMPS)
    self.assertListEqual(values, [("aff4:stored", "4", 3000)])

  @DeletionTest
  def testDeleteAttributes(self):
    """Test we can delete an attribute."""
    predicate = "metadata:predicate"

    data_store.DB.Set(self.test_row, predicate, "hello")

    # Check it's there.
    stored, _ = data_store.DB.Resolve(self.test_row, predicate)

    self.assertEqual(stored, "hello")

    data_store.DB.DeleteAttributes(self.test_row, [predicate], sync=True)
    stored, _ = data_store.DB.Resolve(self.test_row, predicate)

    self.assertIsNone(stored)

  @DeletionTest
  def testMultiDeleteAttributes(self):
    """Test we can delete multiple attributes at once."""

    test_rows = ["aff4:/row/%i" % i for i in range(0, 10)]
    predicate_1 = "metadata:predicate1"
    predicate_2 = "metadata:predicate2"

    for row in test_rows:
      data_store.DB.Set(row, predicate_1, "hello")
      data_store.DB.Set(row, predicate_2, "hello")

    self.assertLen(
        list(data_store.DB.ScanAttribute("aff4:/row/", predicate_1)), 10)
    self.assertLen(
        list(data_store.DB.ScanAttribute("aff4:/row/", predicate_2)), 10)
    data_store.DB.MultiDeleteAttributes(test_rows, [predicate_1, predicate_2])
    self.assertFalse(
        list(data_store.DB.ScanAttribute("aff4:/row/", predicate_1)))
    self.assertFalse(
        list(data_store.DB.ScanAttribute("aff4:/row/", predicate_2)))

  def CheckLength(self, predicate, l):
    all_attributes = data_store.DB.ResolveMulti(
        self.test_row, [predicate], timestamp=(0, 5000))

    self.assertLen(list(all_attributes), l)

  def CheckLast(self, predicate, expected_value, exptected_ts):
    stored, ts = data_store.DB.Resolve(self.test_row, predicate)
    self.assertEqual(stored, expected_value)
    self.assertEqual(ts, exptected_ts)

  @DeletionTest
  def testDeleteAttributesTimestamps(self):
    """Test we can delete an attribute in a time range."""
    predicate = "metadata:tspredicate"

    data_store.DB.Set(
        self.test_row, predicate, "hello1000", timestamp=1000, replace=False)
    data_store.DB.Set(
        self.test_row, predicate, "hello2000", timestamp=2000, replace=False)
    data_store.DB.Set(
        self.test_row, predicate, "hello3000", timestamp=3000, replace=False)
    data_store.DB.Set(
        self.test_row, predicate, "hello4000", timestamp=4000, replace=False)

    # Check its there
    self.CheckLast(predicate, "hello4000", 4000)
    self.CheckLength(predicate, 4)

    # Delete timestamps between 0 and 1500.
    data_store.DB.DeleteAttributes(
        self.test_row, [predicate], start=0, end=1500, sync=True)

    self.CheckLast(predicate, "hello4000", 4000)
    self.CheckLength(predicate, 3)

    # Delete timestamps between 3000 and 4500.
    data_store.DB.DeleteAttributes(
        self.test_row, [predicate], start=3000, end=4500, sync=True)

    self.CheckLast(predicate, "hello2000", 2000)
    self.CheckLength(predicate, 1)

    # Delete everything.
    data_store.DB.DeleteAttributes(
        self.test_row, [predicate], start=0, end=5000, sync=True)

    self.CheckLast(predicate, None, 0)
    self.CheckLength(predicate, 0)

  @DeletionTest
  def testDeleteSubject(self):
    predicate = "metadata:tspredicate"

    data_store.DB.Set(
        self.test_row, predicate, "hello1000", timestamp=1000, replace=False)
    data_store.DB.DeleteSubject(self.test_row, sync=True)
    self.CheckLength(predicate, 0)

    # This should work with the sync argument too.
    data_store.DB.Set(
        self.test_row, predicate, "hello1000", timestamp=1000, replace=False)
    data_store.DB.DeleteSubject(self.test_row, sync=True)
    self.CheckLength(predicate, 0)

  @DeletionTest
  def testDeleteSubjects(self):
    row_template = "aff4:/deletesubjectstest%d"
    rows = [row_template % i for i in range(100)]
    predicate = "metadata:tspredicate"

    for i, row in enumerate(rows):
      data_store.DB.Set(
          row, predicate, "hello%d" % i, timestamp=1000, replace=False)

    data_store.DB.DeleteSubjects(rows[20:80], sync=True)

    res = dict(data_store.DB.MultiResolvePrefix(rows, predicate))
    for i in range(100):
      if 20 <= i < 80:
        # These rows have been deleted.
        self.assertNotIn(row_template % i, res)
      else:
        # These rows should be present.
        self.assertIn(row_template % i, res)

  def testMultiResolvePrefix(self):
    """tests MultiResolvePrefix."""
    rows = self._MakeTimestampedRows()

    subjects = dict(
        data_store.DB.MultiResolvePrefix(rows, ["metadata:3", "metadata:7"]))

    subject_names = sorted(iterkeys(subjects))

    self.assertLen(subjects, 2)
    self.assertEqual(subject_names, [u"aff4:/row:3", u"aff4:/row:7"])

    rows = []
    for r in range(1, 6):
      row_name = "aff4:/prefix_row_%d" % r
      rows.append(row_name)
      for i in range(1, 6):
        timestamp = rdfvalue.RDFDatetime(1000 * i)
        data_store.DB.Set(
            row_name, "metadata:%s" % ("X" * i), str(i), timestamp=timestamp)

    subjects = dict(data_store.DB.MultiResolvePrefix(rows, ["metadata:"]))
    self.assertCountEqual(list(iterkeys(subjects)), rows)
    row = subjects["aff4:/prefix_row_4"]
    self.assertLen(row, 5)

    subjects = dict(data_store.DB.MultiResolvePrefix(rows, ["metadata:XXX"]))
    self.assertCountEqual(list(iterkeys(subjects)), rows)
    for row in itervalues(subjects):
      # Those with 3-5 X's.
      self.assertLen(row, 3)
      self.assertIn((u"metadata:XXX", "3", 3000), row)
      self.assertNotIn((u"metadata:XX", "2", 2000), row)

    # Test unicode subjects.
    unicode_string = u"this is a uñîcödé string"
    attributes = set()
    for i in range(5, 10):
      attributes.add(("metadata:%s" % i, "data%d" % i))
      data_store.DB.MultiSet(unicode_string,
                             {"metadata:%s" % i: ["data%d" % i]})

    result = dict(
        data_store.DB.MultiResolvePrefix([unicode_string], ["metadata:"]))

    result_set = set((k, v) for k, v, _ in result[unicode_string])
    self.assertEqual(result_set, attributes)

  def _MakeTimestampedRows(self):
    # Make some rows.
    rows = []
    for i in range(1, 6):
      row_name = "aff4:/row:%s" % i
      timestamp = rdfvalue.RDFDatetime(1000 * i)
      data_store.DB.Set(row_name, "metadata:%s" % i, i, timestamp=timestamp)
      rows.append(row_name)

    for i in range(6, 11):
      row_name = "aff4:/row:%s" % i
      timestamp = rdfvalue.RDFDatetime(1000 * i)
      data_store.DB.MultiSet(
          row_name, {"metadata:%s" % i: [i]}, timestamp=timestamp)
      rows.append(row_name)

    return rows

  def _CheckResultTimestamps(self, result, expected_timestamps):
    timestamps = []
    for predicates in itervalues(result):
      for predicate in predicates:
        timestamps.append(predicate[2])

    self.assertListEqual(sorted(timestamps), sorted(expected_timestamps))

  def testMultiResolvePrefixTypePreservation(self):
    """Check result subjects have same format as original calls."""
    rows = [
        "aff4:/row:str",
        u"aff4:/row:unicode",
        rdfvalue.RDFURN("aff4:/row:URN"),
        "aff4:/row:str",
        u"aff4:/row:unicode",
        rdfvalue.RDFURN("aff4:/row:URN"),
    ]

    i = 0
    for row_name in rows:
      timestamp = rdfvalue.RDFDatetime(1000 + i)
      data_store.DB.Set(row_name, "metadata:%s" % i, i, timestamp=timestamp)
      i += 1

    subjects = dict(
        data_store.DB.MultiResolvePrefix(
            rows, ["metadata:0", "metadata:2", "metadata:4"]))

    self.assertEqual(
        set([type(s) for s in subjects]), set([type(s) for s in rows]))

    self.assertIn(rows[0], subjects)
    self.assertIn(rows[2], subjects)
    self.assertIn(rows[4], subjects)

  def testResolvePrefixResultsOrderedInDecreasingTimestampOrder1(self):
    predicate1 = "metadata:predicate1"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order1"

    # Set 100 values with increasing timestamps.
    for i in range(100):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False)

    # Check that results will be returned in decreasing timestamp order.
    # This test along with a next one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = data_store.DB.ResolvePrefix(
        subject, predicate1, timestamp=data_store.DB.ALL_TIMESTAMPS)
    for result_index, i in enumerate(reversed(range(100))):
      self.assertEqual(result[result_index], (predicate1, str(i), i * 1000))

  def testResolvePrefixResultsOrderedInDecreasingTimestampOrder2(self):
    predicate1 = "metadata:predicate1"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order2"

    # Set 100 values with timestamps starting in the future and going to
    # the past.
    for i in reversed(range(100)):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False)

    # Check that results will be returned in decreasing timestamp order.
    # This test along with a previous one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = data_store.DB.ResolvePrefix(
        subject, predicate1, timestamp=data_store.DB.ALL_TIMESTAMPS)
    for result_index, i in enumerate(reversed(range(100))):
      self.assertEqual(result[result_index], (predicate1, str(i), i * 1000))

  def testResolvePrefixResultsOrderedInDecreasingTimestampOrderPerColumn1(self):
    predicate1 = "metadata:predicate1"
    predicate2 = "metadata:predicate2"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order_per_column1"

    # Set 100 values with increasing timestamps for each predicate.
    for i in range(100):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False)
      data_store.DB.Set(
          subject, predicate2, str(i), timestamp=i * 1000, replace=False)

    # Check that results will be returned in decreasing timestamp order
    # per column.
    # This test along with a previous one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = list(
        data_store.DB.ResolvePrefix(
            subject,
            "metadata:predicate",
            timestamp=data_store.DB.ALL_TIMESTAMPS,
            limit=1000))

    predicate1_results = [r for r in result if r[0] == predicate1]
    for result_index, i in enumerate(reversed(range(100))):
      self.assertEqual(predicate1_results[result_index],
                       (predicate1, str(i), i * 1000))

    predicate2_results = [r for r in result if r[0] == predicate2]
    for result_index, i in enumerate(reversed(range(100))):
      self.assertEqual(predicate2_results[result_index],
                       (predicate2, str(i), i * 1000))

  def testResolvePrefixResultsOrderedInDecreasingTimestampOrderPerColumn2(self):
    predicate1 = "metadata:predicate1"
    predicate2 = "metadata:predicate2"
    subject = "aff4:/test_resolve_regex_results_order_in_dec_order_per_column2"

    # Set 100 values for each predicate with timestamps starting in the
    # future and going to the past.
    for i in reversed(range(100)):
      data_store.DB.Set(
          subject, predicate1, str(i), timestamp=i * 1000, replace=False)
      data_store.DB.Set(
          subject, predicate2, str(i), timestamp=i * 1000, replace=False)

    # Check that results will be returned in decreasing timestamp order
    # per column.
    # This test along with a previous one tests that no matter how
    # values were set, they will be sorted by timestamp in the decreasing
    # order when fetched.
    result = list(
        data_store.DB.ResolvePrefix(
            subject,
            "metadata:predicate",
            timestamp=data_store.DB.ALL_TIMESTAMPS,
            limit=1000))

    predicate1_results = [r for r in result if r[0] == predicate1]
    for result_index, i in enumerate(reversed(range(100))):
      self.assertEqual(predicate1_results[result_index],
                       (predicate1, str(i), i * 1000))

    predicate2_results = [r for r in result if r[0] == predicate2]
    for result_index, i in enumerate(reversed(range(100))):
      self.assertEqual(predicate2_results[result_index],
                       (predicate2, str(i), i * 1000))

  def testScanAttribute(self):
    data_store.DB.Set("aff4:/A", "aff4:foo", "A value")
    for i in range(1, 10):
      data_store.DB.Set(
          "aff4:/B/" + str(i),
          "aff4:foo",
          "B " + str(i) + " old value",
          timestamp=2000)
      data_store.DB.Set(
          "aff4:/B/" + str(i),
          "aff4:foo",
          "B " + str(i) + " value",
          timestamp=2000)
      data_store.DB.Set(
          "aff4:/B/" + str(i),
          "aff4:foo",
          "B " + str(i) + " older value",
          timestamp=1900,
          replace=False)

    # Something with a different attribute, which should not be included.
    data_store.DB.Set(
        "aff4:/B/1.1", "aff4:foo2", "B 1.1 other value", timestamp=2000)
    data_store.DB.Set("aff4:/C", "aff4:foo", "C value")

    values = [(r[1], r[2])
              for r in data_store.DB.ScanAttribute("aff4:/B", "aff4:foo")]
    self.assertEqual(values,
                     [(2000, "B " + str(i) + " value") for i in range(1, 10)])

    values = [
        r[2] for r in data_store.DB.ScanAttribute(
            "aff4:/B", "aff4:foo", max_records=2)
    ]
    self.assertEqual(values, ["B " + str(i) + " value" for i in range(1, 3)])

    values = [
        r[2] for r in data_store.DB.ScanAttribute(
            "aff4:/B", "aff4:foo", after_urn="aff4:/B/2")
    ]
    self.assertEqual(values, ["B " + str(i) + " value" for i in range(3, 10)])

    values = [
        r[2] for r in data_store.DB.ScanAttribute(
            "aff4:/B",
            u"aff4:foo",
            after_urn=rdfvalue.RDFURN("aff4:/B/2"),
            max_records=2)
    ]
    self.assertEqual(values, ["B " + str(i) + " value" for i in range(3, 5)])

    values = [r[2] for r in data_store.DB.ScanAttribute("aff4:/", "aff4:foo")]
    self.assertEqual(
        values, ["A value"] + ["B " + str(i) + " value" for i in range(1, 10)
                              ] + ["C value"])

    values = [r[2] for r in data_store.DB.ScanAttribute("", "aff4:foo")]
    self.assertEqual(
        values, ["A value"] + ["B " + str(i) + " value" for i in range(1, 10)
                              ] + ["C value"])

    data_store.DB.Set("aff4:/files/hash/generic/sha1/", "aff4:hash", "h1")
    data_store.DB.Set("aff4:/files/hash/generic/sha1/AAAAA", "aff4:hash", "h2")
    data_store.DB.Set("aff4:/files/hash/generic/sha1/AAAAB", "aff4:hash", "h3")
    data_store.DB.Set("aff4:/files/hash/generic/sha256/", "aff4:hash", "h4")
    data_store.DB.Set("aff4:/files/hash/generic/sha256/AAAAA", "aff4:hash",
                      "h5")
    data_store.DB.Set("aff4:/files/hash/generic/sha256/AAAAB", "aff4:hash",
                      "h6")
    data_store.DB.Set("aff4:/files/hash/generic/sha90000", "aff4:hash", "h7")

    (value, _) = data_store.DB.Resolve("aff4:/files/hash/generic/sha90000",
                                       "aff4:hash")
    self.assertEqual(value, "h7")

    values = [
        r[2]
        for r in data_store.DB.ScanAttribute("aff4:/files/hash", "aff4:hash")
    ]
    self.assertEqual(values, ["h1", "h2", "h3", "h4", "h5", "h6", "h7"])

    values = [
        r[2] for r in data_store.DB.ScanAttribute(
            "aff4:/files/hash", "aff4:hash", relaxed_order=True)
    ]
    self.assertEqual(sorted(values), ["h1", "h2", "h3", "h4", "h5", "h6", "h7"])

  def testScanAttributes(self):
    for i in range(0, 7):
      data_store.DB.Set(
          "aff4:/C/" + str(i),
          "aff4:foo",
          "C foo " + str(i) + " value",
          timestamp=10000)
      data_store.DB.Set(
          "aff4:/C/" + str(i),
          "aff4:foo",
          "C foo " + str(i) + " old value",
          timestamp=9000,
          replace=False)
    for i in range(3, 10):
      data_store.DB.Set(
          "aff4:/C/" + str(i),
          "aff4:bar",
          "C bar " + str(i) + " value",
          timestamp=15000)
      data_store.DB.Set(
          "aff4:/C/" + str(i),
          "aff4:bar",
          "C bar " + str(i) + " old value",
          timestamp=9500,
          replace=False)
    data_store.DB.Set("aff4:/C/5a", "aff4:baz", "C baz value", timestamp=9800)

    results = list(
        data_store.DB.ScanAttributes("aff4:/C", ["aff4:foo", "aff4:bar"]))
    self.assertLen(results, 10)
    self.assertEqual([s for s, _ in results],
                     ["aff4:/C/" + str(i) for i in range(10)])

    self.assertEqual(results[0][1], {"aff4:foo": (10000, "C foo 0 value")})
    self.assertEqual(results[5][1], {
        "aff4:bar": (15000, "C bar 5 value"),
        "aff4:foo": (10000, "C foo 5 value")
    })
    self.assertEqual(results[9][1], {"aff4:bar": (15000, "C bar 9 value")})

    results = list(
        data_store.DB.ScanAttributes(
            "aff4:/C", ["aff4:foo", "aff4:bar"], max_records=5))
    self.assertLen(results, 5)

  def testRDFDatetimeTimestamps(self):

    test_rows = self._MakeTimestampedRows()

    # Make sure all timestamps are set correctly.
    result = dict(data_store.DB.MultiResolvePrefix(test_rows, ["metadata:"]))

    self._CheckResultTimestamps(result, range(1000, 11000, 1000))

    # Now MultiResolve by timestamp.
    timestamp = (rdfvalue.RDFDatetime(3000), rdfvalue.RDFDatetime(8000))
    result = dict(
        data_store.DB.MultiResolvePrefix(
            test_rows, ["metadata:"], timestamp=timestamp))

    # Timestamp selection is inclusive so we should have 3k-8k.
    self._CheckResultTimestamps(result, range(3000, 9000, 1000))

    # Now test timestamped attributes.
    row_name = "aff4:/attribute_test_row"
    attribute_name = "metadata:test_attribute"
    attributes_to_set = {
        attribute_name: [
            (i, rdfvalue.RDFDatetime(i)) for i in range(1000, 11000, 1000)
        ]
    }
    data_store.DB.MultiSet(row_name, attributes_to_set, replace=False)

    # Make sure all timestamps are set correctly.
    result = dict(
        data_store.DB.MultiResolvePrefix(
            [row_name], ["metadata:"], timestamp=data_store.DB.ALL_TIMESTAMPS))

    self._CheckResultTimestamps(result, range(1000, 11000, 1000))

    if self.TEST_DELETION:
      # Delete some of them.
      data_store.DB.DeleteAttributes(
          row_name, [attribute_name],
          start=rdfvalue.RDFDatetime(2000),
          end=rdfvalue.RDFDatetime(4000))
      # Make sure that passing start==end deletes that version.
      data_store.DB.DeleteAttributes(
          row_name, [attribute_name],
          start=rdfvalue.RDFDatetime(6000),
          end=rdfvalue.RDFDatetime(6000))

      result = dict(
          data_store.DB.MultiResolvePrefix(
              [row_name], ["metadata:"],
              timestamp=data_store.DB.ALL_TIMESTAMPS))

      expected_timestamps = [1000, 5000, 7000, 8000, 9000, 10000]
      self._CheckResultTimestamps(result, expected_timestamps)

  @DBSubjectLockTest
  def testDBSubjectLocks(self):
    """Test lock locking."""
    predicate = u"metadata:predicateÎñţér"
    subject = u"aff4:/metadata:rowÎñţér"

    # t1 is holding a lock on this row.
    with data_store.DB.DBSubjectLock(subject, lease_time=100):
      # This means that modification of this row will fail using a different
      # lock.
      self.assertRaises(
          data_store.DBSubjectLockError,
          data_store.DB.DBSubjectLock,
          subject,
          lease_time=100)
      data_store.DB.Set(subject, predicate, "1")

    self.assertEqual(data_store.DB.Resolve(subject, predicate)[0], "1")

    t2 = data_store.DB.DBSubjectLock(subject, lease_time=100)
    self.assertRaises(
        data_store.DBSubjectLockError,
        data_store.DB.DBSubjectLock,
        subject,
        lease_time=100)
    t2.Release()

    t3 = data_store.DB.DBSubjectLock(subject, lease_time=100)
    self.assertTrue(t3.CheckLease())
    t3.Release()

  @DBSubjectLockTest
  def testDBSubjectLockIndependence(self):
    """Check that locks don't influence each other."""
    subject = u"aff4:/metadata:rowÎñţér"
    subject2 = u"aff4:/metadata:rowÎñţér2"

    t1 = data_store.DB.DBSubjectLock(subject, lease_time=100)

    # Check it's locked.
    self.assertRaises(
        data_store.DBSubjectLockError,
        data_store.DB.DBSubjectLock,
        subject,
        lease_time=100)

    # t2 is holding a lock on this row.
    t2 = data_store.DB.DBSubjectLock(subject2, lease_time=100)

    # This means that modification of this row will fail using a different
    # lock.
    self.assertRaises(
        data_store.DBSubjectLockError,
        data_store.DB.DBSubjectLock,
        subject2,
        lease_time=100)
    t2.Release()

    # Subject 1 should still be locked.
    self.assertRaises(
        data_store.DBSubjectLockError,
        data_store.DB.DBSubjectLock,
        subject,
        lease_time=100)

    t1.Release()

  @DBSubjectLockTest
  def testDBSubjectLockLease(self):
    # This needs to be current time or cloud bigtable server will reply with
    # deadline exceeded because the RPC is too old.
    now = int(time.time())
    with test_lib.FakeTime(now):
      with data_store.DB.DBSubjectLock(self.lease_row, lease_time=100) as lock:
        self.assertEqual(lock.CheckLease(), 100)
        self.assertTrue(lock.locked)

        # Set our expiry time to now + 2 * 100
        lock.UpdateLease(2 * 100)
        self.assertEqual(lock.CheckLease(), 2 * 100)

        # Deliberately call release twice, __exit__ will also call
        lock.Release()

  @DBSubjectLockTest
  def testDBSubjectLockLeaseExpiryWithExtension(self):
    now = int(time.time())
    # Cloud Bigtable RPC library doesn't like long, convert to int
    lease_time = 100
    with test_lib.FakeTime(now):
      lock = data_store.DB.DBSubjectLock(self.lease_row, lease_time=lease_time)
      self.assertEqual(lock.expires, int(now + lease_time) * 1e6)
      lock.UpdateLease(2 * lease_time)
      self.assertEqual(lock.expires, int(now + (2 * lease_time)) * 1e6)

    # Lock should still be active
    with test_lib.FakeTime(now + lease_time + 1):
      self.assertRaises(
          data_store.DBSubjectLockError,
          data_store.DB.DBSubjectLock,
          self.lease_row,
          lease_time=lease_time)

    # Now it is expired
    with test_lib.FakeTime(now + (2 * lease_time) + 1):
      data_store.DB.DBSubjectLock(self.lease_row, lease_time=lease_time)

  @DBSubjectLockTest
  def testDBSubjectLockLeaseExpiry(self):
    now = int(time.time())
    lease_time = 100
    with test_lib.FakeTime(now):
      lock = data_store.DB.DBSubjectLock(self.lease_row, lease_time=lease_time)
      self.assertEqual(lock.CheckLease(), lease_time)

      self.assertRaises(
          data_store.DBSubjectLockError,
          data_store.DB.DBSubjectLock,
          self.lease_row,
          lease_time=lease_time)

    # Almost expired
    with test_lib.FakeTime(now + lease_time - 1):
      self.assertRaises(
          data_store.DBSubjectLockError,
          data_store.DB.DBSubjectLock,
          self.lease_row,
          lease_time=lease_time)

    # Expired
    after_expiry = now + lease_time + 1
    with test_lib.FakeTime(after_expiry):
      lock = data_store.DB.DBSubjectLock(self.lease_row, lease_time=lease_time)
      self.assertEqual(lock.CheckLease(), lease_time)
      self.assertEqual(lock.expires, int((after_expiry + lease_time) * 1e6))

  @DBSubjectLockTest
  def testLockRetryWrapperTemporaryFailure(self):
    """Two failed attempts to get the lock, then a succcess."""
    lock = mock.MagicMock()
    with mock.patch.object(time, "sleep", return_value=None) as mock_time:
      with mock.patch.object(
          data_store.DB,
          "DBSubjectLock",
          side_effect=[
              data_store.DBSubjectLockError("1"),
              data_store.DBSubjectLockError("2"), lock
          ]):
        lock = data_store.DB.LockRetryWrapper("aff4:/something")

        # We slept and retried twice
        self.assertEqual(mock_time.call_count, 2)

        lock.Release()

  @DBSubjectLockTest
  def testLockRetryWrapperNoBlock(self):
    subject = "aff4:/noblocklock"
    lock = data_store.DB.DBSubjectLock(subject, lease_time=100)
    with mock.patch.object(time, "sleep", return_value=None) as mock_time:
      with self.assertRaises(data_store.DBSubjectLockError):
        data_store.DB.LockRetryWrapper(subject, lease_time=100, blocking=False)
        self.assertEqual(mock_time.call_count, 0)
    lock.Release()

  @DBSubjectLockTest
  def testLockRetryWrapperCompleteFailure(self):
    subject = "aff4:/subject"
    # We need to sync this delete or it happens after we take the lock and
    # messes up the test.
    data_store.DB.DeleteSubject(subject, sync=True)
    lock = data_store.DB.DBSubjectLock(subject, lease_time=100)

    # By mocking out sleep we can ensure all retries are exhausted.
    with mock.patch.object(time, "sleep", return_value=None):
      with self.assertRaises(data_store.DBSubjectLockError):
        data_store.DB.LockRetryWrapper(
            subject,
            lease_time=100,
            retrywrap_timeout=1,
            retrywrap_max_timeout=3)

    lock.Release()

  def testTimestamps(self):
    """Check that timestamps are reasonable."""
    predicate = "metadata:predicate"
    subject = "aff4:test_timestamps"

    # Extend the range of valid timestamps returned from the table to account
    # for potential clock skew.
    start = int(time.time() - 60) * 1e6
    data_store.DB.Set(subject, predicate, "1")

    stored, ts = data_store.DB.Resolve(subject, predicate)

    # Check the time is reasonable
    end = int(time.time() + 60) * 1e6

    self.assertBetween(ts, start, end)
    self.assertEqual(stored, "1")

  def testSpecificTimestamps(self):
    """Check arbitrary timestamps can be specified."""
    predicate = "metadata:predicate"
    subject = "aff4:/test_specific_timestamps"

    # Check we can specify a timestamp
    data_store.DB.Set(subject, predicate, "2", timestamp=1000)
    stored, ts = data_store.DB.Resolve(subject, predicate)

    # Check the time is reasonable
    self.assertEqual(ts, 1000)
    self.assertEqual(stored, "2")

  def testNewestTimestamps(self):
    """Check that NEWEST_TIMESTAMP works as expected."""
    predicate1 = "metadata:predicate1"
    predicate2 = "metadata:predicate2"

    # Check we can specify a timestamp
    data_store.DB.Set(
        self.test_row, predicate1, "1.1", timestamp=10000, replace=False)
    data_store.DB.Set(
        self.test_row, predicate1, "1.2", timestamp=20000, replace=False)
    data_store.DB.Set(
        self.test_row, predicate2, "2.1", timestamp=11000, replace=False)
    data_store.DB.Set(
        self.test_row, predicate2, "2.2", timestamp=22000, replace=False)

    result = data_store.DB.ResolvePrefix(
        self.test_row, predicate1, timestamp=data_store.DB.ALL_TIMESTAMPS)

    # Should return 2 results. Newest should be first.
    values = [x[1] for x in result]
    self.assertLen(values, 2)
    self.assertListEqual(values, ["1.2", "1.1"])
    times = [x[2] for x in result]
    self.assertListEqual(times, [20000, 10000])

    result = data_store.DB.ResolvePrefix(
        self.test_row, predicate1, timestamp=data_store.DB.NEWEST_TIMESTAMP)

    # Should return 1 result - the most recent.
    self.assertLen(result, 1)
    self.assertEqual(result[0][1], "1.2")
    self.assertEqual(result[0][2], 20000)

    result = list(
        data_store.DB.ResolvePrefix(
            self.test_row, "metadata:", timestamp=data_store.DB.ALL_TIMESTAMPS))

    self.assertLen(result, 4)
    self.assertListEqual([r for r in result if r[0] == "metadata:predicate1"],
                         [(u"metadata:predicate1", "1.2", 20000),
                          (u"metadata:predicate1", "1.1", 10000)])
    self.assertListEqual([r for r in result if r[0] == "metadata:predicate2"],
                         [(u"metadata:predicate2", "2.2", 22000),
                          (u"metadata:predicate2", "2.1", 11000)])

    result = list(
        data_store.DB.ResolvePrefix(
            self.test_row,
            "metadata:",
            timestamp=data_store.DB.NEWEST_TIMESTAMP))

    # Should only return the latest version.
    self.assertCountEqual(result, [(u"metadata:predicate1", "1.2", 20000),
                                   (u"metadata:predicate2", "2.2", 22000)])

  @DeletionTest
  def testTimestampEdgeCases(self):
    row = "aff4:/row"
    attribute = "metadata:attribute"
    for i in range(4):
      # First TS is 0!
      timestamp = rdfvalue.RDFDatetime(1000 * i)
      data_store.DB.MultiSet(
          row, {attribute: [i]}, timestamp=timestamp, replace=False)

    rows = data_store.DB.ResolvePrefix(
        row, "metadata:", timestamp=data_store.DB.ALL_TIMESTAMPS)

    self.assertLen(rows, 4)
    self.assertCountEqual([r[2] for r in rows], [0, 1000, 2000, 3000])

    data_store.DB.DeleteAttributes(row, [attribute], start=0, end=0)
    rows = data_store.DB.ResolvePrefix(
        row, "metadata:", timestamp=data_store.DB.ALL_TIMESTAMPS)
    self.assertLen(rows, 3)
    self.assertCountEqual([r[2] for r in rows], [1000, 2000, 3000])

  def testResolvePrefix(self):
    predicate = "metadata:predicate"
    subject = "aff4:/test_resolve_regex_prefix"

    # Check we can specify a timestamp
    data_store.DB.Set(subject, predicate, "3")
    results = [x for x in data_store.DB.ResolvePrefix(subject, "metadata:")]

    self.assertLen(results, 1)
    # Value
    self.assertEqual(results[0][1], "3")
    # Predicate
    self.assertEqual(results[0][0], predicate)

  def testResolveMulti(self):
    """Test regex Multi Resolving works."""
    subject = "aff4:/resolve_multi"

    predicates = []
    predicate_values = []
    for i in range(0, 100):
      predicate = "metadata:predicate" + str(i)
      predicates.append(predicate)
      predicate_values.append("Cell " + predicate)
      data_store.DB.Set(subject, predicate, "Cell " + predicate, timestamp=1000)

    results = [x for x in data_store.DB.ResolveMulti(subject, predicates)]

    self.assertLen(results, 100)
    self.assertCountEqual(predicates, [x[0] for x in results])
    self.assertCountEqual(predicate_values, [x[1] for x in results])

    # Now try to query for non existent predicates.
    predicates = predicates[:10]
    predicate_values = predicate_values[:10]
    for i in range(10):
      predicates.append("metadata:not_existing" + str(i))

    results = [x for x in data_store.DB.ResolveMulti(subject, predicates)]

    self.assertLen(results, 10)
    self.assertCountEqual(predicates[:10], [x[0] for x in results])
    self.assertCountEqual(predicate_values, [x[1] for x in results])

  def testBlobs(self):
    data = b"randomdata" * 50

    identifier = data_store.BLOBS.WriteBlobWithUnknownHash(data)

    self.assertTrue(data_store.BLOBS.CheckBlobExists(identifier))
    self.assertEqual(data_store.BLOBS.ReadBlob(identifier), data)

    empty_digest = rdf_objects.BlobID.FromBlobData(b"")

    self.assertFalse(data_store.BLOBS.CheckBlobExists(empty_digest))
    self.assertIsNone(data_store.BLOBS.ReadBlob(empty_digest))

  def testAFF4BlobImage(self):
    # 500k
    data = b"randomdata" * 50 * 1024

    identifier = data_store.BLOBS.WriteBlobWithUnknownHash(data)

    # Now create the image containing the blob.
    with aff4.FACTORY.Create("aff4:/C.1235/image", aff4_grr.VFSBlobImage) as fd:
      fd.SetChunksize(512 * 1024)
      fd.Set(fd.Schema.STAT())

      fd.AddBlob(identifier, len(data))

    # Check if we can read back the data.
    with aff4.FACTORY.Open("aff4:/C.1235/image") as fd:
      self.assertEqual(
          fd.read(len(data)), data,
          "Data read back from aff4image doesn't match.")

  def testDotsInDirectory(self):
    """Check that dots work in rows/indexes."""

    for directory in [
        "aff4:/C.1240/dir", "aff4:/C.1240/dir/a.b", "aff4:/C.1240/dir/a.b/c",
        "aff4:/C.1240/dir/b"
    ]:
      aff4.FACTORY.Create(directory, standard.VFSDirectory).Close()

    # This must not raise.
    aff4.FACTORY.Open("aff4:/C.1240/dir/a.b/c", standard.VFSDirectory)

    directory = aff4.FACTORY.Open("aff4:/C.1240/dir")
    dirs = list(directory.OpenChildren())
    self.assertLen(dirs, 2)
    self.assertCountEqual([d.urn.Basename() for d in dirs], ["b", "a.b"])
    urns = list(directory.ListChildren())
    self.assertLen(urns, 2)
    self.assertCountEqual([u.Basename() for u in urns], ["b", "a.b"])

  OPEN_WITH_LOCK_NUM_THREADS = 5
  OPEN_WITH_LOCK_TRIES_PER_THREAD = 3
  OPEN_WITH_LOCK_SYNC_LOCK_SLEEP = 0.2

  @pytest.mark.large
  @DBSubjectLockTest
  def testAFF4OpenWithLock(self):
    self.opened = False
    self.client_urn = "aff4:/C.0000000000000001"

    client = aff4.FACTORY.Create(
        self.client_urn, aff4_grr.VFSGRRClient, mode="w")
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Set(
        client.Schema.LEASED_UNTIL(
            rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)))
    client.Close()

    self.open_failures = 0
    self.close_failures = 0
    self.results = []

    def ParallelThread():
      for _ in range(self.OPEN_WITH_LOCK_TRIES_PER_THREAD):
        t = time.time()
        try:
          with aff4.FACTORY.OpenWithLock(
              self.client_urn,
              blocking=True,
              blocking_sleep_interval=self.OPEN_WITH_LOCK_SYNC_LOCK_SLEEP,
              blocking_lock_timeout=10):

            # We fail if another thread has the object already opened here.
            if self.opened:
              self.open_failures += 1
              self.fail("Double open!")

            self.opened = True
            logging.info("Thread %s holding lock for 0.2 seconds.",
                         _thread.get_ident())
            time.sleep(0.2)

            # We fail if someone has closed the object while we are holding it
            # opened.
            if not self.opened:
              self.close_failures += 1
              self.fail("Double close!")

            self.results.append(_thread.get_ident())

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
    self.assertLen(self.results, self.OPEN_WITH_LOCK_NUM_THREADS)

  def _ListedMultiResolvePrefix(self, *args, **kwargs):
    return list(data_store.DB.MultiResolvePrefix(*args, **kwargs))

  def _ListedResolveMulti(self, *args, **kwargs):
    return list(data_store.DB.ResolveMulti(*args, **kwargs))

  def _ListedResolvePrefix(self, *args, **kwargs):
    return list(data_store.DB.ResolvePrefix(*args, **kwargs))

  def _FlushedDeleteSubject(self, *args, **kwargs):
    # DeleteSubject is not guaranteed to be synchronous. Make sure that
    # we flush data store when testing it.
    data_store.DB.DeleteSubject(*args, **kwargs)
    data_store.DB.Flush()

  def testLimits(self):
    # Create 10 rows with 10 attributes each.
    subjects = ["aff4:limittest_%d" % i for i in range(10)]
    attributes = ["metadata:limittest_%d" % i for i in range(10)]

    value_idx = 0
    for subject in subjects:
      for attribute in attributes:
        value = "value_%d" % value_idx
        value_idx += 1
        data_store.DB.Set(subject, attribute, value)

    # ResolvePrefix.
    for limit in [1, 2, 5, 10, 100]:
      results = data_store.DB.ResolvePrefix(
          subjects[0], "metadata:", limit=limit)
      self.assertLen(results, min(limit, 10))

    # MultiResolvePrefix.
    for limit in [1, 2, 5, 9, 10, 11, 25, 100, 120]:
      results = dict(
          data_store.DB.MultiResolvePrefix(subjects, "metadata:", limit=limit))
      all_results = []
      for subect_res in itervalues(results):
        all_results.extend(subect_res)

      self.assertLen(all_results, min(limit, 100))

    for limit in [1, 2, 5, 9, 10, 11, 25]:
      results = dict(
          data_store.DB.MultiResolvePrefix(
              subjects, "metadata:limittest_7", limit=limit))
      all_results = []
      for subect_res in itervalues(results):
        all_results.extend(subect_res)

      self.assertLen(all_results, min(limit, 10))

    # ResolveMulti.
    for limit in [1, 2, 5, 9, 10, 11, 25]:
      results = list(
          data_store.DB.ResolveMulti(subjects[2], attributes, limit=limit))

      self.assertLen(results, min(limit, 10))

  def testApi(self):
    # pyformat: disable
    api = [
        "CheckRequestsForCompletion",
        "CollectionReadIndex",
        "CollectionReadStoredTypes",
        "CollectionScanItems",
        "CreateNotifications",
        "DBSubjectLock",
        "DeleteAttributes",
        "DeleteNotifications",
        "DeleteRequest",
        "DeleteRequests",
        "DeleteSubject",
        "DeleteSubjects",
        "DeleteWellKnownFlowResponses",
        "DestroyFlowStates",
        "FetchResponsesForWellKnownFlow",
        "GetMutationPool",
        "GetNotifications",
        "IndexAddKeywordsForName",
        "IndexReadPostingLists",
        "IndexRemoveKeywordsForName",
        "MultiDeleteAttributes",
        "MultiDestroyFlowStates",
        "MultiResolvePrefix",
        "MultiSet",
        "ReadCompletedRequests",
        "ReadRequestsAndResponses",
        "ReadResponses",
        "ReadResponsesForRequestId",
        "Resolve",
        "ResolveMulti",
        "ResolvePrefix",
        "ScanAttribute",
        "ScanAttributes",
        "Set",
        "StoreRequestsAndResponses",
    ]

    pool_api = [
        "CollectionAddIndex",
        "CollectionAddItem",
        "CollectionAddStoredTypeIndex",
        "CreateNotifications",
        "DeleteAttributes",
        "DeleteSubject",
        "DeleteSubjects",
        "Flush",
        "MultiSet",
        "QueueAddItem",
        "QueueClaimRecords",
        "QueueDeleteRecords",
        "QueueRefreshClaims",
        "QueueReleaseRecords",
        "Set",
        "Size",
    ]
    # pyformat: enable

    implementation = data_store.DB
    reference = data_store.DataStore

    for f in api:
      implementation_spec = inspect.getargspec(getattr(implementation, f))
      reference_spec = inspect.getargspec(getattr(reference, f))
      self.assertEqual(
          implementation_spec, reference_spec,
          "Signatures for function %s not matching: \n%s !=\n%s" %
          (f, implementation_spec, reference_spec))

    # Check the MutationPool.
    implementation = data_store.DB.GetMutationPool()
    reference = data_store.MutationPool
    for f in pool_api:
      implementation_spec = inspect.getargspec(getattr(implementation, f))
      reference_spec = inspect.getargspec(getattr(reference, f))
      self.assertEqual(
          implementation_spec, reference_spec,
          "Signatures for function %s not matching: \n%s !=\n%s" %
          (f, implementation_spec, reference_spec))

  @DeletionTest
  def testPoolDeleteSubjects(self):

    predicate = "metadata:predicate"
    data_store.DB.Set(self.test_row, predicate, "hello")
    # Check it's there.
    stored, _ = data_store.DB.Resolve(self.test_row, predicate)
    self.assertEqual(stored, "hello")

    pool = data_store.DB.GetMutationPool()
    pool.DeleteAttributes(self.test_row, [predicate])

    # Check it's still there.
    stored, _ = data_store.DB.Resolve(self.test_row, predicate)
    self.assertEqual(stored, "hello")

    pool.Flush()

    # Now it should be gone.
    stored, _ = data_store.DB.Resolve(self.test_row, predicate)
    self.assertIsNone(stored)

  def testPoolMultiSet(self):
    pool = data_store.DB.GetMutationPool()

    unicode_string = u"this is a uñîcödé string"
    pool.MultiSet(
        self.test_row, {
            "aff4:size": [1],
            "aff4:stored": [unicode_string],
            "aff4:unknown_attribute": ["hello"]
        })

    # Nothing is written before Flush() is called.
    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertIsNone(stored)

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:stored")
    self.assertIsNone(stored)

    # Flush.
    pool.Flush()

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:size")
    self.assertEqual(stored, 1)

    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:stored")
    self.assertEqual(stored, unicode_string)

    # Make sure that unknown attributes are stored as bytes.
    stored, _ = data_store.DB.Resolve(self.test_row, "aff4:unknown_attribute")
    self.assertEqual(stored, "hello")
    self.assertEqual(type(stored), str)

  @DeletionTest
  def testPoolDeleteAttributes(self):
    predicate = "metadata:predicate"
    pool = data_store.DB.GetMutationPool()

    data_store.DB.Set(self.test_row, predicate, "hello")

    # Check it's there.
    stored, _ = data_store.DB.Resolve(self.test_row, predicate)
    self.assertEqual(stored, "hello")

    pool.DeleteAttributes(self.test_row, [predicate])

    # Check it's still there.
    stored, _ = data_store.DB.Resolve(self.test_row, predicate)
    self.assertEqual(stored, "hello")

    pool.Flush()

    stored, _ = data_store.DB.Resolve(self.test_row, predicate)
    self.assertIsNone(stored)

  def testQueueManager(self):
    session_id = rdfvalue.SessionID(flow_name="test")
    client_id = test_lib.TEST_CLIENT_ID

    request = rdf_flow_runner.RequestState(
        id=1,
        client_id=client_id,
        next_state="TestState",
        session_id=session_id)

    with queue_manager.QueueManager() as manager:
      manager.QueueRequest(request)

    # We only have one unanswered request on the queue.
    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertLen(all_requests, 1)
    self.assertEqual(all_requests[0], (request, []))

    # FetchCompletedRequests should return nothing now.
    self.assertEqual(list(manager.FetchCompletedRequests(session_id)), [])

    # Now queue more requests and responses:
    with queue_manager.QueueManager() as manager:
      # Start with request 2 - leave request 1 un-responded to.
      for request_id in range(2, 5):
        request = rdf_flow_runner.RequestState(
            id=request_id,
            client_id=client_id,
            next_state="TestState",
            session_id=session_id)

        manager.QueueRequest(request)

        response_id = None
        for response_id in range(1, 10):
          # Normal message.
          manager.QueueResponse(
              rdf_flows.GrrMessage(
                  session_id=session_id,
                  request_id=request_id,
                  response_id=response_id))

        # And a status message.
        manager.QueueResponse(
            rdf_flows.GrrMessage(
                session_id=session_id,
                request_id=request_id,
                response_id=response_id + 1,
                type=rdf_flows.GrrMessage.Type.STATUS))

    completed_requests = list(manager.FetchCompletedRequests(session_id))
    self.assertLen(completed_requests, 3)

    # First completed message is request_id = 2 with 10 responses.
    self.assertEqual(completed_requests[0][0].id, 2)

    # Last message is the status message.
    self.assertEqual(completed_requests[0][-1].type,
                     rdf_flows.GrrMessage.Type.STATUS)
    self.assertEqual(completed_requests[0][-1].response_id, 10)

    # Now fetch all the completed responses. Set the limit so we only fetch some
    # of the responses.
    completed_response = list(manager.FetchCompletedResponses(session_id))
    self.assertLen(completed_response, 3)
    for i, (request, responses) in enumerate(completed_response, 2):
      self.assertEqual(request.id, i)
      self.assertLen(responses, 10)

    # Now check if the limit is enforced. The limit refers to the total number
    # of responses to return. We ask for maximum 15 responses, so we should get
    # a single request with 10 responses (since 2 requests will exceed the
    # limit).
    more_data = False
    i = 0
    try:
      partial_response = manager.FetchCompletedResponses(session_id, limit=15)
      for i, (request, responses) in enumerate(partial_response, 2):
        self.assertEqual(request.id, i)
        self.assertLen(responses, 10)
    except queue_manager.MoreDataException:
      more_data = True

    # Returns the first request that is completed.
    self.assertEqual(i, 3)

    # Make sure the manager told us that more data is available.
    self.assertTrue(more_data)

    with queue_manager.QueueManager() as manager:
      manager.QueueNotification(
          rdf_flows.GrrNotification(session_id=session_id, timestamp=100))
    stored_notifications = manager.GetNotificationsForAllShards(
        session_id.Queue())
    self.assertLen(stored_notifications, 1)


@pytest.mark.benchmark
class DataStoreCSVBenchmarks(benchmark_test_lib.MicroBenchmarks):
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
    super(DataStoreCSVBenchmarks, self).setUp(
        ["DB Size (KB)", "Queries", "Subjects", "Predicates", "Values"],
        ["<20", "<10", "<10", "<10", "<10"])
    self.start_time = time.time()
    self.last_time = self.start_time

  def tearDown(self):
    self.Register(force=True)
    super(DataStoreCSVBenchmarks, self).tearDown()
    self.WriteCSV()

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
                     data_store.DB.Size() // 1024, queries_diff, self.subjects,
                     self.predicates, self.values)

  def WriteCSV(self, remove=False):
    """Write results to a CSV file."""
    writer = csv.Writer(delimiter=u" ")
    writer.WriteRow([
        u"Benchmark",
        u"Time",
        u"DBSize",
        u"Queries",
        u"Subjects",
        u"Predicates",
        u"Values",
    ])
    for row in self.scratchpad[2:]:
      writer.WriteRow([row[0], row[1], row[3], row[4], row[5], row[6], row[7]])

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fp:
      fp.write(writer.Content().encode("utf-8"))
      logging.info("CSV File is in %s", fp.name)
      if remove:
        os.unlink(fp.name)

  def _RandomlyReadSubject(self, subject, predicates):
    """Read certain parts of a given subject."""
    for j, timestamps in iteritems(predicates):
      which = self.rand.randint(0, 2)
      if which == 0:
        # Read all timestamps.
        data_store.DB.ResolveMulti(
            subject, [self.predicate_template % j],
            timestamp=data_store.DB.ALL_TIMESTAMPS)
      elif which == 1:
        # Read a specific timestamp.
        if timestamps:
          ts = self.rand.choice(timestamps)
          data_store.DB.ResolveMulti(
              subject, [self.predicate_template % j], timestamp=(ts, ts))
      elif which == 2:
        # Read latest.
        data_store.DB.Resolve(subject, self.predicate_template % j)
      self.Register()
    which = self.rand.randint(0, 1)
    if which == 0:
      # Find all attributes.
      data_store.DB.ResolvePrefix(
          subject, "task:flow", timestamp=data_store.DB.NEWEST_TIMESTAMP)
    elif which == 1:
      # Find all attributes with a prefix reducable regex.
      data_store.DB.ResolvePrefix(
          subject, "task:", timestamp=data_store.DB.NEWEST_TIMESTAMP)
    self.Register()

  def _ReadRandom(self, subjects, fraction, change_test=True):
    """Randomly read the database."""
    if change_test:
      self.test_name = "read random %d%%" % fraction
    for _ in range(0, int(len(subjects) * fraction / 100.0)):
      i = self.rand.choice(list(iterkeys(subjects)))
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
        for j, timestamp_info in iteritems(predicates):
          number_timestamps = len(timestamp_info)
          if which == 0 and len(timestamp_info):
            # Update one timestamp'ed value.
            data_store.DB.Set(
                subject,
                self.predicate_template % j,
                new_value,
                timestamp=timestamp_info[-1])
            self.Register()
          elif which == 1:
            # Add another timestamp.
            timestamp_info.append(100 * number_timestamps + 1)
            data_store.DB.Set(
                subject,
                self.predicate_template % j,
                new_value,
                replace=False,
                timestamp=timestamp_info[-1])
            self.values += 1
            self.Register()
      elif which == 2:
        # Add an extra predicate.
        j = len(predicates)
        number_timestamps = self.rand.randrange(1, 3)
        ts = [100 * (ts + 1) for ts in range(number_timestamps)]
        predicates[j] = ts
        self.values += number_timestamps
        self.predicates += 1
        values = [(new_value, t) for t in ts]
        data_store.DB.MultiSet(
            subject, {self.predicate_template % j: values},
            replace=False,
            timestamp=100)
        self.Register()
    data_store.DB.Flush()

  def _DeleteRandom(self, subjects, fraction, change_test=True):
    """Delete predicates/subjects/values at random."""
    if change_test:
      self.test_name = "delete %d%%" % fraction
    subjects_to_delete = []
    for i, info in iteritems(subjects):
      subject = info["name"]
      predicates = info["attrs"]
      number_predicates = len(predicates)
      do_it = (self.rand.randint(0, 100) <= fraction)
      which = self.rand.randint(0, 2)
      count_values = 0
      predicates_to_delete = []
      for j, timestamp_info in iteritems(predicates):
        number_timestamps = len(timestamp_info)
        count_values += number_timestamps
        if do_it:
          if which == 0:
            # Delete one timestamp'ed value.
            if timestamp_info:
              ts = timestamp_info[0]
              data_store.DB.DeleteAttributes(
                  subject, [self.predicate_template % j], start=ts, end=ts)
              self.values -= 1
              timestamp_info.pop(0)
              self.Register()
            else:
              which = 1
          if which == 1:
            # Delete the attribute itself.
            data_store.DB.DeleteAttributes(subject,
                                           [self.predicate_template % j])
            self.values -= number_timestamps
            self.predicates -= 1
            predicates_to_delete.append(j)
            self.Register()
      if do_it and which == 1:
        for j in predicates_to_delete:
          del predicates[j]
      if do_it and which == 2:
        # Delete subject.
        data_store.DB.DeleteSubject(subject)
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
    how_many = int(len(subjects) * fraction / 100)
    new_value = os.urandom(100)
    new_subject = max(iteritems(subjects), key=operator.itemgetter(0))[0] + 1
    # Generate client names.
    clients = [self._GenerateRandomClient() for _ in range(nclients)]
    for i in range(new_subject, new_subject + how_many):
      client = clients[self.rand.randint(0, nclients - 1)]
      self._AddNewSubject(client, subjects, i, new_value)
    data_store.DB.Flush()

  def _GenerateRandomSubject(self):
    n = self.rand.randint(1, 5)
    seps = [
        self._GenerateRandomString(self.rand.randint(5, 10)) for _ in range(n)
    ]
    return "/".join(seps)

  def _AddNewSubject(self, client, subjects, i, value, max_attributes=3):
    """Add a new subject to the database."""
    number_predicates = self.rand.randrange(1, max_attributes)
    self.subjects += 1
    predicates = dict.fromkeys(range(number_predicates))
    self.predicates += number_predicates
    subject = str(client.Add(self._GenerateRandomSubject()))
    for j in range(number_predicates):
      number_timestamps = self.rand.randrange(1, 3)
      self.values += number_timestamps
      ts = [100 * (ts + 1) for ts in range(number_timestamps)]
      predicates[j] = ts
      values = [(value, t) for t in ts]
      data_store.DB.MultiSet(
          subject, {self.predicate_template % j: values},
          timestamp=100,
          replace=False,
          sync=False)
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
      i = self.rand.choice(list(iterkeys(subjects)))
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      how_many = self.rand.randint(self.BIG_NUM_ATTRIBUTES,
                                   self.BIG_NUM_ATTRIBUTES + 1000)
      self.predicates += how_many
      new_predicate = max(
          iteritems(predicates), key=operator.itemgetter(0))[0] + 1
      for j in range(new_predicate, new_predicate + how_many):
        number_timestamps = self.rand.randrange(1, 3)
        ts = [100 * (ts + 1) for ts in range(number_timestamps)]
        self.values += number_timestamps
        values = [(new_value, t) for t in ts]
        predicates[j] = ts
        data_store.DB.MultiSet(
            subject, {self.predicate_template % j: values},
            replace=False,
            timestamp=100,
            sync=False)
        self.Register()
    data_store.DB.Flush()

  def _RemoveManyAttributes(self, subjects, fraction):
    """Delete all predicates (except 1) from subjects with many predicates."""
    self.test_name = "del +attrs %d%%" % fraction
    often = 100 // fraction
    count = 0
    for i in subjects:
      subject = subjects[i]["name"]
      predicates = subjects[i]["attrs"]
      number_predicates = len(predicates)
      if number_predicates >= self.BIG_NUM_ATTRIBUTES:
        count += 1
        if count == often:
          count = 0
          predicates_to_delete = list(iterkeys(predicates))[1:]
          values_deleted = sum(len(predicates[x]) for x in predicates_to_delete)
          self.values -= values_deleted
          self.predicates -= len(predicates_to_delete)
          for j in predicates_to_delete:
            del predicates[j]
            data_store.DB.DeleteAttributes(
                subject, [self.predicate_template % j], sync=False)
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
      data_store.DB.DeleteSubject(subject)
      self.predicates -= number_predicates
      self.values -= count_values
      self.subjects -= 1
      self.Register()
    subjects = {}
    data_store.DB.Flush()

  def _DoMix(self, subjects):
    """Do a mix of database operations."""
    self.test_name = "mix"
    for _ in range(0, len(subjects) // 2000):
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
    return rdf_client.ClientURN("C.%016d" % self.rand.randint(0, (10**16) - 1))

  def _FillDatabase(self, nsubjects, nclients, max_attributes=3):
    """Fill the database with a certain number of subjects and clients."""
    self.rand = random.Random(0)
    self.test_name = "fill"
    self.AddResult(self.test_name, 0, self.steps, data_store.DB.Size(), 0, 0, 0,
                   0)
    subjects = dict.fromkeys(range(nsubjects))
    value = os.urandom(100)
    clients = [self._GenerateRandomClient() for _ in range(nclients)]
    for i in subjects:
      client = self.rand.choice(clients)
      self._AddNewSubject(client, subjects, i, value, max_attributes)
    data_store.DB.Flush()
    return subjects

  def _GenerateRandomString(self, chars):
    return "".join(
        [self.rand.choice(string.ascii_letters) for _ in range(chars)])

  def _AddBlobs(self, howmany, size):
    """Adds 'howmany' blobs with size 'size' kbs."""
    self.test_name = "add blobs %dx%dk" % (howmany, size)
    count = 0
    often = howmany // 10

    for count in range(howmany):
      data = self._GenerateRandomString(1024 * size)
      data_store.WriteBlobWithUnknownHash(data)

      if count % often == 0:
        # Because adding blobs, takes too long we force the output of
        # new results.
        self.Register(force=True)

    self.Register(force=True)
    data_store.DB.Flush()

  @pytest.mark.benchmark
  def testManySubjectsFewAttrs(self):
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

  @pytest.mark.benchmark
  def testManySubjectsFewWithManyAttrs(self):
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

  @pytest.mark.benchmark
  def testFewSubjectsManyAttrs(self):
    """Database with a few subjects with many attributes."""
    subjects = self._FillDatabase(100, 5)
    self._UpdateRandom(subjects, 100)
    self._AddManyAttributes(subjects, 50)
    self._ReadRandom(subjects, 30)
    self._RemoveManyAttributes(subjects, 50)
    self._ReadRandom(subjects, 50)
    self._Wipeout(subjects)

  @pytest.mark.benchmark
  def testBlobs(self):
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

  @pytest.mark.benchmark
  def testManySubjectsManyAttrs(self):
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


@pytest.mark.benchmark
class DataStoreBenchmarks(benchmark_test_lib.MicroBenchmarks):
  """Datastore micro benchmarks.

  These tests should be run with --labels=benchmark
  """
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
    for i in range(n):
      res.append(
          rdf_client_fs.StatEntry(
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
              pathspec=rdf_paths.PathSpec(
                  path="/dir/dir/file%d" % i, pathtype=0)))
    return res

  def StartFlow(self, client_id):
    flow_id = flow.StartAFF4Flow(
        client_id=client_id,
        flow_name=filesystem.ListDirectory.__name__,
        queue=self.queue,
        pathspec=rdf_paths.PathSpec(
            path="/",
            pathtype="OS",
        ))
    self.flow_ids.append(flow_id)

    messages = []
    for d in range(self.nr_dirs):
      messages += self.GenerateFiles(client_id, self.files_per_dir,
                                     "dir/dir%d" % d)

    messages.append(rdf_flows.GrrStatus())

    with queue_manager.QueueManager() as flow_manager:
      for i, payload in enumerate(messages):
        msg = rdf_flows.GrrMessage(
            session_id=flow_id,
            request_id=1,
            response_id=1 + i,
            auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
            payload=payload)
        if isinstance(payload, rdf_flows.GrrStatus):
          msg.type = 1
        flow_manager.QueueResponse(msg)

  nr_clients = 4
  nr_dirs = 4
  files_per_dir = 500

  def _GenerateRandomString(self, chars):
    return "".join(
        [self.rand.choice(string.ascii_letters) for _ in range(chars)])

  # Constants to control the size of testCollections. These numbers run in a
  # reasonable amount of time for a unit test [O(20s)] on most data stores.
  RECORDS = 5000
  RECORD_SIZE = 1000
  READ_COUNT = 50
  BIG_READ_SIZE = 25

  # The sequential collection index is only computed for records 5m old, so we
  # write records this far in the past in order to force index creation.
  INDEX_DELAY = rdfvalue.Duration("10m")

  @pytest.mark.benchmark
  def testCollections(self):

    self.rand = random.Random(42)

    #
    # Populate and exercise an indexed sequential collection.
    #

    urn = rdfvalue.RDFURN("aff4:/test_seq_collection")
    indexed_collection = StringSequentialCollection(urn)

    start_time = time.time()
    with data_store.DB.GetMutationPool() as pool:
      for _ in range(self.RECORDS):
        indexed_collection.Add(
            rdfvalue.RDFString(self._GenerateRandomString(self.RECORD_SIZE)),
            timestamp=rdfvalue.RDFDatetime.Now() - self.INDEX_DELAY,
            mutation_pool=pool)
    elapsed_time = time.time() - start_time
    self.AddResult("Seq. Coll. Add (size %d)" % self.RECORD_SIZE, elapsed_time,
                   self.RECORDS)

    start_time = time.time()
    self.assertLen(indexed_collection, self.RECORDS)
    elapsed_time = time.time() - start_time
    self.AddResult("Seq. Coll. Read to end", elapsed_time, 1)

    start_time = time.time()
    for _ in range(self.READ_COUNT):
      for _ in indexed_collection.GenerateItems(
          offset=self.rand.randint(0, self.RECORDS - 1)):
        break
    elapsed_time = time.time() - start_time
    self.AddResult("Seq. Coll. random 1 record reads", elapsed_time,
                   self.READ_COUNT)

    start_time = time.time()
    for _ in range(self.READ_COUNT):
      count = 0
      for _ in indexed_collection.GenerateItems(
          offset=self.rand.randint(0, self.RECORDS - self.BIG_READ_SIZE)):
        count += 1
        if count >= self.BIG_READ_SIZE:
          break
    elapsed_time = time.time() - start_time
    self.AddResult("Seq. Coll. random %d record reads" % self.BIG_READ_SIZE,
                   elapsed_time, self.READ_COUNT)

    start_time = time.time()
    for _ in indexed_collection.GenerateItems():
      pass
    elapsed_time = time.time() - start_time
    self.AddResult("Seq. Coll. full sequential read", elapsed_time, 1)

  @pytest.mark.benchmark
  def testSimulateFlows(self):
    self.flow_ids = []
    self.units = "s"

    client_ids = ["C.%016X" % j for j in range(1, self.nr_clients + 1)]

    start_time = time.time()

    for client_id in client_ids:
      self.tp.AddTask(self.StartFlow, (client_id,))
    self.tp.Join()

    notifications = [
        rdf_flows.GrrNotification(session_id=f) for f in self.flow_ids
    ]
    with queue_manager.QueueManager() as manager:
      manager.MultiNotifyQueue(notifications)

    time_used = time.time() - start_time

    self.AddResult(
        "Generate Messages (%d clients, %d files)" %
        (self.nr_clients, self.nr_dirs * self.files_per_dir), time_used, 1)

    my_worker = worker_lib.GRRWorker(queues=[self.queue], token=self.token)

    start_time = time.time()

    while my_worker.RunOnce():
      pass
    my_worker.thread_pool.Join()

    time_used = time.time() - start_time

    self.AddResult("Process Messages", time_used, 1)

  @pytest.mark.benchmark
  def testMicroBenchmarks(self):

    # Tests run in arbitrary order but for the benchmarks, the order makes a
    # difference so we call them all from one test here.
    self.n = 1000
    self.small_n = self.n // 100
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
    for i in range(self.n):
      data_store.DB.Set(subject_template % i, "task:flow", value)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set rows", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.n):
      data_store.DB.Set("aff4:/somerow", predicate_template % i, value)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set attributes", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.n):
      data_store.DB.Set("aff4:/somerow", "task:someflow", value, replace=False)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set versions", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.small_n):
      data_store.DB.Set(
          "aff4:/largerow%d" % i, "task:largeflow", large_value, replace=False)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Set large values", (end_time - start_time) / self.small_n,
                   self.small_n)

  def BenchmarkReading(self):

    subject_template = "aff4:/row%d"
    predicate_template = "task:flow%d"

    start_time = time.time()
    for i in range(self.n):
      data_store.DB.Resolve(subject_template % i, "task:flow")
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Get rows", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.n):
      data_store.DB.Resolve("aff4:/somerow", predicate_template % i)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Get attributes", (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.small_n):
      data_store.DB.ResolvePrefix(
          "aff4:/somerow",
          "task:someflow",
          timestamp=data_store.DB.ALL_TIMESTAMPS)
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Get all versions", (end_time - start_time) / self.small_n,
                   self.small_n)

    start_time = time.time()
    for i in range(self.small_n):
      res = data_store.DB.ResolvePrefix(
          "aff4:/largerow%d" % i,
          "task:largeflow",
          timestamp=data_store.DB.ALL_TIMESTAMPS)
      self.assertLen(res, 1)
      self.assertLen(res[0][1], 10 * 1024 * 1024)

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
    for i in range(self.n):
      self.tp.AddTask(data_store.DB.Set,
                      (subject_template % i, "task:threadedflow", value, None))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set rows", (end_time - start_time) / self.n,
                   self.n)

    start_time = time.time()
    for i in range(self.n):
      self.tp.AddTask(
          data_store.DB.Set,
          ("aff4:/somerowthreaded", predicate_template % i, value, None))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set attributes",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.n):
      self.tp.AddTask(data_store.DB.Set,
                      ("aff4:/somerowthreaded", "task:someflowthreaded", value,
                       None, False))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set versions",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.small_n):
      self.tp.AddTask(data_store.DB.Set,
                      ("aff4:/threadedlargerow%d" % i, "task:largeflowthreaded",
                       large_value, None, False))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Set large values",
                   (end_time - start_time) / self.small_n, self.small_n)

  def ResolvePrefixAndCheck(self, subject, predicate, expected_items=1000):
    res = data_store.DB.ResolvePrefix(
        subject, predicate, timestamp=data_store.DB.ALL_TIMESTAMPS)
    self.assertLen(list(res), expected_items)

  def BenchmarkReadingThreaded(self):

    subject_template = "aff4:/threadedrow%d"
    predicate_template = "task:threadedflow%d"

    start_time = time.time()
    for i in range(self.n):
      self.tp.AddTask(data_store.DB.Resolve,
                      (subject_template % i, "task:threadedflow"))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get rows", (end_time - start_time) / self.n,
                   self.n)

    start_time = time.time()
    for i in range(self.n):
      self.tp.AddTask(data_store.DB.Resolve,
                      ("aff4:/somerowthreaded", predicate_template % i))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get attributes",
                   (end_time - start_time) / self.n, self.n)

    start_time = time.time()
    for i in range(self.small_n):
      self.tp.AddTask(self.ResolvePrefixAndCheck,
                      ("aff4:/somerowthreaded", "task:someflowthreaded"))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get all versions",
                   (end_time - start_time) / self.small_n, self.small_n)

    start_time = time.time()
    for i in range(self.small_n):
      self.tp.AddTask(
          self.ResolvePrefixAndCheck,
          ("aff4:/threadedlargerow%d" % i, "task:largeflowthreaded", 1))
    self.tp.Join()
    data_store.DB.Flush()
    end_time = time.time()

    self.AddResult("Multithreaded: Get large values",
                   (end_time - start_time) / self.small_n, self.small_n)

  def BenchmarkAFF4Locks(self):

    client_id = "C.%016X" % 999

    # Write some data to read.
    client = aff4.FACTORY.Create(client_id, aff4_grr.VFSGRRClient, mode="w")
    client.Set(client.Schema.HOSTNAME("client1"))
    client.Close()

    cl = aff4.FACTORY.Open(client_id)
    self.assertEqual(cl.Get(cl.Schema.HOSTNAME), "client1")

    # Collect exceptions in threads.
    self.fails = []

    def Thread():
      try:
        # Using blocking_lock_timeout of 10 minutes to avoid possible
        # timeouts when running tests on slow hardware.
        with aff4.FACTORY.OpenWithLock(
            client_id,
            blocking=True,
            blocking_sleep_interval=0.2,
            blocking_lock_timeout=600) as client:
          self.assertEqual(client.Get(client.Schema.HOSTNAME), "client1")

      except Exception as e:  # pylint: disable=broad-except
        self.fails.append(e)

    start_time = time.time()
    for _ in range(self.n):
      Thread()
    end_time = time.time()

    self.AddResult("OpenWithLock", (end_time - start_time) / self.n, self.n)

    self.assertEmpty(self.fails)

    start_time = time.time()
    for _ in range(self.n):
      self.tp.AddTask(Thread, ())
    self.tp.Join()
    end_time = time.time()

    self.AddResult("Multithreaded: OpenWithLock",
                   (end_time - start_time) / self.n, self.n)

    self.assertEmpty(self.fails)
