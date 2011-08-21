#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""These are basic tests for the data store abstraction.

Implementations should be able to pass these tests to be conformant.
"""


import time


from grr.client import conf as flags
from grr.lib import data_store

from grr.lib import fake_data_store
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2



FLAGS = flags.FLAGS


class DataStoreTest(test_lib.GRRBaseTest):
  """Test the data store abstraction."""
  test_row = "row:foo"

  def setUp(self):
    # Remove all test rows from the table
    for subject in data_store.DB.Query([], subject_prefix="row:"):
      data_store.DB.Transaction(subject["subject"][0]).DeleteSubject().Commit()

  def testSetResolve(self):
    """Test the Set() and Resolve() methods."""
    predicate = "metadata:predicate"
    value = jobs_pb2.GrrMessage(session_id="session")

    # Ensure that setting a value is immediately available.
    data_store.DB.Set(self.test_row, predicate, value)
    (stored_proto, _) = data_store.DB.Resolve(
        self.test_row, predicate, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(stored_proto.session_id, value.session_id)

  def testMultiSet(self):
    """Test the MultiSet() methods."""
    data_store.DB.MultiSet(self.test_row,
                           {"metadata:1": 1,
                            "metadata:2": 2})

    (stored, _) = data_store.DB.Resolve(self.test_row, "metadata:1")
    self.assertEqual(stored, "1")

    (stored, _) = data_store.DB.Resolve(self.test_row, "metadata:2")
    self.assertEqual(stored, "2")

  def testDeleteAttributes(self):
    """Test we can delete an attribute."""
    predicate = "metadata:predicate"

    data_store.DB.Set(self.test_row, predicate, "hello")

    # Check its there
    (stored, _) = data_store.DB.Resolve(self.test_row, predicate)

    self.assertEqual(stored, "hello")

    data_store.DB.DeleteAttributes(self.test_row, [predicate])
    (stored, _) = data_store.DB.Resolve(self.test_row, predicate)

    self.assertEqual(stored, None)

  def testMultiResolveRegex(self):
    """Test our ability to query."""
    # Make some rows
    rows = []
    for i in range(10):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:%s" % i, i, timestamp=5)
      rows.append(row_name)

    subjects = data_store.DB.MultiResolveRegex(
        rows, ["metadata:[34]", "metadata:[78]"])

    subject_names = subjects.keys()
    subject_names.sort()

    self.assertEqual(len(subjects), 4)
    self.assertEqual(subject_names, [u"row:3", u"row:4", u"row:7", u"row:8"])

  def testQuery(self):
    """Test our ability to query."""
    # Clear anything first
    for i in range(10):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:%s" % i, i, timestamp=5)

    # Retrieve all subjects with metadata:5 set:
    rows = [row for row in data_store.DB.Query(
        ["metadata:5"], data_store.DB.Filter.HasPredicateFilter("metadata:5"),
        subject_prefix="row:")]

    self.assertEqual(len(rows), 1)
    self.assertEqual(rows[0]["subject"][0], "row:5")
    self.assertEqual(rows[0]["metadata:5"][0], "5")
    self.assertEqual(rows[0]["metadata:5"][1], 5)

  def testQueryRegexUnicode(self):
    """Test our ability to query unicode strings using regular expressions."""

    unicodestrings = [(u"aff4:/C.0000000000000000/"
                       u"/test-Îñţérñåţîöñåļîžåţîờñ"),
                      (u"aff4:/C.0000000000000000/"
                       u"/test-[]()[]()"),
                      (u"aff4:/C.0000000000000000/"
                       u"/test-Îñ铁网åţî[öñåļ(îžåţîờñ")]

    for unicodestring in unicodestrings:
      data_store.DB.Set(unicodestring, u"metadata:uñîcödé", 1, timestamp=5)

      # Retrieve all subjects with metadata:uñîcödé set matching our string:
      rows = [row for row in data_store.DB.Query(
          [u"metadata:uñîcödé"],
          data_store.DB.Filter.HasPredicateFilter(u"metadata:uñîcödé"),
          unicodestring)]

      self.assertEqual(len(rows), 1)
      self.assertEqual(utils.SmartUnicode(rows[0]["subject"][0]), unicodestring)
      self.assertEqual(rows[0][u"metadata:uñîcödé"][0], "1")
      self.assertEqual(rows[0][u"metadata:uñîcödé"][1], 5)

      # Now using combination of regex and unicode

      child = unicodestring + u"/Îñţérñåţîöñåļîžåţîờñ-child"

      data_store.DB.Set(child, "metadata:regex", 2, timestamp=7)

      rows = [row for row in data_store.DB.Query(
          ["metadata:regex"], data_store.DB.Filter.AndFilter(
              data_store.DB.Filter.HasPredicateFilter("metadata:regex"),
              data_store.DB.Filter.SubjectContainsFilter(
                  "%s/[^/]+$" % data_store.EscapeRegex(unicodestring))),
          unicodestring)]

      self.assertEqual(len(rows), 1)
      self.assertEqual(utils.SmartUnicode(rows[0]["subject"][0]), child)
      self.assertEqual(rows[0][u"metadata:regex"][0], "2")
      self.assertEqual(rows[0][u"metadata:regex"][1], 7)

      regexes = []
      regexes.append(u"%s[^/]+$" % data_store.EscapeRegex(unicodestring[:-5]))
      regexes.append(u"%s.+%s$" %
                     (data_store.EscapeRegex(unicodestring[:-5]),
                      data_store.EscapeRegex(unicodestring[-3:])))
      regexes.append(u"%s[^/]+%s$" %
                     (data_store.EscapeRegex(unicodestring[:-7]),
                      data_store.EscapeRegex(unicodestring[-6:])))

      for re in regexes:
        rows = [row for row in data_store.DB.Query(
            [u"metadata:uñîcödé"],
            data_store.DB.Filter.SubjectContainsFilter(re),
            u"aff4:")]

        self.assertEqual(len(rows), 1)
        self.assertEqual(utils.SmartUnicode(rows[0]["subject"][0]),
                         unicodestring)
        self.assertEqual(rows[0][u"metadata:uñîcödé"][0], "1")
        self.assertEqual(rows[0][u"metadata:uñîcödé"][1], 5)

  def testQueryWithPrefix(self):
    """Test our ability to query with a prefix filter."""
    for i in range(11):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:5", i)

    # Retrieve all subjects with prefix row1:
    rows = [row for row in data_store.DB.Query(
        ["metadata:5"], data_store.DB.Filter.HasPredicateFilter("metadata:5"),
        subject_prefix="row:1")]

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:1")
    self.assertEqual(rows[1]["subject"][0], "row:10")

  def testQueryWithPrefixNoAttributes(self):
    """Test our ability to query with a prefix filter."""
    for i in range(11):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:51", i)

    # Retrieve all subjects with prefix row1:
    rows = [row for row in data_store.DB.Query(
        [], data_store.DB.Filter.HasPredicateFilter("metadata:51"),
        subject_prefix="row:1")]

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:1")
    self.assertEqual(rows[1]["subject"][0], "row:10")
    self.assertEqual(rows[1].keys(), ["subject"])

  def testQueryWithLimit(self):
    """Test our ability to query with a prefix filter."""
    for i in range(11):
      row_name = "row:%02d" % i
      data_store.DB.Set(row_name, "metadata:51", i)

    # Retrieve all subjects with prefix row1:
    rows = [row for row in data_store.DB.Query(
        [], data_store.DB.Filter.HasPredicateFilter("metadata:51"),
        subject_prefix="row:", limit=(2, 3))]

    self.assertEqual(len(rows), 3)
    self.assertEqual(rows[0]["subject"][0], "row:02")
    self.assertEqual(rows[1]["subject"][0], "row:03")
    self.assertEqual(rows[2]["subject"][0], "row:04")

  def testFilters(self):
    """Test our ability to query with different filters."""
    # This makes a matrix of rows and predicates with exactly one predicate set
    # per row.
    predicates = "foo bar is so good".split()
    for i in range(11):
      row_name = "row:%02d" % i
      predicate = predicates[i % len(predicates)]
      data_store.DB.Set(row_name, "metadata:%s" % predicate,
                        row_name + predicate)

    # Retrieve all subjects with prefix row1:
    rows = list(data_store.DB.Query(
        attributes=["metadata:foo"],
        filter_obj=data_store.DB.Filter.HasPredicateFilter("metadata:foo")))

    for row in rows:
      self.assertEqual(row["metadata:foo"][0], row["subject"][0] + "foo")

    self.assertEqual(len(rows), 3)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:05")
    self.assertEqual(rows[2]["subject"][0], "row:10")

    rows = list(data_store.DB.Query(
        filter_obj=data_store.DB.Filter.AndFilter(
            data_store.DB.Filter.HasPredicateFilter("metadata:foo"),
            data_store.DB.Filter.SubjectContainsFilter("row:[0-1]0"))))

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:10")

    # Check that we can Query with a set of subjects
    rows = list(data_store.DB.Query(
        filter_obj=data_store.DB.Filter.HasPredicateFilter("metadata:foo"),
        subjects=["row:00", "row:10"]))

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:10")

    rows = list(data_store.DB.Query(
        filter_obj=data_store.DB.Filter.PredicateContainsFilter(
            "metadata:foo", "row:0\\dfoo")))

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:05")

  def testTransactions(self):
    """Test transactions raise."""
    predicate = u"metadata:predicateÎñţér"
    t1 = data_store.DB.Transaction(u"metadata:rowÎñţér")
    t2 = data_store.DB.Transaction(u"metadata:rowÎñţér")

    # This grabs read locks on these transactions
    t1.Resolve(predicate)
    t2.Resolve(predicate)

    # Now this should raise since t2 has a read lock:
    t1.Set(predicate, "1")
    # There are two variants allowed here regarding the order of transactions -
    # both are ok but we need to test them slightly differently.
    try:
      # The last transaction succeeds
      t2.Set(predicate, "2")
      t2.Commit()

      self.assertRaises(data_store.Error, t1.Commit)
      # We are not exactly sure what exception is raised here. Normally commit()
      # can raise whatever the implementation of RetryWrapper can take. Commit()
      # should never be called outside of RetwryWrapper.
    except Exception:
      # The first transaction succeeds
      t1.Set(predicate, "1")
      t1.Commit()

  def testTransactions2(self):
    """Test that transactions on different rows do not interfere."""
    predicate = u"metadata:predicate_Îñţér"
    t1 = data_store.DB.Transaction(u"metadata:row1Îñţér")
    t2 = data_store.DB.Transaction(u"metadata:row2Îñţér")

    # This grabs read locks on these transactions
    t1.Resolve(predicate)
    t2.Resolve(predicate)

    # Now this should not raise since t1 and t2 are on different subjects
    t1.Set(predicate, "1")
    t1.Commit()
    t2.Set(predicate, "2")
    t2.Commit()

  def testTimestamps(self):
    """Check that timestamps are reasonable."""
    predicate = "metadata:predicate"
    t = data_store.DB.Transaction("metadata:8")

    # Extend the range of valid timestamps returned from the table to account
    # for potential clock skew.
    start = long(time.time() - 60) * 1e6

    t.Set(predicate, "1")
    t.Commit()

    t = data_store.DB.Transaction("metadata:8")
    (stored, ts) = t.Resolve(predicate)

    # Check the time is reasonable
    end = long(time.time() + 60) * 1e6

    self.assert_(ts >= start and ts <= end)
    self.assertEqual(stored, "1")

  def testSpecificTimestamps(self):
    """Check arbitrary timestamps can be specified."""
    predicate = "metadata:predicate"
    t = data_store.DB.Transaction("metadata:9")

    # Check we can specify a timestamp
    t.Set(predicate, "2", timestamp=1000)
    t.Commit()

    t = data_store.DB.Transaction("metadata:9")
    (stored, ts) = t.Resolve(predicate)

    # Check the time is reasonable
    self.assertEqual(ts, 1000)
    self.assertEqual(stored, "2")

  def testResolveRegEx(self):
    """Test regex Resolving works."""
    predicate = "metadata:predicate"

    t = data_store.DB.Transaction("metadata:10")

    # Check we can specify a timestamp
    t.Set(predicate, "3", timestamp=1000)
    t.Commit()

    t = data_store.DB.Transaction("metadata:10")
    results = [x for x in t.ResolveRegex("metadata:pred.*",
                                         timestamp=(0, 2000))]

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
    t = data_store.DB.Transaction("metadata:101")

    # Check we can specify a timestamp
    t.Set(predicate, "3")
    t.Commit()

    t = data_store.DB.Transaction("metadata:101")
    results = [x for x in t.ResolveRegex("metadata:.*")]

    self.assertEqual(len(results), 1)
    # Value
    self.assertEqual(results[0][1], "3")
    # Predicate
    self.assertEqual(results[0][0], predicate)

  def testResolveMulti(self):
    """Test regex Multi Resolving works."""

    def SetPredicate(predicate):
      t = data_store.DB.Transaction("metadata:11")

      # Check we can specify a timestamp
      t.Set(predicate, "Cell "+predicate, timestamp=1000)
      t.Commit()

    predicates = []
    for i in range(0, 100):
      predicate = "metadata:predicate" + str(i)
      predicates.append(predicate)
      SetPredicate(predicate)

    t = data_store.DB.Transaction("metadata:11")
    results = [x for x in t.ResolveMulti(predicates)]

    self.assertEqual(len(results), 100)
    # Value
    for i in range(0, 100):
      self.assertEqual(results[i][1], "Cell "+predicates[i])
      self.assertEqual(results[i][0], predicates[i])
