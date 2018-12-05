#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_server.rdfvalues import objects as rdf_objects


def _SetTimestampNone(entries):
  for entry in entries:
    entry.timestamp = None


class DatabaseEventsTestMixin(object):

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
    self.db.WriteAPIAuditEntry(self._MakeEntry(router_method_name="bar"))
    self.db.WriteAPIAuditEntry(self._MakeEntry(router_method_name="foobar"))

    entries = self.db.ReadAPIAuditEntries(router_method_name="foo")
    _SetTimestampNone(entries)

    self.assertCountEqual(entries, [entry])

  def testReadEntriesFilterTimestamp(self):
    self.db.WriteAPIAuditEntry(self._MakeEntry(response_code="OK"))
    self.db.WriteAPIAuditEntry(self._MakeEntry(response_code="ERROR"))
    self.db.WriteAPIAuditEntry(self._MakeEntry(response_code="NOT_FOUND"))

    tomorrow = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1d")

    entries = self.db.ReadAPIAuditEntries(min_timestamp=tomorrow)
    self.assertEmpty(entries)

    entries = self.db.ReadAPIAuditEntries(max_timestamp=tomorrow)
    self.assertLen(entries, 3)

    timestamps = [e.timestamp for e in entries]

    entries = self.db.ReadAPIAuditEntries(min_timestamp=timestamps[1])
    self.assertEqual([e.response_code for e in entries], ["ERROR", "NOT_FOUND"])

    entries = self.db.ReadAPIAuditEntries(max_timestamp=timestamps[1])
    self.assertEqual([e.response_code for e in entries], ["OK", "ERROR"])

    entries = self.db.ReadAPIAuditEntries(
        min_timestamp=timestamps[1], max_timestamp=timestamps[1])
    self.assertEqual([e.response_code for e in entries], ["ERROR"])
