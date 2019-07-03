#!/usr/bin/env python
"""The MySQL database methods for flow handling."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import logging
import threading
import time

from future.utils import iteritems
import MySQLdb
from typing import List, Optional, Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import compatibility
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBFlowMixin(object):
  """MySQLDB mixin for flow handling."""

  @mysql_utils.WithTransaction()
  def WriteMessageHandlerRequests(self, requests, cursor=None):
    """Writes a list of message handler requests to the database."""
    query = ("INSERT IGNORE INTO message_handler_requests "
             "(handlername, request_id, request) VALUES ")

    value_templates = []
    args = []
    for r in requests:
      args.extend([r.handler_name, r.request_id, r.SerializeToString()])
      value_templates.append("(%s, %s, %s)")

    query += ",".join(value_templates)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadMessageHandlerRequests(self, cursor=None):
    """Reads all message handler requests from the database."""

    query = ("SELECT UNIX_TIMESTAMP(timestamp), request,"
             "       UNIX_TIMESTAMP(leased_until), leased_by "
             "FROM message_handler_requests "
             "ORDER BY timestamp DESC")

    cursor.execute(query)

    res = []
    for timestamp, request, leased_until, leased_by in cursor.fetchall():
      req = rdf_objects.MessageHandlerRequest.FromSerializedString(request)
      req.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
      req.leased_by = leased_by
      req.leased_until = mysql_utils.TimestampToRDFDatetime(leased_until)
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

  _MESSAGE_HANDLER_POLL_TIME_SECS = 5

  def _MessageHandlerLoop(self, handler, lease_time, limit):
    while not self.handler_stop:
      try:
        msgs = self._LeaseMessageHandlerRequests(lease_time, limit)
        if msgs:
          handler(msgs)
        else:
          time.sleep(self._MESSAGE_HANDLER_POLL_TIME_SECS)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("_LeaseMessageHandlerRequests raised %s.", e)

  @mysql_utils.WithTransaction()
  def _LeaseMessageHandlerRequests(self, lease_time, limit, cursor=None):
    """Leases a number of message handler requests up to the indicated limit."""

    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToTimestamp(now)

    expiry = now + lease_time
    expiry_str = mysql_utils.RDFDatetimeToTimestamp(expiry)

    query = ("UPDATE message_handler_requests "
             "SET leased_until=FROM_UNIXTIME(%s), leased_by=%s "
             "WHERE leased_until IS NULL OR leased_until < FROM_UNIXTIME(%s) "
             "LIMIT %s")

    id_str = utils.ProcessIdString()
    args = (expiry_str, id_str, now_str, limit)
    updated = cursor.execute(query, args)

    if updated == 0:
      return []

    cursor.execute(
        "SELECT UNIX_TIMESTAMP(timestamp), request "
        "FROM message_handler_requests "
        "WHERE leased_by=%s AND leased_until=FROM_UNIXTIME(%s) LIMIT %s",
        (id_str, expiry_str, updated))
    res = []
    for timestamp, request in cursor.fetchall():
      req = rdf_objects.MessageHandlerRequest.FromSerializedString(request)
      req.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
      req.leased_until = expiry
      req.leased_by = id_str
      res.append(req)

    return res

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllClientActionRequests(self, client_id, cursor=None):
    """Reads all client messages available for a given client_id."""

    query = ("SELECT request, UNIX_TIMESTAMP(leased_until), leased_by, "
             "leased_count "
             "FROM client_action_requests "
             "WHERE client_id = %s")

    cursor.execute(query, [db_utils.ClientIDToInt(client_id)])

    ret = []
    for req, leased_until, leased_by, leased_count in cursor.fetchall():
      request = rdf_flows.ClientActionRequest.FromSerializedString(req)
      if leased_until is not None:
        request.leased_by = leased_by
        request.leased_until = mysql_utils.TimestampToRDFDatetime(leased_until)
      else:
        request.leased_by = None
        request.leased_until = None
      request.ttl = db.Database.CLIENT_MESSAGES_TTL - leased_count
      ret.append(request)

    return sorted(ret, key=lambda req: (req.flow_id, req.request_id))

  def DeleteClientActionRequests(self, requests):
    """Deletes a list of client messages from the db."""
    if not requests:
      return

    to_delete = []
    for r in requests:
      to_delete.append((r.client_id, r.flow_id, r.request_id))

    if len(set(to_delete)) != len(to_delete):
      raise ValueError(
          "Received multiple copies of the same message to delete.")

    self._DeleteClientActionRequest(to_delete)

  @mysql_utils.WithTransaction()
  def LeaseClientActionRequests(self,
                                client_id,
                                lease_time=None,
                                limit=None,
                                cursor=None):
    """Leases available client messages for the client with the given id."""

    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToTimestamp(now)
    expiry = now + lease_time
    expiry_str = mysql_utils.RDFDatetimeToTimestamp(expiry)
    proc_id_str = utils.ProcessIdString()
    client_id_int = db_utils.ClientIDToInt(client_id)

    query = ("UPDATE client_action_requests "
             "SET leased_until=FROM_UNIXTIME(%s), leased_by=%s, "
             "leased_count=leased_count+1 "
             "WHERE client_id=%s AND "
             "(leased_until IS NULL OR leased_until < FROM_UNIXTIME(%s)) "
             "LIMIT %s")
    args = [expiry_str, proc_id_str, client_id_int, now_str, limit]

    num_leased = cursor.execute(query, args)
    if num_leased == 0:
      return []

    query = ("SELECT request, leased_count FROM client_action_requests "
             "WHERE client_id=%s AND leased_until=FROM_UNIXTIME(%s) "
             "AND leased_by=%s")

    cursor.execute(query, [client_id_int, expiry_str, proc_id_str])

    ret = []
    expired = []
    for req, leased_count in cursor.fetchall():
      request = rdf_flows.ClientActionRequest.FromSerializedString(req)
      request.leased_by = proc_id_str
      request.leased_until = expiry
      request.ttl = db.Database.CLIENT_MESSAGES_TTL - leased_count
      # > comparison since this check happens after the lease.
      if leased_count > db.Database.CLIENT_MESSAGES_TTL:
        expired.append((request.client_id, request.flow_id, request.request_id))
      else:
        ret.append(request)

    if expired:
      self._DeleteClientActionRequest(expired, cursor=cursor)

    return sorted(ret, key=lambda req: (req.flow_id, req.request_id))

  @mysql_utils.WithTransaction()
  def WriteClientActionRequests(self, requests, cursor=None):
    """Writes messages that should go to the client to the db."""

    query = ("INSERT IGNORE INTO client_action_requests "
             "(client_id, flow_id, request_id, timestamp, request) "
             "VALUES %s ON DUPLICATE KEY UPDATE "
             "timestamp=VALUES(timestamp), request=VALUES(request)")
    now = mysql_utils.RDFDatetimeToTimestamp(rdfvalue.RDFDatetime.Now())

    value_templates = []
    args = []
    for r in requests:
      args.extend([
          db_utils.ClientIDToInt(r.client_id),
          db_utils.FlowIDToInt(r.flow_id), r.request_id, now,
          r.SerializeToString()
      ])
      value_templates.append("(%s, %s, %s, FROM_UNIXTIME(%s), %s)")

    query %= ",".join(value_templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      request_keys = [(r.client_id, r.flow_id, r.request_id) for r in requests]
      raise db.AtLeastOneUnknownRequestError(request_keys=request_keys, cause=e)

  @mysql_utils.WithTransaction()
  def WriteFlowObject(self, flow_obj, cursor=None):
    """Writes a flow object to the database."""

    query = """
    INSERT INTO flows (client_id, flow_id, long_flow_id, parent_flow_id,
                       parent_hunt_id, flow, flow_state,
                       next_request_to_process, pending_termination, timestamp,
                       network_bytes_sent, user_cpu_time_used_micros,
                       system_cpu_time_used_micros, num_replies_sent, last_update)
    VALUES (%(client_id)s, %(flow_id)s, %(long_flow_id)s, %(parent_flow_id)s,
            %(parent_hunt_id)s, %(flow)s, %(flow_state)s,
            %(next_request_to_process)s, %(pending_termination)s,
            FROM_UNIXTIME(%(timestamp)s),
            %(network_bytes_sent)s, %(user_cpu_time_used_micros)s,
            %(system_cpu_time_used_micros)s, %(num_replies_sent)s, NOW(6))
    ON DUPLICATE KEY UPDATE
        flow=VALUES(flow),
        flow_state=VALUES(flow_state),
        next_request_to_process=VALUES(next_request_to_process),
        last_update=VALUES(last_update)
    """

    user_cpu_time_used_micros = db_utils.SecondsToMicros(
        flow_obj.cpu_time_used.user_cpu_time)
    system_cpu_time_used_micros = db_utils.SecondsToMicros(
        flow_obj.cpu_time_used.system_cpu_time)

    args = {
        "client_id": db_utils.ClientIDToInt(flow_obj.client_id),
        "flow_id": db_utils.FlowIDToInt(flow_obj.flow_id),
        "long_flow_id": flow_obj.long_flow_id,
        "flow": flow_obj.SerializeToString(),
        "flow_state": int(flow_obj.flow_state),
        "next_request_to_process": flow_obj.next_request_to_process,
        "timestamp": mysql_utils.RDFDatetimeToTimestamp(flow_obj.create_time),
        "network_bytes_sent": flow_obj.network_bytes_sent,
        "num_replies_sent": flow_obj.num_replies_sent,
        "user_cpu_time_used_micros": user_cpu_time_used_micros,
        "system_cpu_time_used_micros": system_cpu_time_used_micros,
    }

    if flow_obj.parent_flow_id:
      args["parent_flow_id"] = db_utils.FlowIDToInt(flow_obj.parent_flow_id)
    else:
      args["parent_flow_id"] = None

    if flow_obj.parent_hunt_id:
      args["parent_hunt_id"] = db_utils.HuntIDToInt(flow_obj.parent_hunt_id)
    else:
      args["parent_hunt_id"] = None

    if flow_obj.HasField("pending_termination"):
      serialized_termination = flow_obj.pending_termination.SerializeToString()
      args["pending_termination"] = serialized_termination
    else:
      args["pending_termination"] = None

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.UnknownClientError(flow_obj.client_id, cause=e)

  def _FlowObjectFromRow(self, row):
    """Generates a flow object from a database row."""

    flow, fs, cci, pt, nr, pd, po, ps, uct, sct, nbs, nrs, ts, lut = row

    flow_obj = rdf_flow_objects.Flow.FromSerializedString(flow)
    if fs not in [None, rdf_flow_objects.Flow.FlowState.UNSET]:
      flow_obj.flow_state = fs
    if cci is not None:
      cc_cls = rdf_client.ClientCrash
      flow_obj.client_crash_info = cc_cls.FromSerializedString(cci)
    if pt is not None:
      pt_cls = rdf_flow_objects.PendingFlowTermination
      flow_obj.pending_termination = pt_cls.FromSerializedString(pt)
    if nr:
      flow_obj.next_request_to_process = nr
    if pd is not None:
      flow_obj.processing_deadline = mysql_utils.TimestampToRDFDatetime(pd)
    if po is not None:
      flow_obj.processing_on = po
    if ps is not None:
      flow_obj.processing_since = mysql_utils.TimestampToRDFDatetime(ps)
    flow_obj.cpu_time_used.user_cpu_time = db_utils.MicrosToSeconds(uct)
    flow_obj.cpu_time_used.system_cpu_time = db_utils.MicrosToSeconds(sct)
    flow_obj.network_bytes_sent = nbs
    if nrs:
      flow_obj.num_replies_sent = nrs
    flow_obj.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
    flow_obj.last_update_time = mysql_utils.TimestampToRDFDatetime(lut)

    return flow_obj

  FLOW_DB_FIELDS = ("flow, "
                    "flow_state, "
                    "client_crash_info, "
                    "pending_termination, "
                    "next_request_to_process, "
                    "UNIX_TIMESTAMP(processing_deadline), "
                    "processing_on, "
                    "UNIX_TIMESTAMP(processing_since), "
                    "user_cpu_time_used_micros, "
                    "system_cpu_time_used_micros, "
                    "network_bytes_sent, "
                    "num_replies_sent, "
                    "UNIX_TIMESTAMP(timestamp), "
                    "UNIX_TIMESTAMP(last_update) ")

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowObject(self, client_id, flow_id, cursor=None):
    """Reads a flow object from the database."""
    query = ("SELECT " + self.FLOW_DB_FIELDS +
             "FROM flows WHERE client_id=%s AND flow_id=%s")
    cursor.execute(
        query,
        [db_utils.ClientIDToInt(client_id),
         db_utils.FlowIDToInt(flow_id)])
    result = cursor.fetchall()
    if not result:
      raise db.UnknownFlowError(client_id, flow_id)
    row, = result
    return self._FlowObjectFromRow(row)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllFlowObjects(self,
                         client_id = None,
                         min_create_time = None,
                         max_create_time = None,
                         include_child_flows = True,
                         cursor=None):
    """Returns all flow objects."""
    conditions = []
    args = []

    if client_id is not None:
      conditions.append("client_id = %s")
      args.append(db_utils.ClientIDToInt(client_id))

    if min_create_time is not None:
      conditions.append("timestamp >= FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(min_create_time))

    if max_create_time is not None:
      conditions.append("timestamp <= FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(max_create_time))

    if not include_child_flows:
      conditions.append("parent_flow_id IS NULL")

    query = "SELECT {} FROM flows".format(self.FLOW_DB_FIELDS)
    if conditions:
      query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, args)
    return [self._FlowObjectFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction(readonly=True)
  def ReadChildFlowObjects(self, client_id, flow_id, cursor=None):
    """Reads flows that were started by a given flow from the database."""
    query = ("SELECT " + self.FLOW_DB_FIELDS +
             "FROM flows WHERE client_id=%s AND parent_flow_id=%s")
    cursor.execute(
        query,
        [db_utils.ClientIDToInt(client_id),
         db_utils.FlowIDToInt(flow_id)])
    return [self._FlowObjectFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction()
  def LeaseFlowForProcessing(self,
                             client_id,
                             flow_id,
                             processing_time,
                             cursor=None):
    """Marks a flow as being processed on this worker and returns it."""
    query = ("SELECT " + self.FLOW_DB_FIELDS +
             "FROM flows WHERE client_id=%s AND flow_id=%s")
    cursor.execute(
        query,
        [db_utils.ClientIDToInt(client_id),
         db_utils.FlowIDToInt(flow_id)])
    response = cursor.fetchall()
    if not response:
      raise db.UnknownFlowError(client_id, flow_id)

    row, = response
    rdf_flow = self._FlowObjectFromRow(row)

    now = rdfvalue.RDFDatetime.Now()
    if rdf_flow.processing_on and rdf_flow.processing_deadline > now:
      raise ValueError("Flow %s on client %s is already being processed." %
                       (client_id, flow_id))

    if (rdf_flow.parent_hunt_id is not None and
        # TODO(user): remove the check for a legacy hunt prefix as soon as
        # AFF4 is gone.
        not rdf_flow.parent_hunt_id.startswith("H:")):

      query = "SELECT hunt_state FROM hunts WHERE hunt_id=%s"
      args = [db_utils.HuntIDToInt(rdf_flow.parent_hunt_id)]
      rows_found = cursor.execute(query, args)
      if rows_found == 1:
        hunt_state, = cursor.fetchone()
        if (hunt_state is not None and
            not rdf_hunt_objects.IsHuntSuitableForFlowProcessing(hunt_state)):
          raise db.ParentHuntIsNotRunningError(client_id, flow_id,
                                               rdf_flow.parent_hunt_id,
                                               hunt_state)

    update_query = ("UPDATE flows SET "
                    "processing_on=%s, "
                    "processing_since=FROM_UNIXTIME(%s), "
                    "processing_deadline=FROM_UNIXTIME(%s) "
                    "WHERE client_id=%s and flow_id=%s")
    processing_deadline = now + processing_time
    process_id_string = utils.ProcessIdString()

    args = [
        process_id_string,
        mysql_utils.RDFDatetimeToTimestamp(now),
        mysql_utils.RDFDatetimeToTimestamp(processing_deadline),
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id)
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
                 flow_state=db.Database.unchanged,
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
      updates.append("flow_state=%s")
      args.append(int(flow_obj.flow_state))
      updates.append("user_cpu_time_used_micros=%s")
      args.append(
          db_utils.SecondsToMicros(flow_obj.cpu_time_used.user_cpu_time))
      updates.append("system_cpu_time_used_micros=%s")
      args.append(
          db_utils.SecondsToMicros(flow_obj.cpu_time_used.system_cpu_time))
      updates.append("network_bytes_sent=%s")
      args.append(flow_obj.network_bytes_sent)
      updates.append("num_replies_sent=%s")
      args.append(flow_obj.num_replies_sent)

    if flow_state != db.Database.unchanged:
      updates.append("flow_state=%s")
      args.append(int(flow_state))
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
      updates.append("processing_since=FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(processing_since))
    if processing_deadline != db.Database.unchanged:
      updates.append("processing_deadline=FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(processing_deadline))

    if not updates:
      return

    query = "UPDATE flows SET last_update=NOW(6), "
    query += ", ".join(updates)
    query += " WHERE client_id=%s AND flow_id=%s"

    args.append(db_utils.ClientIDToInt(client_id))
    args.append(db_utils.FlowIDToInt(flow_id))
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
      args.extend(
          [db_utils.ClientIDToInt(client_id),
           db_utils.FlowIDToInt(flow_id)])
    cursor.execute(query, args)

  def _WriteFlowProcessingRequests(self, requests, cursor):
    """Returns a (query, args) tuple that inserts the given requests."""
    templates = []
    args = []
    for req in requests:
      templates.append("(%s, %s, %s, FROM_UNIXTIME(%s))")
      args.append(db_utils.ClientIDToInt(req.client_id))
      args.append(db_utils.FlowIDToInt(req.flow_id))
      args.append(req.SerializeToString())
      if req.delivery_time:
        args.append(mysql_utils.RDFDatetimeToTimestamp(req.delivery_time))
      else:
        args.append(None)

    query = ("INSERT INTO flow_processing_requests "
             "(client_id, flow_id, request, delivery_time) VALUES ")
    query += ", ".join(templates)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction()
  def WriteFlowRequests(self, requests, cursor=None):
    """Writes a list of flow requests to the database."""
    args = []
    templates = []
    flow_keys = []
    needs_processing = {}

    for r in requests:
      if r.needs_processing:
        needs_processing.setdefault((r.client_id, r.flow_id), []).append(r)

      flow_keys.append((r.client_id, r.flow_id))
      templates.append("(%s, %s, %s, %s, %s)")
      args.extend([
          db_utils.ClientIDToInt(r.client_id),
          db_utils.FlowIDToInt(r.flow_id), r.request_id, r.needs_processing,
          r.SerializeToString()
      ])

    if needs_processing:
      flow_processing_requests = []
      nr_conditions = []
      nr_args = []
      for client_id, flow_id in needs_processing:
        nr_conditions.append("(client_id=%s AND flow_id=%s)")
        nr_args.append(db_utils.ClientIDToInt(client_id))
        nr_args.append(db_utils.FlowIDToInt(flow_id))

      nr_query = ("SELECT client_id, flow_id, next_request_to_process "
                  "FROM flows WHERE ")
      nr_query += " OR ".join(nr_conditions)

      cursor.execute(nr_query, nr_args)

      db_result = cursor.fetchall()
      for client_id_int, flow_id_int, next_request_to_process in db_result:
        client_id = db_utils.IntToClientID(client_id_int)
        flow_id = db_utils.IntToFlowID(flow_id_int)
        candidate_requests = needs_processing.get((client_id, flow_id), [])
        for r in candidate_requests:
          if next_request_to_process == r.request_id:
            flow_processing_requests.append(
                rdf_flows.FlowProcessingRequest(
                    client_id=client_id,
                    flow_id=flow_id,
                    delivery_time=r.start_time))

      if flow_processing_requests:
        self._WriteFlowProcessingRequests(flow_processing_requests, cursor)

    query = ("INSERT INTO flow_requests "
             "(client_id, flow_id, request_id, needs_processing, request) "
             "VALUES ")
    query += ", ".join(templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(flow_keys, cause=e)

  def _WriteResponses(self, responses, cursor):
    """Builds the writes to store the given responses in the db."""

    query = ("INSERT IGNORE INTO flow_responses "
             "(client_id, flow_id, request_id, response_id, "
             "response, status, iterator, timestamp) VALUES ")

    templates = []
    args = []
    for r in responses:
      templates.append("(%s, %s, %s, %s, %s, %s, %s, NOW(6))")
      client_id_int = db_utils.ClientIDToInt(r.client_id)
      flow_id_int = db_utils.FlowIDToInt(r.flow_id)

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

    query += ",".join(templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError:
      # If we have multiple responses and one of them fails to insert, we try
      # them one by one so we don't lose any valid replies.
      if len(responses) > 1:
        for r in responses:
          self._WriteResponses([r], cursor)
      else:
        logging.warn("Response for unknown request: %s", responses[0])

  @mysql_utils.WithTransaction()
  def _DeleteClientActionRequest(self, to_delete, cursor=None):
    """Builds deletes for client messages."""
    query = "DELETE FROM client_action_requests WHERE "
    conditions = []
    args = []

    for client_id, flow_id, request_id in to_delete:
      conditions.append("(client_id=%s AND flow_id=%s AND request_id=%s)")
      args.append(db_utils.ClientIDToInt(client_id))
      args.append(db_utils.FlowIDToInt(flow_id))
      args.append(request_id)

    query += " OR ".join(conditions)
    cursor.execute(query, args)

  @mysql_utils.WithTransaction()
  def _WriteFlowResponsesAndExpectedUpdates(self, responses, cursor=None):
    """Writes a flow responses and updates flow requests expected counts."""

    self._WriteResponses(responses, cursor)

    query = """
      UPDATE flow_requests
      SET responses_expected=%(responses_expected)s
      WHERE
        client_id = %(client_id)s AND
        flow_id = %(flow_id)s AND
        request_id = %(request_id)s
    """

    for r in responses:
      # If the response is a FlowStatus, we have to update the FlowRequest with
      # the number of expected messages.
      if isinstance(r, rdf_flow_objects.FlowStatus):
        args = {
            "client_id": db_utils.ClientIDToInt(r.client_id),
            "flow_id": db_utils.FlowIDToInt(r.flow_id),
            "request_id": r.request_id,
            "responses_expected": r.response_id,
        }
        cursor.execute(query, args)

  def _ReadFlowResponseCounts(self, request_keys, cursor=None):
    """Reads counts of responses for the given requests."""

    query = """
      SELECT
        flow_requests.client_id, flow_requests.flow_id,
        flow_requests.request_id, COUNT(*)
      FROM flow_responses, flow_requests
      WHERE ({conditions}) AND
        flow_requests.client_id = flow_responses.client_id AND
        flow_requests.flow_id = flow_responses.flow_id AND
        flow_requests.request_id = flow_responses.request_id AND
        flow_requests.needs_processing = FALSE
      GROUP BY
        flow_requests.client_id,
        flow_requests.flow_id,
        flow_requests.request_id
    """

    condition_template = """
      (flow_requests.client_id=%s AND
       flow_requests.flow_id=%s AND
       flow_requests.request_id=%s)"""
    conditions = [condition_template] * len(request_keys)
    args = []
    for client_id, flow_id, request_id in request_keys:
      args.append(db_utils.ClientIDToInt(client_id))
      args.append(db_utils.FlowIDToInt(flow_id))
      args.append(request_id)

    query = query.format(conditions=" OR ".join(conditions))
    cursor.execute(query, args)
    response_counts = {}
    for (client_id_int, flow_id_int, request_id, count) in cursor.fetchall():
      request_key = (db_utils.IntToClientID(client_id_int),
                     db_utils.IntToFlowID(flow_id_int), request_id)
      response_counts[request_key] = count
    return response_counts

  def _ReadAndLockNextRequestsToProcess(self, flow_keys, cursor):
    """Reads and locks the next_request_to_process for a number of flows."""

    query = """
      SELECT client_id, flow_id, next_request_to_process
      FROM flows
      WHERE {conditions}
      FOR UPDATE
    """
    condition_template = "(client_id = %s AND flow_id = %s)"
    conditions = [condition_template] * len(flow_keys)
    query = query.format(conditions=" OR ".join(conditions))
    args = []
    for client_id, flow_id in flow_keys:
      args.append(db_utils.ClientIDToInt(client_id))
      args.append(db_utils.FlowIDToInt(flow_id))

    cursor.execute(query, args)
    next_requests = {}
    for client_id_int, flow_id_int, next_request in cursor.fetchall():
      flow_key = (db_utils.IntToClientID(client_id_int),
                  db_utils.IntToFlowID(flow_id_int))
      next_requests[flow_key] = next_request
    return next_requests

  def _ReadLockAndUpdateCompletedRequests(self, request_keys, response_counts,
                                          cursor):
    """Reads, locks, and updates completed requests."""

    condition_template = """
      (flow_requests.client_id = %s AND
       flow_requests.flow_id = %s AND
       flow_requests.request_id = %s AND
       responses_expected = %s)"""

    args = []
    conditions = []
    completed_requests = {}

    for request_key in request_keys:
      client_id, flow_id, request_id = request_key
      if request_key in response_counts:
        conditions.append(condition_template)
        args.append(db_utils.ClientIDToInt(client_id))
        args.append(db_utils.FlowIDToInt(flow_id))
        args.append(request_id)
        args.append(response_counts[request_key])

    if not args:
      return completed_requests

    query = """
      SELECT client_id, flow_id, request_id, request
      FROM flow_requests
      WHERE ({conditions}) AND NOT needs_processing
      FOR UPDATE
    """

    query = query.format(conditions=" OR ".join(conditions))
    cursor.execute(query, args)
    for client_id_int, flow_id_int, request_id, request in cursor.fetchall():
      request_key = (db_utils.IntToClientID(client_id_int),
                     db_utils.IntToFlowID(flow_id_int), request_id)
      r = rdf_flow_objects.FlowRequest.FromSerializedString(request)
      completed_requests[request_key] = r

    query = """
    UPDATE flow_requests
    SET needs_processing = TRUE
    WHERE ({conditions}) AND NOT needs_processing
    """
    query = query.format(conditions=" OR ".join(conditions))
    cursor.execute(query, args)

    return completed_requests

  @mysql_utils.WithTransaction()
  def _UpdateRequestsAndScheduleFPRs(self, responses, cursor=None):
    """Updates requests and writes FlowProcessingRequests if needed."""

    request_keys = set(
        (r.client_id, r.flow_id, r.request_id) for r in responses)
    flow_keys = set((r.client_id, r.flow_id) for r in responses)

    response_counts = self._ReadFlowResponseCounts(request_keys, cursor)

    next_requests = self._ReadAndLockNextRequestsToProcess(flow_keys, cursor)

    completed_requests = self._ReadLockAndUpdateCompletedRequests(
        request_keys, response_counts, cursor)

    if not completed_requests:
      return completed_requests

    fprs_to_write = []
    for request_key, r in iteritems(completed_requests):
      client_id, flow_id, request_id = request_key
      if next_requests[(client_id, flow_id)] == request_id:
        fprs_to_write.append(
            rdf_flows.FlowProcessingRequest(
                client_id=r.client_id,
                flow_id=r.flow_id,
                delivery_time=r.start_time))

    if fprs_to_write:
      self._WriteFlowProcessingRequests(fprs_to_write, cursor)

    return completed_requests

  @db_utils.CallLoggedAndAccounted
  def WriteFlowResponses(self, responses):
    """Writes FlowMessages and updates corresponding requests."""

    if not responses:
      return

    for batch in collection.Batch(responses, self._WRITE_ROWS_BATCH_SIZE):

      self._WriteFlowResponsesAndExpectedUpdates(batch)

      completed_requests = self._UpdateRequestsAndScheduleFPRs(batch)

      if completed_requests:
        self._DeleteClientActionRequest(completed_requests)

  @mysql_utils.WithTransaction()
  def DeleteFlowRequests(self, requests, cursor=None):
    """Deletes a list of flow requests from the database."""
    if not requests:
      return

    for batch in collection.Batch(requests, self._DELETE_ROWS_BATCH_SIZE):
      # Each iteration might delete more than BATCH_SIZE flow_responses.
      # This is acceptable, because batching should only prevent the statement
      # size from growing too large.
      conditions = []
      args = []

      for r in batch:
        conditions.append("(client_id=%s AND flow_id=%s AND request_id=%s)")
        args.append(db_utils.ClientIDToInt(r.client_id))
        args.append(db_utils.FlowIDToInt(r.flow_id))
        args.append(r.request_id)

      req_query = "DELETE FROM flow_requests WHERE " + " OR ".join(conditions)
      res_query = "DELETE FROM flow_responses WHERE " + " OR ".join(conditions)

      cursor.execute(res_query, args)
      cursor.execute(req_query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllFlowRequestsAndResponses(self, client_id, flow_id, cursor=None):
    """Reads all requests and responses for a given flow from the database."""
    query = ("SELECT request, needs_processing, responses_expected, "
             "UNIX_TIMESTAMP(timestamp) "
             "FROM flow_requests WHERE client_id=%s AND flow_id=%s")

    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]
    cursor.execute(query, args)

    requests = []
    for req, needs_processing, resp_expected, ts in cursor.fetchall():
      request = rdf_flow_objects.FlowRequest.FromSerializedString(req)
      request.needs_processing = needs_processing
      request.nr_responses_expected = resp_expected
      request.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      requests.append(request)

    query = ("SELECT response, status, iterator, UNIX_TIMESTAMP(timestamp) "
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
      response.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      responses.setdefault(response.request_id,
                           {})[response.response_id] = response

    ret = []
    for req in sorted(requests, key=lambda r: r.request_id):
      ret.append((req, responses.get(req.request_id, {})))
    return ret

  @mysql_utils.WithTransaction()
  def DeleteAllFlowRequestsAndResponses(self, client_id, flow_id, cursor=None):
    """Deletes all requests and responses for a given flow from the database."""
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]
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
    query = ("SELECT request, needs_processing, responses_expected, "
             "UNIX_TIMESTAMP(timestamp) "
             "FROM flow_requests "
             "WHERE client_id=%s AND flow_id=%s")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]
    cursor.execute(query, args)

    requests = {}
    for req, needs_processing, responses_expected, ts in cursor.fetchall():
      if not needs_processing:
        continue

      request = rdf_flow_objects.FlowRequest.FromSerializedString(req)
      request.needs_processing = needs_processing
      request.nr_responses_expected = responses_expected
      request.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      requests[request.request_id] = request

    query = ("SELECT response, status, iterator, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_responses "
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
      response.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
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
  def ReleaseProcessedFlow(self, flow_obj, cursor=None):
    """Releases a flow that the worker was processing to the database."""

    update_query = """
    UPDATE flows
    LEFT OUTER JOIN (
      SELECT client_id, flow_id, needs_processing
      FROM flow_requests
      WHERE
        client_id = %(client_id)s AND
        flow_id = %(flow_id)s AND
        request_id = %(next_request_to_process)s AND
        needs_processing
    ) AS needs_processing
    ON
      flows.client_id = needs_processing.client_id AND
      flows.flow_id = needs_processing.flow_id
    SET
      flows.flow = %(flow)s,
      flows.processing_on = NULL,
      flows.processing_since = NULL,
      flows.processing_deadline = NULL,
      flows.next_request_to_process = %(next_request_to_process)s,
      flows.flow_state = %(flow_state)s,
      flows.user_cpu_time_used_micros = %(user_cpu_time_used_micros)s,
      flows.system_cpu_time_used_micros = %(system_cpu_time_used_micros)s,
      flows.network_bytes_sent = %(network_bytes_sent)s,
      flows.num_replies_sent = %(num_replies_sent)s,
      flows.last_update = NOW(6)
    WHERE
      flows.client_id = %(client_id)s AND
      flows.flow_id = %(flow_id)s AND (
        needs_processing.needs_processing = FALSE OR
        needs_processing.needs_processing IS NULL)
    """

    clone = flow_obj.Copy()
    clone.processing_on = None
    clone.processing_since = None
    clone.processing_deadline = None
    args = {
        "client_id":
            db_utils.ClientIDToInt(flow_obj.client_id),
        "flow":
            clone.SerializeToString(),
        "flow_id":
            db_utils.FlowIDToInt(flow_obj.flow_id),
        "flow_state":
            int(clone.flow_state),
        "network_bytes_sent":
            flow_obj.network_bytes_sent,
        "next_request_to_process":
            flow_obj.next_request_to_process,
        "num_replies_sent":
            flow_obj.num_replies_sent,
        "system_cpu_time_used_micros":
            db_utils.SecondsToMicros(flow_obj.cpu_time_used.system_cpu_time),
        "user_cpu_time_used_micros":
            db_utils.SecondsToMicros(flow_obj.cpu_time_used.user_cpu_time),
    }
    rows_updated = cursor.execute(update_query, args)
    return rows_updated == 1

  @mysql_utils.WithTransaction()
  def WriteFlowProcessingRequests(self, requests, cursor=None):
    """Writes a list of flow processing requests to the database."""
    self._WriteFlowProcessingRequests(requests, cursor)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowProcessingRequests(self, cursor=None):
    """Reads all flow processing requests from the database."""
    query = ("SELECT request, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_processing_requests")
    cursor.execute(query)

    res = []
    for serialized_request, ts in cursor.fetchall():
      req = rdf_flows.FlowProcessingRequest.FromSerializedString(
          serialized_request)
      req.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
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
      conditions.append(
          "(client_id=%s AND flow_id=%s AND timestamp=FROM_UNIXTIME(%s))")
      args.append(db_utils.ClientIDToInt(r.client_id))
      args.append(db_utils.FlowIDToInt(r.flow_id))
      args.append(mysql_utils.RDFDatetimeToTimestamp(r.timestamp))

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
    expiry = now + rdfvalue.Duration("10m")

    query = """
      UPDATE flow_processing_requests
      SET leased_until=FROM_UNIXTIME(%(expiry)s), leased_by=%(id)s
      WHERE
       (delivery_time IS NULL OR
        delivery_time <= NOW(6)) AND
       (leased_until IS NULL OR
        leased_until < NOW(6))
      LIMIT %(limit)s
    """

    id_str = utils.ProcessIdString()
    args = {
        "expiry": mysql_utils.RDFDatetimeToTimestamp(expiry),
        "id": id_str,
        "limit": 50,
    }

    updated = cursor.execute(query, args)

    if updated == 0:
      return []

    query = """
      SELECT UNIX_TIMESTAMP(timestamp), request
      FROM flow_processing_requests
      FORCE INDEX (flow_processing_requests_by_lease)
      WHERE leased_by=%(id)s AND leased_until=FROM_UNIXTIME(%(expiry)s)
      LIMIT %(updated)s
    """

    args = {
        "expiry": mysql_utils.RDFDatetimeToTimestamp(expiry),
        "id": id_str,
        "updated": updated,
    }

    cursor.execute(query, args)

    res = []
    for timestamp, request in cursor.fetchall():
      req = rdf_flows.FlowProcessingRequest.FromSerializedString(request)
      req.timestamp = mysql_utils.TimestampToRDFDatetime(timestamp)
      req.leased_until = expiry
      req.leased_by = id_str
      res.append(req)

    return res

  _FLOW_REQUEST_POLL_TIME_SECS = 3

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
          time.sleep(self._FLOW_REQUEST_POLL_TIME_SECS)

      except Exception as e:  # pylint: disable=broad-except
        logging.exception("_FlowProcessingRequestHandlerLoop raised %s.", e)
        break

  def RegisterFlowProcessingHandler(self, handler):
    """Registers a handler to receive flow processing messages."""
    self.UnregisterFlowProcessingHandler()

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
  def WriteFlowResults(self, results, cursor=None):
    """Writes flow results for a given flow."""
    query = ("INSERT INTO flow_results "
             "(client_id, flow_id, hunt_id, timestamp, payload, type, tag) "
             "VALUES ")
    templates = []

    args = []
    for r in results:
      templates.append("(%s, %s, %s, FROM_UNIXTIME(%s), %s, %s, %s)")
      args.append(db_utils.ClientIDToInt(r.client_id))
      args.append(db_utils.FlowIDToInt(r.flow_id))
      if r.hunt_id:
        args.append(db_utils.HuntIDToInt(r.hunt_id))
      else:
        args.append(0)
      args.append(
          mysql_utils.RDFDatetimeToTimestamp(rdfvalue.RDFDatetime.Now()))
      args.append(r.payload.SerializeToString())
      args.append(compatibility.GetName(r.payload.__class__))
      args.append(r.tag)

    query += ",".join(templates)

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(
          [(r.client_id, r.flow_id) for r in results], cause=e)

  @mysql_utils.WithTransaction(readonly=True)
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

    query = ("SELECT payload, type, UNIX_TIMESTAMP(timestamp), tag "
             "FROM flow_results "
             "FORCE INDEX (flow_results_by_client_id_flow_id_timestamp) "
             "WHERE client_id = %s AND flow_id = %s ")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    if with_tag is not None:
      query += "AND tag = %s "
      args.append(with_tag)

    if with_type is not None:
      query += "AND type = %s "
      args.append(with_type)

    if with_substring is not None:
      query += "AND payload LIKE %s "
      args.append("%{}%".format(with_substring))

    query += "ORDER BY timestamp ASC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)

    ret = []
    for serialized_payload, payload_type, ts, tag in cursor.fetchall():
      if payload_type in rdfvalue.RDFValue.classes:
        payload = rdfvalue.RDFValue.classes[payload_type]()
        payload.ParseFromString(serialized_payload)
      else:
        payload = rdf_objects.SerializedValueOfUnrecognizedType(
            type_name=payload_type, value=serialized_payload)

      timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      result = rdf_flow_objects.FlowResult(payload=payload, timestamp=timestamp)
      if tag:
        result.tag = tag

      ret.append(result)

    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def CountFlowResults(self,
                       client_id,
                       flow_id,
                       with_tag=None,
                       with_type=None,
                       cursor=None):
    """Counts flow results of a given flow using given query options."""
    query = ("SELECT COUNT(*) "
             "FROM flow_results "
             "FORCE INDEX (flow_results_by_client_id_flow_id_timestamp) "
             "WHERE client_id = %s AND flow_id = %s ")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    if with_tag is not None:
      query += "AND tag = %s "
      args.append(with_tag)

    if with_type is not None:
      query += "AND type = %s "
      args.append(with_type)

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @mysql_utils.WithTransaction(readonly=True)
  def CountFlowResultsByType(self, client_id, flow_id, cursor=None):
    """Returns counts of flow results grouped by result type."""
    query = ("SELECT type, COUNT(*) FROM flow_results "
             "FORCE INDEX (flow_results_by_client_id_flow_id_timestamp) "
             "WHERE client_id = %s AND flow_id = %s "
             "GROUP BY type")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    cursor.execute(query, args)

    return dict(cursor.fetchall())

  @mysql_utils.WithTransaction()
  def WriteFlowLogEntries(self, entries, cursor=None):
    """Writes flow log entries for a given flow."""
    query = ("INSERT INTO flow_log_entries "
             "(client_id, flow_id, hunt_id, message) "
             "VALUES ")
    templates = []
    args = []
    for entry in entries:
      templates.append("(%s, %s, %s, %s)")
      args.append(db_utils.ClientIDToInt(entry.client_id))
      args.append(db_utils.FlowIDToInt(entry.flow_id))
      if entry.hunt_id:
        args.append(db_utils.HuntIDToInt(entry.hunt_id))
      else:
        args.append(0)
      args.append(entry.message)

    query += ",".join(templates)

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(
          [(entry.client_id, entry.flow_id) for entry in entries], cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowLogEntries(self,
                         client_id,
                         flow_id,
                         offset,
                         count,
                         with_substring=None,
                         cursor=None):
    """Reads flow log entries of a given flow using given query options."""

    query = ("SELECT message, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_log_entries "
             "FORCE INDEX (flow_log_entries_by_flow) "
             "WHERE client_id = %s AND flow_id = %s ")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    if with_substring is not None:
      query += "AND message LIKE %s "
      args.append("%{}%".format(with_substring))

    query += "ORDER BY log_id ASC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)

    ret = []
    for message, timestamp in cursor.fetchall():
      ret.append(
          rdf_flow_objects.FlowLogEntry(
              message=message,
              timestamp=mysql_utils.TimestampToRDFDatetime(timestamp)))

    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def CountFlowLogEntries(self, client_id, flow_id, cursor=None):
    """Returns number of flow log entries of a given flow."""

    query = ("SELECT COUNT(*) "
             "FROM flow_log_entries "
             "FORCE INDEX (flow_log_entries_by_flow) "
             "WHERE client_id = %s AND flow_id = %s ")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @mysql_utils.WithTransaction()
  def WriteFlowOutputPluginLogEntries(self, entries, cursor=None):
    """Writes flow output plugin log entries for a given flow."""
    query = ("INSERT INTO flow_output_plugin_log_entries "
             "(client_id, flow_id, hunt_id, output_plugin_id, "
             "log_entry_type, message) "
             "VALUES ")
    templates = []
    args = []
    for entry in entries:
      templates.append("(%s, %s, %s, %s, %s, %s)")
      args.append(db_utils.ClientIDToInt(entry.client_id))
      args.append(db_utils.FlowIDToInt(entry.flow_id))
      if entry.hunt_id:
        args.append(db_utils.HuntIDToInt(entry.hunt_id))
      else:
        args.append(0)
      args.append(db_utils.OutputPluginIDToInt(entry.output_plugin_id))
      args.append(int(entry.log_entry_type))
      args.append(entry.message)

    query += ",".join(templates)

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(
          [(entry.client_id, entry.flow_id) for entry in entries], cause=e)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowOutputPluginLogEntries(self,
                                     client_id,
                                     flow_id,
                                     output_plugin_id,
                                     offset,
                                     count,
                                     with_type=None,
                                     cursor=None):
    """Reads flow output plugin log entries."""
    query = ("SELECT log_entry_type, message, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_output_plugin_log_entries "
             "FORCE INDEX (flow_output_plugin_log_entries_by_flow) "
             "WHERE client_id = %s AND flow_id = %s AND output_plugin_id = %s ")
    args = [
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id),
        db_utils.OutputPluginIDToInt(output_plugin_id)
    ]

    if with_type is not None:
      query += "AND log_entry_type = %s "
      args.append(int(with_type))

    query += "ORDER BY log_id ASC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)

    ret = []
    for log_entry_type, message, timestamp in cursor.fetchall():
      ret.append(
          rdf_flow_objects.FlowOutputPluginLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              output_plugin_id=output_plugin_id,
              log_entry_type=log_entry_type,
              message=message,
              timestamp=mysql_utils.TimestampToRDFDatetime(timestamp)))

    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def CountFlowOutputPluginLogEntries(self,
                                      client_id,
                                      flow_id,
                                      output_plugin_id,
                                      with_type=None,
                                      cursor=None):
    """Returns number of flow output plugin log entries of a given flow."""
    query = ("SELECT COUNT(*) "
             "FROM flow_output_plugin_log_entries "
             "FORCE INDEX (flow_output_plugin_log_entries_by_flow) "
             "WHERE client_id = %s AND flow_id = %s AND output_plugin_id = %s ")
    args = [
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id), output_plugin_id
    ]

    if with_type is not None:
      query += "AND log_entry_type = %s"
      args.append(int(with_type))

    cursor.execute(query, args)
    return cursor.fetchone()[0]
