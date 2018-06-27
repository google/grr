#!/usr/bin/env python
"""The MySQL database methods for flow handling."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.server.grr_response_server.databases import mysql_utils
from grr.server.grr_response_server.rdfvalues import objects


class MySQLDBFlowMixin(object):
  """MySQLDB mixin for flow handling."""

  @mysql_utils.WithTransaction()
  def WriteMessageHandlerRequests(self, requests, cursor=None):
    """Writes a list of message handler requests to the database."""
    query = ("INSERT IGNORE INTO message_handler_requests "
             "(handlername, timestamp, request_id, request) VALUES ")
    now = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

    value_templates = []
    args = []
    for r in requests:
      args.extend([r.handler_name, now, r.request_id, r.SerializeToString()])
      value_templates.append("(%s, %s, %s, %s)")

    query += ",".join(value_templates)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadMessageHandlerRequests(self, cursor=None):
    """Reads all message handler requests from the database."""

    query = ("SELECT timestamp, request, leased_until, leased_by "
             "FROM message_handler_requests "
             "ORDER BY timestamp DESC")

    cursor.execute(query)

    res = []
    for timestamp, request, leased_until, leased_by in cursor.fetchall():
      req = objects.MessageHandlerRequest.FromSerializedString(request)
      req.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      req.leased_by = leased_by
      req.leased_until = mysql_utils.MysqlToRDFDatetime(leased_until)
      res.append(req)
    return res

  @mysql_utils.WithTransaction()
  def DeleteMessageHandlerRequests(self, requests, cursor=None):
    """Deletes a list of message handler requests from the database."""

    query = "DELETE FROM message_handler_requests WHERE request_id IN ({})"
    request_ids = set([r.request_id for r in requests])
    query = query.format(",".join(["%s"] * len(request_ids)))
    cursor.execute(query, request_ids)

  @mysql_utils.WithTransaction()
  def LeaseMessageHandlerRequests(self,
                                  lease_time=None,
                                  limit=1000,
                                  cursor=None):
    """Leases a number of message handler requests up to the indicated limit."""

    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToMysqlString(now)

    expiry = now + lease_time
    expiry_str = mysql_utils.RDFDatetimeToMysqlString(expiry)

    query = ("UPDATE message_handler_requests "
             "SET leased_until=%s, leased_by=%s "
             "WHERE leased_until IS NULL OR leased_until < %s "
             "LIMIT %s")

    id_str = utils.ProcessIdString()
    args = (expiry_str, id_str, now_str, limit)
    updated = cursor.execute(query, args)

    if updated == 0:
      return []

    cursor.execute(
        "SELECT timestamp, request FROM message_handler_requests "
        "WHERE leased_by=%s AND leased_until=%s LIMIT %s",
        (id_str, expiry_str, updated))
    res = []
    for timestamp, request in cursor.fetchall():
      req = objects.MessageHandlerRequest.FromSerializedString(request)
      req.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      req.leased_until = expiry
      req.leased_by = id_str
      res.append(req)

    return res
