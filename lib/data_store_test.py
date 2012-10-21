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


import hashlib
import time
import zlib


from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2


FLAGS = flags.FLAGS


class DataStoreTest(test_lib.GRRBaseTest):
  """Test the data store abstraction."""
  test_row = "row:foo"

  def setUp(self):
    super(DataStoreTest, self).setUp()
    # Remove all test rows from the table
    for subject in data_store.DB.Query([], subject_prefix="row:",
                                       token=self.token):
      data_store.DB.DeleteSubject(subject["subject"][0], token=self.token)

  def testSetResolve(self):
    """Test the Set() and Resolve() methods."""
    predicate = "task:00000001"
    value = jobs_pb2.GrrMessage(session_id="session")

    # Ensure that setting a value is immediately available.
    data_store.DB.Set(self.test_row, predicate, value, token=self.token)
    (stored_proto, _) = data_store.DB.Resolve(
        self.test_row, predicate, decoder=jobs_pb2.GrrMessage,
        token=self.token)

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
    for count, (predicate, value, _) in enumerate(data_store.DB.ResolveRegex(
        self.test_row, "aff4:size", timestamp=data_store.DB.ALL_TIMESTAMPS,
        token=self.token)):
      self.assertEqual(value, 4)
      self.assertEqual(predicate, "aff4:size")

    self.assertEqual(count, 0)  # pylint: disable=W0631

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

  def testMultiResolveRegex(self):
    """tests MultiResolveRegex."""
    # Make some rows
    rows = []
    for i in range(10):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:%s" % i, i, timestamp=5,
                        token=self.token)
      rows.append(row_name)

    subjects = data_store.DB.MultiResolveRegex(
        rows, ["metadata:[34]", "metadata:[78]"], token=self.token)

    subject_names = subjects.keys()
    subject_names.sort()

    self.assertEqual(len(subjects), 4)
    self.assertEqual(subject_names, [u"row:3", u"row:4", u"row:7", u"row:8"])

  def testQuery(self):
    """Test our ability to query."""
    # Clear anything first
    for i in range(10):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:%s" % i, str(i), timestamp=5,
                        token=self.token)
      data_store.DB.Set(row_name, "aff4:type", "test", token=self.token)

    # Retrieve all subjects with metadata:5 set:
    rows = [row for row in data_store.DB.Query(
        ["metadata:5"], data_store.DB.filter.HasPredicateFilter("metadata:5"),
        subject_prefix="row:", token=self.token)]

    self.assertEqual(len(rows), 1)
    self.assertEqual(rows[0]["subject"][0], "row:5")
    self.assertEqual(rows[0]["metadata:5"][0], "5")
    self.assertEqual(rows[0]["metadata:5"][1], 5)

  def testQueryRegexUnicode(self):
    """Test our ability to query unicode strings using regular expressions."""

    unicodestrings = [(u"aff4:/C.0000000000000000/"
                       u"/test-Îñţérñåţîöñåļîžåţîờñ"),
                      (u"aff4:/C.0000000000000000/"
                       u"/test-Îñ铁网åţî[öñåļ(îžåţîờñ"),
                      # Test for special regex characters.
                      (u"aff4:/C.0000000000000000/"
                       u"/test-[]()+*?[]()"),
                      # We also want to test if datastore special characters
                      # are escaped correctly.
                      (u"aff4:/C.0000000000000000/"
                       u"/test-{qqq@qqq{aaa}")
                     ]

    for unicodestring in unicodestrings:
      data_store.DB.Set(unicodestring, u"metadata:uñîcödé",
                        "1", timestamp=5, token=self.token)
      data_store.DB.Set(unicodestring, "aff4:type", "test", token=self.token)

      # Retrieve all subjects with metadata:uñîcödé set matching our string:
      rows = [row for row in data_store.DB.Query(
          [u"metadata:uñîcödé"],
          data_store.DB.filter.HasPredicateFilter(u"metadata:uñîcödé"),
          unicodestring, token=self.token)]

      self.assertEqual(len(rows), 1)
      self.assertEqual(utils.SmartUnicode(rows[0]["subject"][0]), unicodestring)
      self.assertEqual(rows[0][u"metadata:uñîcödé"][0], "1")
      self.assertEqual(rows[0][u"metadata:uñîcödé"][1], 5)

      # Now using combination of regex and unicode

      child = unicodestring + u"/Îñţérñåţîöñåļîžåţîờñ-child"

      data_store.DB.Set(child, "metadata:regex", "2", timestamp=7,
                        token=self.token)
      data_store.DB.Set(child, "aff4:type", "test", token=self.token)

      rows = [row for row in data_store.DB.Query(
          ["metadata:regex"], data_store.DB.filter.AndFilter(
              data_store.DB.filter.HasPredicateFilter("metadata:regex"),
              data_store.DB.filter.SubjectContainsFilter(
                  "%s/[^/]+$" % data_store.EscapeRegex(unicodestring))),
          unicodestring, token=self.token)]

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
            data_store.DB.filter.SubjectContainsFilter(re),
            u"aff4:", token=self.token)]

        self.assertEqual(len(rows), 1)
        self.assertEqual(utils.SmartUnicode(rows[0]["subject"][0]),
                         unicodestring)
        self.assertEqual(rows[0][u"metadata:uñîcödé"][0], "1")
        self.assertEqual(rows[0][u"metadata:uñîcödé"][1], 5)

  def testQueryWithPrefix(self):
    """Test our ability to query with a prefix filter."""
    for i in range(11):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:5", i, token=self.token)
      data_store.DB.Set(row_name, "aff4:type", "test", token=self.token)

    # Retrieve all subjects with prefix row1:
    rows = [row for row in data_store.DB.Query(
        ["metadata:5"], data_store.DB.filter.HasPredicateFilter("metadata:5"),
        subject_prefix="row:1", token=self.token)]

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:1")
    self.assertEqual(rows[1]["subject"][0], "row:10")

  def testQueryWithPrefixNoAttributes(self):
    """Test our ability to query with a prefix filter."""
    for i in range(11):
      row_name = "row:%s" % i
      data_store.DB.Set(row_name, "metadata:5", i, token=self.token)
      data_store.DB.Set(row_name, "aff4:type", "test", token=self.token)

    # Retrieve all subjects with prefix row1:
    rows = [row for row in data_store.DB.Query(
        [], data_store.DB.filter.HasPredicateFilter("metadata:5"),
        subject_prefix="row:1", token=self.token)]

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:1")
    self.assertEqual(rows[1]["subject"][0], "row:10")
    self.assert_("subject" in rows[1])

  def testQueryWithLimit(self):
    """Test our ability to query with a prefix filter."""
    for i in range(11):
      row_name = "row:%02d" % i
      data_store.DB.Set(row_name, "metadata:5", i, token=self.token)
      data_store.DB.Set(row_name, "aff4:type", "test", token=self.token)

    # Retrieve all subjects with prefix row1:
    rows = [row for row in data_store.DB.Query(
        [], data_store.DB.filter.HasPredicateFilter("metadata:5"),
        subject_prefix="row:", limit=(2, 3), token=self.token)]

    self.assertEqual(len(rows), 3)
    self.assertEqual(rows[0]["subject"][0], "row:02")
    self.assertEqual(rows[1]["subject"][0], "row:03")
    self.assertEqual(rows[2]["subject"][0], "row:04")

  def testQueryWithSubjectFilter(self):
    """Test our ability to query with a subject filter."""
    subjects = []
    for i in range(9):
      row_name = "row:test %d" % i
      data_store.DB.Set(row_name, "metadata:5", i, token=self.token)
      data_store.DB.Set(row_name, "aff4:type", "test", token=self.token)
      subjects.append(row_name)

    # Retrieve all subjects with prefix:
    rows = [row for row in data_store.DB.Query(
        [], data_store.DB.filter.SubjectContainsFilter("test [1-5]"),
        subjects=subjects, token=self.token)]

    self.assertEqual(len(rows), 5)

    # Retrieve all subjects with prefix:
    rows = [row for row in data_store.DB.Query(
        [], data_store.DB.filter.SubjectContainsFilter("test [1-5]"),
        subject_prefix="row:", token=self.token)]

    self.assertEqual(len(rows), 5)

  def testFilters(self):
    """Test our ability to query with different filters."""
    # This makes a matrix of rows and predicates with exactly one predicate set
    # per row.
    predicates = "foo bar is so good".split()
    for i in range(11):
      row_name = "row:%02d" % i
      predicate = predicates[i % len(predicates)]
      data_store.DB.Set(row_name, "metadata:%s" % predicate,
                        utils.SmartUnicode(row_name + predicate),
                        token=self.token)
      data_store.DB.Set(row_name, "aff4:type", u"test", token=self.token)

    # Retrieve all subjects with prefix row1:
    rows = list(data_store.DB.Query(
        attributes=["metadata:foo"],
        filter_obj=data_store.DB.filter.HasPredicateFilter("metadata:foo"),
        token=self.token))

    for row in rows:
      self.assertEqual(row["metadata:foo"][0], row["subject"][0] + "foo")

    self.assertEqual(len(rows), 3)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:05")
    self.assertEqual(rows[2]["subject"][0], "row:10")

    rows = list(data_store.DB.Query(
        filter_obj=data_store.DB.filter.AndFilter(
            data_store.DB.filter.HasPredicateFilter("metadata:foo"),
            data_store.DB.filter.SubjectContainsFilter("row:[0-1]0")),
        token=self.token))

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:10")

    # Check that we can Query with a set of subjects
    rows = list(data_store.DB.Query(
        filter_obj=data_store.DB.filter.HasPredicateFilter("metadata:foo"),
        subjects=["row:00", "row:10"], token=self.token))

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:10")

    rows = list(data_store.DB.Query(
        filter_obj=data_store.DB.filter.PredicateContainsFilter(
            "metadata:foo", "row:0\\dfoo"),
        token=self.token))

    self.assertEqual(len(rows), 2)
    self.assertEqual(rows[0]["subject"][0], "row:00")
    self.assertEqual(rows[1]["subject"][0], "row:05")

  def testTransactions(self):
    """Test transactions raise."""
    predicate = u"metadata:predicateÎñţér"
    t1 = data_store.DB.Transaction(u"metadata:rowÎñţér", token=self.token)
    t2 = data_store.DB.Transaction(u"metadata:rowÎñţér", token=self.token)

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
    except Exception:  # pylint: disable=W0703
      # The first transaction succeeds
      t1.Set(predicate, "1")
      t1.Commit()

  def testTransactions2(self):
    """Test that transactions on different rows do not interfere."""
    predicate = u"metadata:predicate_Îñţér"
    t1 = data_store.DB.Transaction(u"metadata:row1Îñţér", token=self.token)
    t2 = data_store.DB.Transaction(u"metadata:row2Îñţér", token=self.token)

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
    subject = "metadata:8"

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
    subject = "metadata:9"

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
    subject = "metadata:9.1"

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
    subject = "metadata:10"

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
    subject = "metadata:101"

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
    subject = "metadata:11"

    predicates = []
    for i in range(0, 100):
      predicate = "metadata:predicate" + str(i)
      predicates.append(predicate)
      data_store.DB.Set(subject, predicate, "Cell "+predicate, timestamp=1000,
                        token=self.token)

    results = [x for x in data_store.DB.ResolveMulti(subject, predicates,
                                                     token=self.token)]

    self.assertEqual(len(results), 100)
    # Value
    for i in range(0, 100):
      self.assertEqual(results[i][1], "Cell "+predicates[i])
      self.assertEqual(results[i][0], predicates[i])

    # Now try to query for non existent predicates.
    predicates = predicates[:10]
    for i in range(10):
      predicates.append("metadata:not_existing" + str(i))

    results = [x for x in data_store.DB.ResolveMulti(subject, predicates,
                                                     token=self.token)]

    self.assertEqual(10, len(results))
    for i in range(0, 10):
      self.assertEqual(results[i][1], "Cell "+predicates[i])
      self.assertEqual(results[i][0], predicates[i])

  def testQueryIntegerRanges(self):
    """Test that querying for ranges works."""
    # Create some new aff4 objects with integer attributes
    for i in range(10):
      fd = aff4.FACTORY.Create("aff4:/C.1234/test%s" % i, "AFF4MemoryStream",
                               token=self.token)
      # This sets the SIZE attribute:
      fd.Write("A" * i)
      fd.Close()

    # Select a range
    rows = [row for row in data_store.DB.Query(
        [fd.Schema.SIZE], data_store.DB.filter.PredicateLessThanFilter(
            fd.Schema.SIZE, 5),
        subject_prefix="aff4:/C.1234/", token=self.token)]

    # We should receive rows 0-4 inclusive.
    self.assertEqual(len(rows), 5)
    for i in range(5):
      self.assertEqual("aff4:/C.1234/test%s" % i, rows[i]["subject"][0])

    rows = [row for row in data_store.DB.Query(
        [fd.Schema.SIZE], data_store.DB.filter.PredicateGreaterThanFilter(
            fd.Schema.SIZE, 5),
        subject_prefix="aff4:/C.1234/", token=self.token)]

    self.assertEqual(len(rows), 4)
    for i in range(6, 10):
      self.assertEqual("aff4:/C.1234/test%s" % i, rows[i-6]["subject"][0])

  def testAFF4Image(self):
    # 500k
    data = "randomdata" * 50 * 1024

    # Create a blob.
    cdata = zlib.compress(data)
    digest = hashlib.sha256(data).digest()
    urn = aff4.ROOT_URN.Add("blobs").Add(digest.encode("hex"))
    blob_fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", mode="w",
                                  token=self.token)
    blob_fd.Set(blob_fd.Schema.CONTENT(cdata))
    blob_fd.Set(blob_fd.Schema.SIZE(len(data)))
    blob_fd.Close(sync=True)

    # Now create the image containing the blob.
    fd = aff4.FACTORY.Create("aff4:/C.1235/image", "HashImage",
                             token=self.token)
    fd.Set(fd.Schema.CHUNKSIZE(512*1024))
    fd.Set(fd.Schema.STAT())

    fd.AddBlob(digest, len(data))
    fd.Close(sync=True)

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
