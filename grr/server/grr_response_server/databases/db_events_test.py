#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


def _SetTimestampNone(entries):
  for entry in entries:
    entry.timestamp = None


def _Date(date, time="00:00:00"):
  return rdfvalue.RDFDatetime.FromHumanReadable("{} {}".format(date, time))


class DatabaseTestEventsMixin(object):

  def _MakeEntry(self,
                 http_request_path="/test",
                 router_method_name="TestHandler",
                 username="user",
                 response_code="OK"):

    self.db.WriteGRRUser(username)

    return rdf_objects.APIAuditEntry(
        http_request_path=http_request_path,
        router_method_name=router_method_name,
        username=username,
        response_code=response_code,
    )

  def testWriteDoesNotMutate(self):
    entry = self._MakeEntry()
    copy = entry.Copy()
    self.db.WriteAPIAuditEntry(entry)
    self.assertEqual(entry, copy)

  def testWriteAuditEntry(self):
    entry = self._MakeEntry()
    self.db.WriteAPIAuditEntry(entry)

    entries = self.db.ReadAPIAuditEntries()
    _SetTimestampNone(entries)

    self.assertCountEqual(entries, [entry])

  def testWriteEntriesWithMicrosecondDifference(self):
    # MySQL TIMESTAMP's valid range starts from 1970-01-01 00:00:01,
    # hence we have to set the time to at least 1 second from epoch.
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(1000000 + 1)):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user2"))

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(1000000 + 2)):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))

    entries = self.db.ReadAPIAuditEntries()
    self.assertLen(entries, 3)

  def testReadEntries(self):
    entry1 = self._MakeEntry()
    self.db.WriteAPIAuditEntry(entry1)

    entry2 = self._MakeEntry(response_code="ERROR")
    self.db.WriteAPIAuditEntry(entry2)

    entries = self.db.ReadAPIAuditEntries()
    _SetTimestampNone(entries)

    self.assertCountEqual(entries, [entry1, entry2])

  def testReadEntriesOrder(self):
    status_codes = list(range(200, 210))

    for status_code in status_codes:
      self.db.WriteAPIAuditEntry(self._MakeEntry(response_code=status_code))

    entries = self.db.ReadAPIAuditEntries()
    _SetTimestampNone(entries)

    for entry, status_code in zip(entries, status_codes):
      self.assertEqual(entry.response_code, status_code)

  def testReadEntriesFilterUsername(self):
    entry = self._MakeEntry(username="foo")
    self.db.WriteAPIAuditEntry(entry)
    self.db.WriteAPIAuditEntry(self._MakeEntry(username="bar"))
    self.db.WriteAPIAuditEntry(self._MakeEntry(username="foobar"))

    entries = self.db.ReadAPIAuditEntries(username="foo")
    _SetTimestampNone(entries)

    self.assertCountEqual(entries, [entry])

  def testReadEntriesFilterRouterMethodName(self):
    entry = self._MakeEntry(router_method_name="foo")
    self.db.WriteAPIAuditEntry(entry)
    entry2 = self._MakeEntry(router_method_name="bar")
    self.db.WriteAPIAuditEntry(entry2)
    self.db.WriteAPIAuditEntry(self._MakeEntry(router_method_name="foobar"))

    entries = self.db.ReadAPIAuditEntries(router_method_names=["foo", "bar"])
    _SetTimestampNone(entries)

    self.assertCountEqual(entries, [entry, entry2])

  def testReadEntriesFilterTimestamp(self):
    self.db.WriteAPIAuditEntry(self._MakeEntry(response_code="OK"))
    ok_timestamp = rdfvalue.RDFDatetime.Now()

    self.db.WriteAPIAuditEntry(self._MakeEntry(response_code="ERROR"))
    error_timestamp = rdfvalue.RDFDatetime.Now()

    self.db.WriteAPIAuditEntry(self._MakeEntry(response_code="NOT_FOUND"))
    not_found_timestamp = rdfvalue.RDFDatetime.Now()

    entries = self.db.ReadAPIAuditEntries(min_timestamp=not_found_timestamp)
    self.assertEmpty(entries)

    entries = self.db.ReadAPIAuditEntries(max_timestamp=not_found_timestamp)
    self.assertLen(entries, 3)

    entries = self.db.ReadAPIAuditEntries(min_timestamp=ok_timestamp)
    self.assertEqual([e.response_code for e in entries], ["ERROR", "NOT_FOUND"])

    entries = self.db.ReadAPIAuditEntries(max_timestamp=error_timestamp)
    self.assertEqual([e.response_code for e in entries], ["OK", "ERROR"])

    entries = self.db.ReadAPIAuditEntries(
        min_timestamp=ok_timestamp, max_timestamp=error_timestamp)
    self.assertEqual([e.response_code for e in entries], ["ERROR"])

  def testCountEntries(self):
    day = _Date("2019-02-02")

    with test_lib.FakeTime(_Date("2019-02-02", "00:00:00")):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user2"))

    self.assertEqual({
        ("user1", day): 1,
        ("user2", day): 1
    }, self.db.CountAPIAuditEntriesByUserAndDay())

    with test_lib.FakeTime(_Date("2019-02-02", "23:59:59")):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))

    self.assertEqual({
        ("user1", day): 2,
        ("user2", day): 1
    }, self.db.CountAPIAuditEntriesByUserAndDay())

  def testCountEntriesFilteredByTimestamp(self):
    with test_lib.FakeTime(_Date("2019-02-01")):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user"))

    with test_lib.FakeTime(_Date("2019-02-02", "00:12:00")):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user2"))

    with test_lib.FakeTime(_Date("2019-02-02", "00:12:01")):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))

    with test_lib.FakeTime(_Date("2019-02-03")):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))

    with test_lib.FakeTime(_Date("2019-02-04")):
      self.db.WriteAPIAuditEntry(self._MakeEntry(username="user1"))

    counts = self.db.CountAPIAuditEntriesByUserAndDay(
        min_timestamp=_Date("2019-02-02"),
        max_timestamp=_Date("2019-02-03", "23:59:59"))
    self.assertEqual(
        {
            ("user1", _Date("2019-02-02")): 2,
            ("user2", _Date("2019-02-02")): 1,
            ("user1", _Date("2019-02-03")): 1,
        }, counts)

  def testDeleteUsersRetainsApiAuditEntries(self):
    entry = self._MakeEntry(username="foo")
    self.db.WriteAPIAuditEntry(entry)
    self.db.DeleteGRRUser("foo")
    entries = self.db.ReadAPIAuditEntries(username="foo")
    self.assertLen(entries, 1)
    self.assertEqual(entries[0].username, "foo")


# This file is a test library and thus does not require a __main__ block.
