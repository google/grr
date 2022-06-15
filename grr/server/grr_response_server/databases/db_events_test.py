#!/usr/bin/env python
from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_server.rdfvalues import objects as rdf_objects


APIAuditEntry = rdf_objects.APIAuditEntry


def _Date(date: str) -> rdfvalue.RDFDatetime:
  return rdfvalue.RDFDatetime.FromHumanReadable(date)


class DatabaseTestEventsMixin(object):

  def _MakeEntry(
      self,
      http_request_path: str = "/test",
      router_method_name: str = "TestHandler",
      username: str = "user",
      response_code: APIAuditEntry.Code = APIAuditEntry.Code.OK,
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> APIAuditEntry:
    self.db.WriteGRRUser(username)

    return APIAuditEntry(
        http_request_path=http_request_path,
        router_method_name=router_method_name,
        username=username,
        response_code=response_code,
        timestamp=timestamp,
    )

  def _WriteEntry(self, **kwargs) -> rdf_objects.APIAuditEntry:
    entry = self._MakeEntry(**kwargs)
    self.db.WriteAPIAuditEntry(entry)
    return entry

  def testWriteDoesNotMutate(self):
    entry = self._MakeEntry()
    copy = entry.Copy()
    self.db.WriteAPIAuditEntry(entry)
    self.assertEqual(entry, copy)

  def testWriteAuditEntry(self):
    entry = self._WriteEntry()

    entries = self.db.ReadAPIAuditEntries()
    self.assertLen(entries, 1)

    # We should not compare timestamps.
    entries[0].timestamp = None
    self.assertCountEqual(entries, [entry])

  def testWriteEntriesWithMicrosecondDifference(self):
    # MySQL TIMESTAMP's valid range starts from 1970-01-01 00:00:01,
    # hence we have to set the time to at least 1 second from epoch.
    timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(1000000 + 1)
    entry1 = self._WriteEntry(username="user1", timestamp=timestamp)
    entry2 = self._WriteEntry(username="user2", timestamp=timestamp)

    timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(1000000 + 2)
    entry3 = self._WriteEntry(username="user1", timestamp=timestamp)

    entries = self.db.ReadAPIAuditEntries()
    self.assertCountEqual(entries, [entry1, entry2, entry3])

  def testReadEntries(self):
    entry1 = self._WriteEntry()
    entry2 = self._WriteEntry(response_code=APIAuditEntry.Code.ERROR)

    entries = self.db.ReadAPIAuditEntries()
    self.assertLen(entries, 2)

    # We should not compare timestamps.
    entries[0].timestamp = None
    entries[1].timestamp = None
    self.assertCountEqual(entries, [entry1, entry2])

  def testReadEntriesOrder(self):
    status_codes = [
        APIAuditEntry.Code.OK,
        APIAuditEntry.Code.ERROR,
        APIAuditEntry.Code.FORBIDDEN,
        APIAuditEntry.Code.NOT_FOUND,
        APIAuditEntry.Code.NOT_IMPLEMENTED,
    ]

    for status_code in status_codes:
      self._WriteEntry(response_code=status_code)

    entries = self.db.ReadAPIAuditEntries()

    for entry, status_code in zip(entries, status_codes):
      self.assertEqual(entry.response_code, status_code)

  def testReadEntriesFilterUsername(self):
    entry = self._WriteEntry(username="foo")
    self._WriteEntry(username="bar")
    self._WriteEntry(username="foobar")

    entries = self.db.ReadAPIAuditEntries(username="foo")
    self.assertLen(entries, 1)

    # We should not compare timestamps.
    entries[0].timestamp = None
    self.assertCountEqual(entries, [entry])

  def testReadEntriesFilterRouterMethodName(self):
    self._WriteEntry(router_method_name="foo")
    self._WriteEntry(router_method_name="bar")
    self._WriteEntry(router_method_name="foobar")

    entries = self.db.ReadAPIAuditEntries(router_method_names=["foo", "bar"])
    router_method_names = [_.router_method_name for _ in entries]
    self.assertCountEqual(router_method_names, ["foo", "bar"])

  def testReadEntriesFilterTimestamp(self):
    self._WriteEntry(response_code=APIAuditEntry.Code.OK)
    ok_timestamp = self.db.Now()

    self._WriteEntry(response_code=APIAuditEntry.Code.ERROR)
    error_timestamp = self.db.Now()

    self._WriteEntry(response_code=APIAuditEntry.Code.NOT_FOUND)
    not_found_timestamp = self.db.Now()

    entries = self.db.ReadAPIAuditEntries(min_timestamp=not_found_timestamp)
    self.assertEmpty(entries)

    entries = self.db.ReadAPIAuditEntries(max_timestamp=not_found_timestamp)
    self.assertLen(entries, 3)

    entries = self.db.ReadAPIAuditEntries(min_timestamp=ok_timestamp)
    self.assertEqual([e.response_code for e in entries],
                     [APIAuditEntry.Code.ERROR, APIAuditEntry.Code.NOT_FOUND])

    entries = self.db.ReadAPIAuditEntries(max_timestamp=error_timestamp)
    self.assertEqual([e.response_code for e in entries],
                     [APIAuditEntry.Code.OK, APIAuditEntry.Code.ERROR])

    entries = self.db.ReadAPIAuditEntries(
        min_timestamp=ok_timestamp, max_timestamp=error_timestamp)
    self.assertEqual([e.response_code for e in entries],
                     [APIAuditEntry.Code.ERROR])

  def testCountEntries(self):
    day = _Date("2019-02-02")

    self._WriteEntry(username="user1", timestamp=_Date("2019-02-02 00:00"))
    self._WriteEntry(username="user2", timestamp=_Date("2019-02-02 00:00"))

    self.assertEqual({
        ("user1", day): 1,
        ("user2", day): 1
    }, self.db.CountAPIAuditEntriesByUserAndDay())

    self._WriteEntry(username="user1", timestamp=_Date("2019-02-02 23:59:59"))

    self.assertEqual({
        ("user1", day): 2,
        ("user2", day): 1
    }, self.db.CountAPIAuditEntriesByUserAndDay())

  def testCountEntriesFilteredByTimestamp(self):
    self._WriteEntry(username="user", timestamp=_Date("2019-02-01"))
    self._WriteEntry(username="user1", timestamp=_Date("2019-02-02 00:12:00"))
    self._WriteEntry(username="user2", timestamp=_Date("2019-02-02 00:12:00"))
    self._WriteEntry(username="user1", timestamp=_Date("2019-02-02 00:12:01"))
    self._WriteEntry(username="user1", timestamp=_Date("2019-02-03"))
    self._WriteEntry(username="user1", timestamp=_Date("2019-02-04"))

    counts = self.db.CountAPIAuditEntriesByUserAndDay(
        min_timestamp=_Date("2019-02-02"),
        max_timestamp=_Date("2019-02-03 23:59:59"))
    self.assertEqual(
        {
            ("user1", _Date("2019-02-02")): 2,
            ("user2", _Date("2019-02-02")): 1,
            ("user1", _Date("2019-02-03")): 1,
        }, counts)

  def testDeleteUsersRetainsApiAuditEntries(self):
    self._WriteEntry(username="foo")
    self.db.DeleteGRRUser("foo")

    entries = self.db.ReadAPIAuditEntries(username="foo")
    self.assertLen(entries, 1)
    self.assertEqual(entries[0].username, "foo")

  def testWriteAndReadWithCommitTimestamp(self):
    entry = self._MakeEntry(username="foo")

    before = self.db.Now()
    self.db.WriteAPIAuditEntry(entry)
    after = self.db.Now()

    entries = self.db.ReadAPIAuditEntries(username="foo")
    self.assertLen(entries, 1)
    self.assertBetween(entries[0].timestamp, before, after)


# This file is a test library and thus does not require a __main__ block.
