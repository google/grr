#!/usr/bin/env python
"""The MySQL database methods for event handling."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import events as rdf_events
from grr.server.grr_response_server.databases import mysql_utils


class MySQLDBEventMixin(object):
  """MySQLDB mixin for event handling."""

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllAuditEvents(self, cursor=None):
    """Reads all audit events stored in the database."""
    cursor.execute("""
        SELECT username, urn, client_id, timestamp, details
        FROM audit_event
        ORDER BY timestamp
    """)

    result = []
    for username, urn, client_id, timestamp, details in cursor.fetchall():
      event = rdf_events.AuditEvent.FromSerializedString(details)
      event.user = username
      if urn:
        event.urn = rdfvalue.RDFURN(urn)
      if client_id is not None:
        event.client = rdf_client.ClientURN(
            mysql_utils.IntToClientID(client_id))
      event.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      result.append(event)

    return result

  @mysql_utils.WithTransaction()
  def WriteAuditEvent(self, event, cursor=None):
    """Writes an audit event to the database."""
    event = event.Copy()

    if event.HasField("user"):
      username = event.user
      event.user = None
    else:
      username = None

    if event.HasField("urn"):
      urn = str(event.urn)
      event.urn = None
    else:
      urn = None

    if event.HasField("client"):
      client_id = mysql_utils.ClientIDToInt(event.client.Basename())
      event.client = None
    else:
      client_id = None

    if event.HasField("timestamp"):
      timestamp = mysql_utils.RDFDatetimeToMysqlString(event.timestamp)
      event.timestamp = None
    else:
      timestamp = mysql_utils.RDFDatetimeToMysqlString(
          rdfvalue.RDFDatetime.Now())

    details = event.SerializeToString()

    query = """
    INSERT INTO audit_event (username, urn, client_id, timestamp, details)
    VALUES (%s, %s, %s, %s, %s)
    """
    values = (username, urn, client_id, timestamp, details)

    cursor.execute(query, values)
