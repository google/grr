#!/usr/bin/env python
"""The MySQL database methods for event handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
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
                          router_method_names=None,
                          min_timestamp=None,
                          max_timestamp=None,
                          cursor=None):
    """Returns audit entries stored in the database."""

    query = """SELECT details, timestamp
        FROM api_audit_entry
        WHERE_PLACEHOLDER
        ORDER BY timestamp ASC
    """

    conditions = []
    values = []
    where = ""

    if username is not None:
      conditions.append("username_hash = %s")
      values.append(mysql_utils.Hash(username))

    if router_method_names:
      placeholders = ["%s"] * len(router_method_names)
      placeholders = ", ".join(placeholders)
      conditions.append("router_method_name IN (%s)" % placeholders)
      values.extend(router_method_names)

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
    args = {
        "username_hash":
            mysql_utils.Hash(entry.username),
        "router_method_name":
            entry.router_method_name,
        "details":
            entry.SerializeToString(),
        "timestamp":
            mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())
    }
    query = "INSERT INTO api_audit_entry {columns} VALUES {values}".format(
        columns=mysql_utils.Columns(args),
        values=mysql_utils.NamedPlaceholders(args))
    cursor.execute(query, args)
