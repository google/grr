#!/usr/bin/env python
"""The MySQL database methods for flow handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading
import time

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import db
from grr_response_server import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects


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

  def RegisterMessageHandler(self, handler, lease_time, limit=1000):
    """Leases a number of message handler requests up to the indicated limit."""
    self.UnregisterMessageHandler()

    if handler:
      self.handler_stop = False
      self.handler_thread = threading.Thread(
          name="message_handler",
          target=self._MessageHandlerLoop,
          args=(handler, lease_time, limit))
      self.handler_thread.daemon = True
      self.handler_thread.start()

  def UnregisterMessageHandler(self, timeout=None):
    """Unregisters any registered message handler."""
    if self.handler_thread:
      self.handler_stop = True
      self.handler_thread.join(timeout)
      if self.handler_thread.isAlive():
        raise RuntimeError("Message handler thread did not join in time.")
      self.handler_thread = None

  def _MessageHandlerLoop(self, handler, lease_time, limit):
    while not self.handler_stop:
      try:
        msgs = self._LeaseMessageHandlerRequests(lease_time, limit)
        if msgs:
          handler(msgs)
        else:
          time.sleep(5)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("_LeaseMessageHandlerRequests raised %s.", e)

  @mysql_utils.WithTransaction()
  def _LeaseMessageHandlerRequests(self, lease_time, limit, cursor=None):
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

  @mysql_utils.WithTransaction(readonly=True)
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

    return sorted(ret, key=lambda msg: msg.task_id)

  @mysql_utils.WithTransaction()
  def DeleteClientMessages(self, messages, cursor=None):
    """Deletes a list of client messages from the db."""
    if not messages:
      return

    to_delete = []
    for m in messages:
      to_delete.append((db_utils.ClientIdFromGrrMessage(m), m.task_id))

    if len(set(to_delete)) != len(to_delete):
      raise ValueError(
          "Received multiple copies of the same message to delete.")

    self._DeleteClientMessages(to_delete, cursor=cursor)

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
             "SET leased_until=%s, leased_by=%s, leased_count=leased_count+1 "
             "WHERE client_id=%s AND "
             "(leased_until IS NULL OR leased_until < %s) "
             "LIMIT %s")
    args = [expiry_str, proc_id_str, client_id_int, now_str, limit]

    num_leased = cursor.execute(query, args)
    if num_leased == 0:
      return []

    query = ("SELECT message, leased_count FROM client_messages "
             "WHERE client_id=%s AND leased_until=%s AND leased_by=%s")

    cursor.execute(query, [client_id_int, expiry_str, proc_id_str])

    ret = []
    expired = []
    for msg, leased_count in cursor.fetchall():
      message = rdf_flows.GrrMessage.FromSerializedString(msg)
      message.leased_by = proc_id_str
      message.leased_until = expiry
      # > comparison since this check happens after the lease.
      if leased_count > db.Database.CLIENT_MESSAGES_TTL:
        expired.append((client_id, message.task_id))
      else:
        ret.append(message)

    if expired:
      self._DeleteClientMessages(expired, cursor=cursor)

    return sorted(ret, key=lambda msg: msg.task_id)

  @mysql_utils.WithTransaction()
  def WriteClientMessages(self, messages, cursor=None):
    """Writes messages that should go to the client to the db."""

    query = ("INSERT IGNORE INTO client_messages "
             "(client_id, message_id, timestamp, message) "
             "VALUES %s ON DUPLICATE KEY UPDATE "
             "timestamp=VALUES(timestamp), message=VALUES(message)")
    now = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

    client_ids = set()

    value_templates = []
    args = []
    for m in messages:
      cid = db_utils.ClientIdFromGrrMessage(m)
      client_ids.add(cid)
      client_id_int = mysql_utils.ClientIDToInt(cid)
      args.extend([client_id_int, m.task_id, now, m.SerializeToString()])
      value_templates.append("(%s, %s, %s, %s)")

    query %= ",".join(value_templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownClientError(client_ids=client_ids, cause=e)

  @mysql_utils.WithTransaction()
  def WriteFlowObject(self, flow_obj, cursor=None):
    """Writes a flow object to the database."""

    query = ("INSERT INTO flows "
             "(client_id, flow_id, long_flow_id, parent_flow_id, flow, "
             "next_request_to_process, timestamp, last_update) VALUES "
             "(%s, %s, %s, %s, %s, %s, %s, %s) "
             "ON DUPLICATE KEY UPDATE "
             "flow=VALUES(flow), "
             "next_request_to_process=VALUES(next_request_to_process),"
             "last_update=VALUES(last_update)")

    if flow_obj.parent_flow_id:
      pfi = mysql_utils.FlowIDToInt(flow_obj.parent_flow_id)
    else:
      pfi = None

    timestamp_str = mysql_utils.RDFDatetimeToMysqlString(flow_obj.create_time)
    now_str = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())

    args = [
        mysql_utils.ClientIDToInt(flow_obj.client_id),
        mysql_utils.FlowIDToInt(flow_obj.flow_id), flow_obj.long_flow_id, pfi,
        flow_obj.SerializeToString(), flow_obj.next_request_to_process,
        timestamp_str, now_str
    ]
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(flow_obj.client_id, cause=e)

  def _FlowObjectFromRow(self, row):
    """Generates a flow object from a database row."""

    flow, cci, pt, nr, pd, po, ps, ts, lut = row

    flow_obj = rdf_flow_objects.Flow.FromSerializedString(flow)
    if cci is not None:
      cc_cls = rdf_client.ClientCrash
      flow_obj.client_crash_info = cc_cls.FromSerializedString(cci)
    if pt is not None:
      pt_cls = rdf_flow_objects.PendingFlowTermination
      flow_obj.pending_termination = pt_cls.FromSerializedString(pt)
    if nr:
      flow_obj.next_request_to_process = nr
    if pd is not None:
      flow_obj.processing_deadline = mysql_utils.MysqlToRDFDatetime(pd)
    if po is not None:
      flow_obj.processing_on = po
    if ps is not None:
      flow_obj.processing_since = mysql_utils.MysqlToRDFDatetime(ps)
    flow_obj.timestamp = mysql_utils.MysqlToRDFDatetime(ts)
    flow_obj.last_update_time = mysql_utils.MysqlToRDFDatetime(lut)

    return flow_obj

  FLOW_DB_FIELDS = ("flow, client_crash_info, pending_termination, "
                    "next_request_to_process, processing_deadline, "
                    "processing_on, processing_since, timestamp, last_update ")

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowObject(self, client_id, flow_id, cursor=None):
    """Reads a flow object from the database."""
    query = ("SELECT " + self.FLOW_DB_FIELDS +
             "FROM flows WHERE client_id=%s AND flow_id=%s")
    cursor.execute(query, [
        mysql_utils.ClientIDToInt(client_id),
        mysql_utils.FlowIDToInt(flow_id)
    ])
    result = cursor.fetchall()
    if not result:
      raise db.UnknownFlowError(client_id, flow_id)
    row, = result
    return self._FlowObjectFromRow(row)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllFlowObjects(self, client_id, min_create_time=None, cursor=None):
    """Reads all flow objects from the database for a given client."""
    query = "SELECT " + self.FLOW_DB_FIELDS + " FROM flows WHERE client_id=%s"
    args = [mysql_utils.ClientIDToInt(client_id)]

    if min_create_time is not None:
      query += " AND timestamp >= %s"
      args.append(mysql_utils.RDFDatetimeToMysqlString(min_create_time))

    cursor.execute(query, args)
    return [self._FlowObjectFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction(readonly=True)
  def ReadChildFlowObjects(self, client_id, flow_id, cursor=None):
    """Reads flows that were started by a given flow from the database."""
    query = ("SELECT " + self.FLOW_DB_FIELDS +
             "FROM flows WHERE client_id=%s AND parent_flow_id=%s")
    cursor.execute(query, [
        mysql_utils.ClientIDToInt(client_id),
        mysql_utils.FlowIDToInt(flow_id)
    ])
    return [self._FlowObjectFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction()
  def ReadFlowForProcessing(self,
                            client_id,
                            flow_id,
                            processing_time,
                            cursor=None):
    """Marks a flow as being processed on this worker and returns it."""
    query = ("SELECT " + self.FLOW_DB_FIELDS +
             "FROM flows WHERE client_id=%s AND flow_id=%s")
    cursor.execute(query, [
        mysql_utils.ClientIDToInt(client_id),
        mysql_utils.FlowIDToInt(flow_id)
    ])
    response = cursor.fetchall()
    if not response:
      raise db.UnknownFlowError(client_id, flow_id)

    row, = response
    rdf_flow = self._FlowObjectFromRow(row)

    now = rdfvalue.RDFDatetime.Now()
    if rdf_flow.processing_on and rdf_flow.processing_deadline > now:
      raise ValueError("Flow %s on client %s is already being processed." %
                       (client_id, flow_id))
    update_query = ("UPDATE flows SET processing_on=%s, processing_since=%s, "
                    "processing_deadline=%s WHERE client_id=%s and flow_id=%s")
    processing_deadline = now + processing_time
    process_id_string = utils.ProcessIdString()

    args = [
        process_id_string,
        mysql_utils.RDFDatetimeToMysqlString(now),
        mysql_utils.RDFDatetimeToMysqlString(processing_deadline),
        mysql_utils.ClientIDToInt(client_id),
        mysql_utils.FlowIDToInt(flow_id)
    ]
    cursor.execute(update_query, args)

    # This needs to happen after we are sure that the write has succeeded.
    rdf_flow.processing_on = process_id_string
    rdf_flow.processing_since = now
    rdf_flow.processing_deadline = processing_deadline
    return rdf_flow

  @mysql_utils.WithTransaction()
  def UpdateFlow(self,
                 client_id,
                 flow_id,
                 flow_obj=db.Database.unchanged,
                 client_crash_info=db.Database.unchanged,
                 pending_termination=db.Database.unchanged,
                 processing_on=db.Database.unchanged,
                 processing_since=db.Database.unchanged,
                 processing_deadline=db.Database.unchanged,
                 cursor=None):
    """Updates flow objects in the database."""
    updates = []
    args = []
    if flow_obj != db.Database.unchanged:
      updates.append("flow=%s")
      args.append(flow_obj.SerializeToString())
    if client_crash_info != db.Database.unchanged:
      updates.append("client_crash_info=%s")
      args.append(client_crash_info.SerializeToString())
    if pending_termination != db.Database.unchanged:
      updates.append("pending_termination=%s")
      args.append(pending_termination.SerializeToString())
    if processing_on != db.Database.unchanged:
      updates.append("processing_on=%s")
      args.append(processing_on)
    if processing_since != db.Database.unchanged:
      updates.append("processing_since=%s")
      args.append(mysql_utils.RDFDatetimeToMysqlString(processing_since))
    if processing_deadline != db.Database.unchanged:
      updates.append("processing_deadline=%s")
      args.append(mysql_utils.RDFDatetimeToMysqlString(processing_deadline))

    if not updates:
      return

    query = "UPDATE flows SET "
    query += ", ".join(updates)
    query += " WHERE client_id=%s AND flow_id=%s"

    args.append(mysql_utils.ClientIDToInt(client_id))
    args.append(mysql_utils.FlowIDToInt(flow_id))
    updated = cursor.execute(query, args)
    if updated == 0:
      raise db.UnknownFlowError(client_id, flow_id)

  @mysql_utils.WithTransaction()
  def UpdateFlows(self,
                  client_id_flow_id_pairs,
                  pending_termination=db.Database.unchanged,
                  cursor=None):
    """Updates flow objects in the database."""

    if pending_termination == db.Database.unchanged:
      return

    serialized_termination = pending_termination.SerializeToString()
    query = "UPDATE flows SET pending_termination=%s WHERE "
    args = [serialized_termination]
    for index, (client_id, flow_id) in enumerate(client_id_flow_id_pairs):
      query += ("" if index == 0 else " OR ") + " client_id=%s AND flow_id=%s"
      args.extend([
          mysql_utils.ClientIDToInt(client_id),
          mysql_utils.FlowIDToInt(flow_id)
      ])
    cursor.execute(query, args)

  def _WriteFlowProcessingRequests(self, requests, cursor):
    """Returns a (query, args) tuple that inserts the given requests."""
    timestamp = rdfvalue.RDFDatetime.Now()
    timestamp_str = mysql_utils.RDFDatetimeToMysqlString(timestamp)

    templates = []
    args = []
    for req in requests:
      templates.append("(%s, %s, %s, %s, %s)")
      req = req.Copy()
      req.timestamp = timestamp
      args.append(mysql_utils.ClientIDToInt(req.client_id))
      args.append(mysql_utils.FlowIDToInt(req.flow_id))
      args.append(timestamp_str)
      args.append(req.SerializeToString())
      if req.delivery_time:
        args.append(mysql_utils.RDFDatetimeToMysqlString(req.delivery_time))
      else:
        args.append(None)

    query = ("INSERT INTO flow_processing_requests "
             "(client_id, flow_id, timestamp, request, delivery_time) VALUES ")
    query += ", ".join(templates)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction()
  def WriteFlowRequests(self, requests, cursor=None):
    """Writes a list of flow requests to the database."""
    args = []
    templates = []
    flow_keys = []
    needs_processing = {}
    now_str = mysql_utils.RDFDatetimeToMysqlString(rdfvalue.RDFDatetime.Now())
    for r in requests:
      if r.needs_processing:
        needs_processing.setdefault((r.client_id, r.flow_id),
                                    []).append(r.request_id)

      flow_keys.append((r.client_id, r.flow_id))
      templates.append("(%s, %s, %s, %s, %s, %s)")
      args.extend([
          mysql_utils.ClientIDToInt(r.client_id),
          mysql_utils.FlowIDToInt(r.flow_id), r.request_id, r.needs_processing,
          r.SerializeToString(), now_str
      ])

    if needs_processing:
      flow_processing_requests = []
      nr_conditions = []
      nr_args = []
      for client_id, flow_id in needs_processing:
        nr_conditions.append("(client_id=%s AND flow_id=%s)")
        nr_args.append(mysql_utils.ClientIDToInt(client_id))
        nr_args.append(mysql_utils.FlowIDToInt(flow_id))

      nr_query = ("SELECT client_id, flow_id, next_request_to_process "
                  "FROM flows WHERE ")
      nr_query += " OR ".join(nr_conditions)

      cursor.execute(nr_query, nr_args)

      db_result = cursor.fetchall()
      for client_id_int, flow_id_int, next_request_to_process in db_result:
        client_id = mysql_utils.IntToClientID(client_id_int)
        flow_id = mysql_utils.IntToFlowID(flow_id_int)
        if next_request_to_process in needs_processing[(client_id, flow_id)]:
          flow_processing_requests.append(
              rdf_flows.FlowProcessingRequest(
                  client_id=client_id, flow_id=flow_id))

      if flow_processing_requests:
        self._WriteFlowProcessingRequests(flow_processing_requests, cursor)

    query = ("INSERT INTO flow_requests "
             "(client_id, flow_id, request_id, needs_processing, request, "
             "timestamp) VALUES ")
    query += ", ".join(templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(flow_keys, cause=e)

  def _ReadCurrentFlowInfo(self, responses, currently_available_requests,
                           next_request_by_flow, responses_expected_by_request,
                           current_responses_by_request, cursor):
    """Reads stored data for flows we want to modify."""
    flow_conditions = []
    flow_args = []
    req_conditions = []
    req_args = []
    for r in responses:
      flow_conditions.append("(client_id=%s AND flow_id=%s)")
      flow_args.append(mysql_utils.ClientIDToInt(r.client_id))
      flow_args.append(mysql_utils.FlowIDToInt(r.flow_id))

      req_conditions.append("(client_id=%s AND flow_id=%s AND request_id=%s)")
      req_args.append(mysql_utils.ClientIDToInt(r.client_id))
      req_args.append(mysql_utils.FlowIDToInt(r.flow_id))
      req_args.append(r.request_id)

    flow_query = ("SELECT client_id, flow_id, next_request_to_process "
                  "FROM flows WHERE ")
    flow_query += " OR ".join(flow_conditions)

    req_query = ("SELECT client_id, flow_id, request_id, responses_expected "
                 "FROM flow_requests WHERE ")
    req_query += " OR ".join(req_conditions)

    res_query = ("SELECT client_id, flow_id, request_id, response_id "
                 "FROM flow_responses WHERE ")
    res_query += " OR ".join(req_conditions)

    cursor.execute(flow_query, flow_args)

    for row in cursor.fetchall():
      client_id_int, flow_id_int, next_request_to_process = row
      client_id = mysql_utils.IntToClientID(client_id_int)
      flow_id = mysql_utils.IntToFlowID(flow_id_int)
      next_request_by_flow[(client_id, flow_id)] = next_request_to_process

    cursor.execute(req_query, req_args)

    for row in cursor.fetchall():
      client_id_int, flow_id_int, request_id, responses_expected = row
      client_id = mysql_utils.IntToClientID(client_id_int)
      flow_id = mysql_utils.IntToFlowID(flow_id_int)
      request_key = (client_id, flow_id, request_id)
      currently_available_requests.add(request_key)
      if responses_expected:
        responses_expected_by_request[request_key] = responses_expected

    cursor.execute(res_query, req_args)

    for row in cursor.fetchall():
      client_id_int, flow_id_int, request_id, response_id = row
      client_id = mysql_utils.IntToClientID(client_id_int)
      flow_id = mysql_utils.IntToFlowID(flow_id_int)
      request_key = (client_id, flow_id, request_id)
      current_responses_by_request.setdefault(request_key,
                                              set()).add(response_id)

  def _WriteResponses(self, responses, timestamp_str, cursor):
    """Builds the writes to store the given responses in the db."""

    query = ("INSERT IGNORE INTO flow_responses "
             "(client_id, flow_id, request_id, response_id, "
             "response, status, iterator, timestamp) VALUES ")

    templates = []
    args = []
    for r in responses:
      templates.append("(%s, %s, %s, %s, %s, %s, %s, %s)")
      client_id_int = mysql_utils.ClientIDToInt(r.client_id)
      flow_id_int = mysql_utils.FlowIDToInt(r.flow_id)

      args.append(client_id_int)
      args.append(flow_id_int)
      args.append(r.request_id)
      args.append(r.response_id)
      if isinstance(r, rdf_flow_objects.FlowResponse):
        args.append(r.SerializeToString())
        args.append("")
        args.append("")
      elif isinstance(r, rdf_flow_objects.FlowStatus):
        args.append("")
        args.append(r.SerializeToString())
        args.append("")
      elif isinstance(r, rdf_flow_objects.FlowIterator):
        args.append("")
        args.append("")
        args.append(r.SerializeToString())
      else:
        # This can't really happen due to db api type checking.
        raise ValueError("Got unexpected response type: %s %s" % (type(r), r))
      args.append(timestamp_str)

    query += ",".join(templates)
    cursor.execute(query, args)

  def _UpdateExpected(self, requests, value_dict, cursor):
    """Updates requests that have their ResponsesExpected set."""
    for client_id, flow_id, request_id in requests:
      query = ("UPDATE flow_requests SET responses_expected=%s "
               "WHERE client_id=%s AND flow_id=%s AND request_id=%s")
      args = [
          value_dict[(client_id, flow_id, request_id)],
          mysql_utils.ClientIDToInt(client_id),
          mysql_utils.FlowIDToInt(flow_id), request_id
      ]
      cursor.execute(query, args)

  def _UpdateNeedsProcessing(self, requests, cursor):
    """Updates requests that have their NeedsProcessing flag set."""
    query = "UPDATE flow_requests SET needs_processing=TRUE WHERE"
    conditions = []
    args = []
    for client_id, flow_id, request_id in requests:
      conditions.append("(client_id=%s AND flow_id=%s AND request_id=%s)")
      args.append(mysql_utils.ClientIDToInt(client_id))
      args.append(mysql_utils.FlowIDToInt(flow_id))
      args.append(request_id)
    query += " OR ".join(conditions)
    cursor.execute(query, args)

  def _UpdateCombined(self, requests, value_dict, cursor):
    """Updates requests that have both fields changes."""
    for client_id, flow_id, request_id in requests:
      query = ("UPDATE flow_requests SET responses_expected=%s, "
               "needs_processing=TRUE "
               "WHERE client_id=%s AND flow_id=%s AND request_id=%s")
      args = [
          value_dict[(client_id, flow_id, request_id)],
          mysql_utils.ClientIDToInt(client_id),
          mysql_utils.FlowIDToInt(flow_id), request_id
      ]
      cursor.execute(query, args)

  def _UpdateRequests(self, needs_processing_update, needs_expected_update,
                      cursor):
    """Updates for a number of requests."""
    needs_expected_set = set(needs_expected_update)

    expected_only = needs_expected_set - needs_processing_update
    if expected_only:
      self._UpdateExpected(expected_only, needs_expected_update, cursor)

    processing_only = needs_processing_update - needs_expected_set
    if processing_only:
      self._UpdateNeedsProcessing(processing_only, cursor)

    combined_update = needs_expected_set & needs_processing_update
    if combined_update:
      self._UpdateCombined(combined_update, needs_expected_update, cursor)

  def _DeleteClientMessages(self, to_delete, cursor):
    """Builds deletes for client messages."""
    query = "DELETE FROM client_messages WHERE "
    conditions = []
    args = []

    for client_id, task_id in to_delete:
      conditions.append("(client_id=%s AND message_id=%s)")
      args.append(mysql_utils.ClientIDToInt(client_id))
      args.append(task_id)

    query += " OR ".join(conditions)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction()
  def WriteFlowResponses(self, responses, cursor=None):
    """Writes a list of flow responses to the database."""

    if not responses:
      return

    # In addition to just writing responses, this function needs to also

    # - Update the expected nr of response for each request that received a
    #   status.
    # - Set the needs_processing flag for all requests that now have all
    #   responses.
    # - Send FlowProcessingRequests for all flows that are waiting on a request
    #   whose needs_processing flag was just set.

    # To achieve this, we need to get the next request each flow is waiting for.
    next_request_by_flow = {}

    # And the number of responses each affected request is waiting for (if
    # available).
    responses_expected_by_request = {}

    # As well as the ids of the currently available responses for each request.
    current_responses_by_request = {}

    # We also store all requests we have in the db so we can discard responses
    # for unknown requests right away.
    currently_available_requests = set()

    self._ReadCurrentFlowInfo(
        responses, currently_available_requests, next_request_by_flow,
        responses_expected_by_request, current_responses_by_request, cursor)

    # For some requests we will need to update the number of expected responses.
    needs_expected_update = {}

    # For some we will need to update the needs_processing flag.
    needs_processing_update = set()

    # Some completed requests will trigger a flow processing request, we collect
    # them in:
    flow_processing_requests = []

    task_ids_by_request = {}

    for r in responses:
      request_key = (r.client_id, r.flow_id, r.request_id)

      try:
        # If this is a response coming from a client, a task_id will be set. We
        # store it in case the request is complete and we can remove the client
        # messages.
        task_ids_by_request[request_key] = r.task_id
      except AttributeError:
        pass

      if not isinstance(r, rdf_flow_objects.FlowStatus):
        continue

      current = responses_expected_by_request.get(request_key)
      if current:
        logging.error("Got duplicate status message for request %s/%s/%d",
                      r.client_id, r.flow_id, r.request_id)
        # If there is already responses_expected information, we need to make
        # sure the current status doesn't disagree.
        if current != r.response_id:
          raise ValueError(
              "Got conflicting status information for request %s: %s" %
              (request_key, r))
      else:
        needs_expected_update[request_key] = r.response_id

      responses_expected_by_request[request_key] = r.response_id

    responses_to_write = []
    client_messages_to_delete = []
    for r in responses:
      request_key = (r.client_id, r.flow_id, r.request_id)

      if request_key not in currently_available_requests:
        logging.info("Dropping response for unknown request %s/%s/%d",
                     r.client_id, r.flow_id, r.request_id)
        continue

      responses_to_write.append(r)

      current_responses = current_responses_by_request.setdefault(
          request_key, set())
      if r.response_id in current_responses:
        # We have this response already, nothing further to do.
        continue

      current_responses.add(r.response_id)
      expected_responses = responses_expected_by_request.get(request_key, 0)
      if len(current_responses) == expected_responses:
        # This response was the one that was missing, time to set the
        # needs_processing flag.
        needs_processing_update.add(request_key)
        if r.request_id == next_request_by_flow[(r.client_id, r.flow_id)]:
          # The request that is now ready for processing was also the one the
          # flow was waiting for.
          req = rdf_flows.FlowProcessingRequest(
              client_id=r.client_id, flow_id=r.flow_id)
          flow_processing_requests.append(req)

        # Since this request is now complete, we can remove the corresponding
        # client messages if there are any.
        task_id = task_ids_by_request.get(request_key, None)
        if task_id is not None:
          client_messages_to_delete.append((r.client_id, task_id))

    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToMysqlString(now)

    if responses_to_write:
      self._WriteResponses(responses_to_write, now_str, cursor)

    self._UpdateRequests(needs_processing_update, needs_expected_update, cursor)

    if client_messages_to_delete:
      self._DeleteClientMessages(client_messages_to_delete, cursor)

    if flow_processing_requests:
      self._WriteFlowProcessingRequests(flow_processing_requests, cursor)

  @mysql_utils.WithTransaction()
  def DeleteFlowRequests(self, requests, cursor=None):
    """Deletes a list of flow requests from the database."""
    if not requests:
      return

    conditions = []
    args = []
    for r in requests:
      conditions.append("(client_id=%s AND flow_id=%s AND request_id=%s)")
      args.append(mysql_utils.ClientIDToInt(r.client_id))
      args.append(mysql_utils.FlowIDToInt(r.flow_id))
      args.append(r.request_id)

    req_query = "DELETE FROM flow_requests WHERE " + " OR ".join(conditions)
    res_query = "DELETE FROM flow_responses WHERE " + " OR ".join(conditions)

    cursor.execute(res_query, args)
    cursor.execute(req_query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllFlowRequestsAndResponses(self, client_id, flow_id, cursor=None):
    """Reads all requests and responses for a given flow from the database."""
    query = ("SELECT request, needs_processing, responses_expected, timestamp "
             "FROM flow_requests WHERE client_id=%s AND flow_id=%s")

    args = [
        mysql_utils.ClientIDToInt(client_id),
        mysql_utils.FlowIDToInt(flow_id)
    ]
    cursor.execute(query, args)

    requests = []
    for req, needs_processing, resp_expected, ts in cursor.fetchall():
      request = rdf_flow_objects.FlowRequest.FromSerializedString(req)
      request.needs_processing = needs_processing
      request.nr_responses_expected = resp_expected
      request.timestamp = mysql_utils.MysqlToRDFDatetime(ts)
      requests.append(request)

    query = ("SELECT response, status, iterator, timestamp "
             "FROM flow_responses WHERE client_id=%s AND flow_id=%s")
    cursor.execute(query, args)

    responses = {}
    for res, status, iterator, ts in cursor.fetchall():
      if status:
        response = rdf_flow_objects.FlowStatus.FromSerializedString(status)
      elif iterator:
        response = rdf_flow_objects.FlowIterator.FromSerializedString(iterator)
      else:
        response = rdf_flow_objects.FlowResponse.FromSerializedString(res)
      response.timestamp = mysql_utils.MysqlToRDFDatetime(ts)
      responses.setdefault(response.request_id,
                           {})[response.response_id] = response

    ret = []
    for req in sorted(requests, key=lambda r: r.request_id):
      ret.append((req, responses.get(req.request_id, {})))
    return ret

  @mysql_utils.WithTransaction()
  def DeleteAllFlowRequestsAndResponses(self, client_id, flow_id, cursor=None):
    """Deletes all requests and responses for a given flow from the database."""
    args = [
        mysql_utils.ClientIDToInt(client_id),
        mysql_utils.FlowIDToInt(flow_id)
    ]
    res_query = "DELETE FROM flow_responses WHERE client_id=%s AND flow_id=%s"
    cursor.execute(res_query, args)
    req_query = "DELETE FROM flow_requests WHERE client_id=%s AND flow_id=%s"
    cursor.execute(req_query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowRequestsReadyForProcessing(self,
                                         client_id,
                                         flow_id,
                                         next_needed_request,
                                         cursor=None):
    """Reads all requests for a flow that can be processed by the worker."""
    query = ("SELECT request, needs_processing, timestamp FROM flow_requests "
             "WHERE client_id=%s AND flow_id=%s")
    args = [
        mysql_utils.ClientIDToInt(client_id),
        mysql_utils.FlowIDToInt(flow_id)
    ]
    cursor.execute(query, args)

    requests = {}
    for req, needs_processing, ts in cursor.fetchall():
      if not needs_processing:
        continue

      request = rdf_flow_objects.FlowRequest.FromSerializedString(req)
      request.needs_processing = needs_processing
      request.timestamp = mysql_utils.MysqlToRDFDatetime(ts)
      requests[request.request_id] = request

    query = ("SELECT response, status, iterator, timestamp FROM flow_responses "
             "WHERE client_id=%s AND flow_id=%s")
    cursor.execute(query, args)

    responses = {}
    for res, status, iterator, ts in cursor.fetchall():
      if status:
        response = rdf_flow_objects.FlowStatus.FromSerializedString(status)
      elif iterator:
        response = rdf_flow_objects.FlowIterator.FromSerializedString(iterator)
      else:
        response = rdf_flow_objects.FlowResponse.FromSerializedString(res)
      response.timestamp = mysql_utils.MysqlToRDFDatetime(ts)
      responses.setdefault(response.request_id, []).append(response)

    res = {}
    while next_needed_request in requests:
      req = requests[next_needed_request]
      sorted_responses = sorted(
          responses.get(next_needed_request, []), key=lambda r: r.response_id)
      res[req.request_id] = (req, sorted_responses)
      next_needed_request += 1

    return res

  @mysql_utils.WithTransaction()
  def ReturnProcessedFlow(self, flow_obj, cursor=None):
    """Returns a flow that the worker was processing to the database."""
    query = ("SELECT needs_processing FROM flow_requests "
             "WHERE client_id=%s AND flow_id=%s AND request_id=%s")
    cursor.execute(query, [
        mysql_utils.ClientIDToInt(flow_obj.client_id),
        mysql_utils.FlowIDToInt(flow_obj.flow_id),
        flow_obj.next_request_to_process
    ])
    for row in cursor.fetchall():
      needs_processing = row[0]
      if needs_processing:
        return False

    update_query = ("UPDATE flows SET flow=%s, processing_on=%s, "
                    "processing_since=%s, processing_deadline=%s, "
                    "next_request_to_process=%s, last_update=%s "
                    "WHERE client_id=%s AND flow_id=%s")
    clone = flow_obj.Copy()
    clone.processing_on = None
    clone.processing_since = None
    clone.processing_deadline = None
    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToMysqlString(now)
    args = [
        clone.SerializeToString(), None, None, None,
        flow_obj.next_request_to_process, now_str,
        mysql_utils.ClientIDToInt(flow_obj.client_id),
        mysql_utils.FlowIDToInt(flow_obj.flow_id)
    ]
    cursor.execute(update_query, args)

    # This needs to happen after we are sure that the write has succeeded.
    flow_obj.processing_on = None
    flow_obj.processing_since = None
    flow_obj.processing_deadline = None

    return True

  @mysql_utils.WithTransaction()
  def WriteFlowProcessingRequests(self, requests, cursor=None):
    """Writes a list of flow processing requests to the database."""
    self._WriteFlowProcessingRequests(requests, cursor)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowProcessingRequests(self, cursor=None):
    """Reads all flow processing requests from the database."""
    query = "SELECT request, timestamp FROM flow_processing_requests"
    cursor.execute(query)

    res = []
    for serialized_request, ts in cursor.fetchall():
      req = rdf_flows.FlowProcessingRequest.FromSerializedString(
          serialized_request)
      req.timestamp = mysql_utils.MysqlToRDFDatetime(ts)
      res.append(req)
    return res

  @mysql_utils.WithTransaction()
  def AckFlowProcessingRequests(self, requests, cursor=None):
    """Deletes a list of flow processing requests from the database."""
    if not requests:
      return

    query = "DELETE FROM flow_processing_requests WHERE "

    conditions = []
    args = []
    for r in requests:
      conditions.append("(client_id=%s AND flow_id=%s AND timestamp=%s)")
      args.append(mysql_utils.ClientIDToInt(r.client_id))
      args.append(mysql_utils.FlowIDToInt(r.flow_id))
      args.append(mysql_utils.RDFDatetimeToMysqlString(r.timestamp))

    query += " OR ".join(conditions)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction()
  def DeleteAllFlowProcessingRequests(self, cursor=None):
    """Deletes all flow processing requests from the database."""
    query = "DELETE FROM flow_processing_requests WHERE true"
    cursor.execute(query)

  @mysql_utils.WithTransaction()
  def _LeaseFlowProcessingReqests(self, cursor=None):
    """Leases a number of flow processing requests."""
    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToMysqlString(now)

    expiry = now + rdfvalue.Duration("10m")
    expiry_str = mysql_utils.RDFDatetimeToMysqlString(expiry)

    query = ("UPDATE flow_processing_requests "
             "SET leased_until=%s, leased_by=%s "
             "WHERE (delivery_time IS NULL OR delivery_time <= %s) AND "
             "(leased_until IS NULL OR leased_until < %s) "
             "LIMIT %s")

    id_str = utils.ProcessIdString()
    args = (expiry_str, id_str, now_str, now_str, 50)
    updated = cursor.execute(query, args)

    if updated == 0:
      return []

    cursor.execute(
        "SELECT timestamp, request FROM flow_processing_requests "
        "WHERE leased_by=%s AND leased_until=%s LIMIT %s",
        (id_str, expiry_str, updated))
    res = []
    for timestamp, request in cursor.fetchall():
      req = rdf_flows.FlowProcessingRequest.FromSerializedString(request)
      req.timestamp = mysql_utils.MysqlToRDFDatetime(timestamp)
      req.leased_until = expiry
      req.leased_by = id_str
      res.append(req)

    return res

  def _FlowProcessingRequestHandlerLoop(self, handler):
    """The main loop for the flow processing request queue."""
    while not self.flow_processing_request_handler_stop:
      try:
        msgs = self._LeaseFlowProcessingReqests()
        if msgs:
          for m in msgs:
            self.flow_processing_request_handler_pool.AddTask(
                target=handler, args=(m,))
        else:
          time.sleep(5)

      except Exception as e:  # pylint: disable=broad-except
        logging.exception("_FlowProcessingRequestHandlerLoop raised %s.", e)
        break

  def RegisterFlowProcessingHandler(self, handler):
    """Registers a handler to receive flow processing messages."""
    self.UnregisterMessageHandler()

    if handler:
      self.flow_processing_request_handler_stop = False
      self.flow_processing_request_handler_thread = threading.Thread(
          name="flow_processing_request_handler",
          target=self._FlowProcessingRequestHandlerLoop,
          args=(handler,))
      self.flow_processing_request_handler_thread.daemon = True
      self.flow_processing_request_handler_thread.start()

  def UnregisterFlowProcessingHandler(self, timeout=None):
    """Unregisters any registered flow processing handler."""
    if self.flow_processing_request_handler_thread:
      self.flow_processing_request_handler_stop = True
      self.flow_processing_request_handler_thread.join(timeout)
      if self.flow_processing_request_handler_thread.isAlive():
        raise RuntimeError("Flow processing handler did not join in time.")
      self.flow_processing_request_handler_thread = None

  @mysql_utils.WithTransaction()
  def WriteFlowResults(self, client_id, flow_id, results, cursor=None):
    """Writes flow results for a given flow."""

  @mysql_utils.WithTransaction()
  def ReadFlowResults(self,
                      client_id,
                      flow_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None,
                      cursor=None):
    """Reads flow results of a given flow using given query options."""

  @mysql_utils.WithTransaction()
  def CountFlowResults(self,
                       client_id,
                       flow_id,
                       with_tag=None,
                       with_type=None,
                       cursor=None):
    """Counts flow results of a given flow using given query options."""

  @mysql_utils.WithTransaction()
  def WriteFlowLogEntries(self, client_id, flow_id, entries, cursor=None):
    """Writes flow log entries for a given flow."""

  @mysql_utils.WithTransaction()
  def ReadFlowLogEntries(self,
                         client_id,
                         flow_id,
                         offset,
                         count,
                         with_substring=None,
                         cursor=None):
    """Reads flow log entries of a given flow using given query options."""

  @mysql_utils.WithTransaction()
  def CountFlowLogEntries(self, client_id, flow_id, cursor=None):
    """Returns number of flow log entries of a given flow."""
