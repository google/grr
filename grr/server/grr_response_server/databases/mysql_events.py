#!/usr/bin/env python
"""The MySQL database methods for event handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects


def _AuditEntryFromRow(details, timestamp):
  entry = rdf_objects.APIAuditEntry.FromSerializedString(details)
  entry.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
  return entry


class MySQLDBEventMixin(object):
  """MySQLDB mixin for event handling."""

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAPIAuditEntries(self,
                          username=None,
                          router_method_name=None,
                          min_timestamp=None,
                          max_timestamp=None,
                          cursor=None):
    """Returns audit entries stored in the database."""

    query = """SELECT details, timestamp
        FROM admin_ui_access_audit_entry
        WHERE_PLACEHOLDER
        ORDER BY timestamp ASC
    """

    conditions = []
    values = []
    where = ""

    if username is not None:
      conditions.append("username = %s")
      values.append(username)

    if router_method_name is not None:
      conditions.append("router_method_name = %s")
      values.append(router_method_name)

    if min_timestamp is not None:
      conditions.append("timestamp >= %s")
      values.append(mysql_utils.RDFDatetimeToMysqlString(min_timestamp))

    if max_timestamp is not None:
      conditions.append("timestamp <= %s")
      values.append(mysql_utils.RDFDatetimeToMysqlString(max_timestamp))

    if conditions:
      where = "WHERE " + " AND ".join(conditions)

    query = query.replace("WHERE_PLACEHOLDER", where)
    cursor.execute(query, values)

    return [
        _AuditEntryFromRow(details, timestamp)
        for details, timestamp in cursor.fetchall()
    ]

  @mysql_utils.WithTransaction()
  def WriteAPIAuditEntry(self, entry, cursor=None):
    """Writes an audit entry to the database."""

    query = """
    INSERT INTO admin_ui_access_audit_entry
        (username, router_method_name, timestamp, details)
    VALUES
        (%(username)s, %(router_method_name)s, CURRENT_TIMESTAMP(6), %(details)s)
    """
    cursor.execute(
        query, {
            "username": entry.username,
            "router_method_name": entry.router_method_name,
            "details": entry.SerializeToString()
        })
