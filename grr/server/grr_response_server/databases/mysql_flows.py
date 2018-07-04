#!/usr/bin/env python
"""The MySQL database methods for flow handling."""

import MySQLdb

from grr.core.grr_response_core.lib import rdfvalue
from grr.core.grr_response_core.lib import utils
from grr.core.grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.server.grr_response_server import db
from grr.server.grr_response_server.databases import mysql_utils
from grr.server.grr_response_server.rdfvalues import objects as rdf_objects


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
      req = rdf_objects.MessageHandlerRequest.FromSerializedString(request)
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
      req = rdf_objects.MessageHandlerRequest.FromSerializedString(request)
      req.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      req.leased_until = expiry
      req.leased_by = id_str
      res.append(req)

    return res

  @mysql_utils.WithTransaction()
  def ReadClientMessages(self, client_id, cursor=None):
    """Reads all client messages available for a given client_id."""

    query = ("SELECT message, leased_until, leased_by FROM client_messages "
             "WHERE client_id = %s")

    cursor.execute(query, [mysql_utils.ClientIDToInt(client_id)])

    ret = []
    for msg, leased_until, leased_by in cursor.fetchall():
      message = rdf_flows.GrrMessage.FromSerializedString(msg)
      if leased_until:
        message.leased_by = leased_by
        message.leased_until = mysql_utils.MysqlToRDFDatetime(leased_until)
      ret.append(message)
    return ret

  @mysql_utils.WithTransaction()
  def DeleteClientMessages(self, messages, cursor=None):
    """Deletes a list of client messages from the db."""
    if not messages:
      return

    args = []
    conditions = ["(client_id=%s and message_id=%s)"] * len(messages)
    query = "DELETE FROM client_messages WHERE " + " OR ".join(conditions)
    for m in messages:
      args.append(mysql_utils.ClientIDToInt(m.queue.Split()[0]))
      args.append(m.task_id)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction()
  def LeaseClientMessages(self,
                          client_id,
                          lease_time=None,
                          limit=None,
                          cursor=None):
    """Leases available client messages for the client with the given id."""

    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToMysqlString(now)
    expiry = now + lease_time
    expiry_str = mysql_utils.RDFDatetimeToMysqlString(expiry)
    proc_id_str = utils.ProcessIdString()
    client_id_int = mysql_utils.ClientIDToInt(client_id)

    query = ("UPDATE client_messages "
             "SET leased_until=%s, leased_by=%s "
             "WHERE client_id=%s AND "
             "(leased_until IS NULL OR leased_until < %s) "
             "LIMIT %s")
    args = [expiry_str, proc_id_str, client_id_int, now_str, limit]

    num_leased = cursor.execute(query, args)
    if num_leased == 0:
      return []

    query = ("SELECT message FROM client_messages "
             "WHERE client_id=%s AND leased_until=%s AND leased_by=%s")

    cursor.execute(query, [client_id_int, expiry_str, proc_id_str])

    ret = []
    for msg, in cursor.fetchall():
      message = rdf_flows.GrrMessage.FromSerializedString(msg)
      message.leased_by = proc_id_str
      message.leased_until = expiry
      ret.append(message)
    return ret

  @mysql_utils.WithTransaction()
  def WriteClientMessages(self, messages, cursor=None):
    """Writes messages that should go to the client to the db."""

    query = ("INSERT IGNORE INTO client_messages "
             "(client_id, message_id, timestamp, message) "
             "VALUES %s ON DUPLICATE KEY UPDATE "
             "timestamp=VALUES(timestamp), message=VALUES(message)")
    now = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

    value_templates = []
    args = []
    for m in messages:
      client_id_int = mysql_utils.ClientIDToInt(m.queue.Split()[0])
      args.extend([client_id_int, m.task_id, now, m.SerializeToString()])
      value_templates.append("(%s, %s, %s, %s)")

    query %= ",".join(value_templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(cause=e)
