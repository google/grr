#!/usr/bin/env python
"""The MySQL database methods for event handling."""

from typing import Optional

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils


def _AuditEntryFromRow(
    details: bytes, timestamp: float
) -> objects_pb2.APIAuditEntry:
  entry = objects_pb2.APIAuditEntry()
  entry.ParseFromString(details)
  entry.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(timestamp)
  return entry


class MySQLDBEventMixin(object):
  """MySQLDB mixin for event handling."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadAPIAuditEntries(
      self,
      username: Optional[str] = None,
      router_method_names: Optional[list[str]] = None,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> list[objects_pb2.APIAuditEntry]:
    """Returns audit entries stored in the database."""

    query = """SELECT details, UNIX_TIMESTAMP(timestamp)
        FROM api_audit_entry
        FORCE INDEX (api_audit_entry_by_username_timestamp)
        {WHERE_PLACEHOLDER}
        ORDER BY timestamp ASC
    """
    assert cursor is not None

    conditions = []
    values = []
    where = ""

    if username is not None:
      conditions.append("username = %s")
      values.append(username)

    if router_method_names:
      placeholders = ["%s"] * len(router_method_names)
      placeholders = ", ".join(placeholders)
      conditions.append("router_method_name IN (%s)" % placeholders)
      values.extend(router_method_names)

    if min_timestamp is not None:
      conditions.append("timestamp >= FROM_UNIXTIME(%s)")
      values.append(mysql_utils.RDFDatetimeToTimestamp(min_timestamp))

    if max_timestamp is not None:
      conditions.append("timestamp <= FROM_UNIXTIME(%s)")
      values.append(mysql_utils.RDFDatetimeToTimestamp(max_timestamp))

    if conditions:
      where = "WHERE " + " AND ".join(conditions)

    query = query.replace("{WHERE_PLACEHOLDER}", where)
    cursor.execute(query, values)

    return [
        _AuditEntryFromRow(details, timestamp)
        for details, timestamp in cursor.fetchall()
    ]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def CountAPIAuditEntriesByUserAndDay(
      self,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> dict[tuple[str, rdfvalue.RDFDatetime], int]:
    """Returns audit entry counts grouped by user and calendar day."""
    assert cursor is not None

    query = """
        -- Timestamps are timezone-agnostic whereas dates are not. Hence, we are
        -- forced to pick some timezone, in order to extract the day. We choose
        -- UTC ('+00:00') as it is the most sane default.
        SELECT username,
               CAST(CONVERT_TZ(timestamp, @@SESSION.time_zone, '+00:00')
                    AS DATE) AS day,
               COUNT(*)
        FROM api_audit_entry
        FORCE INDEX (api_audit_entry_by_username_timestamp)
        {WHERE_PLACEHOLDER}
        GROUP BY username, day
    """
    conditions = []
    values = []
    where = ""

    if min_timestamp is not None:
      conditions.append("timestamp >= FROM_UNIXTIME(%s)")
      values.append(mysql_utils.RDFDatetimeToTimestamp(min_timestamp))

    if max_timestamp is not None:
      conditions.append("timestamp <= FROM_UNIXTIME(%s)")
      values.append(mysql_utils.RDFDatetimeToTimestamp(max_timestamp))

    if conditions:
      where = "WHERE " + " AND ".join(conditions)

    query = query.replace("{WHERE_PLACEHOLDER}", where)
    cursor.execute(query, values)

    return {
        (username, rdfvalue.RDFDatetime.FromDate(day)): count
        for (username, day, count) in cursor.fetchall()
    }

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteAPIAuditEntry(
      self,
      entry: objects_pb2.APIAuditEntry,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes an audit entry to the database."""
    assert cursor is not None

    if not entry.HasField("timestamp"):
      datetime = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    else:
      datetime = entry.timestamp

    args = {
        "username": entry.username,
        "router_method_name": entry.router_method_name,
        "details": entry.SerializeToString(),
        "timestamp": mysql_utils.MicrosecondsSinceEpochToTimestamp(datetime),
    }
    query = """
    INSERT INTO api_audit_entry (username, router_method_name, details,
        timestamp)
    VALUES (%(username)s, %(router_method_name)s, %(details)s,
        FROM_UNIXTIME(%(timestamp)s))
    """
    cursor.execute(query, args)
