#!/usr/bin/env python
"""The MySQL database methods for flow handling."""

import logging
import threading
import time
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Text

import MySQLdb
from MySQLdb import cursors
from MySQLdb.constants import ER as mysql_errors

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import random
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
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
      args.extend([r.handler_name, r.request_id, r.SerializeToBytes()])
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
      req = rdf_objects.MessageHandlerRequest.FromSerializedBytes(request)
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
      if self.handler_thread.is_alive():
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
      req = rdf_objects.MessageHandlerRequest.FromSerializedBytes(request)
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
      request = rdf_flows.ClientActionRequest.FromSerializedBytes(req)
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
      request = rdf_flows.ClientActionRequest.FromSerializedBytes(req)
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
          r.SerializeToBytes()
      ])
      value_templates.append("(%s, %s, %s, FROM_UNIXTIME(%s), %s)")

    query %= ",".join(value_templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      request_keys = [(r.client_id, r.flow_id, r.request_id) for r in requests]
      raise db.AtLeastOneUnknownRequestError(request_keys=request_keys, cause=e)

  @mysql_utils.WithTransaction()
  def WriteFlowObject(self, flow_obj, allow_update=True, cursor=None):
    """Writes a flow object to the database."""

    query = """
    INSERT INTO flows (client_id, flow_id, long_flow_id, parent_flow_id,
                       parent_hunt_id, name, creator, flow, flow_state,
                       next_request_to_process, timestamp,
                       network_bytes_sent, user_cpu_time_used_micros,
                       system_cpu_time_used_micros, num_replies_sent, last_update)
    VALUES (%(client_id)s, %(flow_id)s, %(long_flow_id)s, %(parent_flow_id)s,
            %(parent_hunt_id)s, %(name)s, %(creator)s, %(flow)s, %(flow_state)s,
            %(next_request_to_process)s, NOW(6),
            %(network_bytes_sent)s, %(user_cpu_time_used_micros)s,
            %(system_cpu_time_used_micros)s, %(num_replies_sent)s, NOW(6))"""

    if allow_update:
      query += """
        ON DUPLICATE KEY UPDATE
          flow=VALUES(flow),
          flow_state=VALUES(flow_state),
          next_request_to_process=VALUES(next_request_to_process),
          last_update=VALUES(last_update)"""

    user_cpu_time_used_micros = db_utils.SecondsToMicros(
        flow_obj.cpu_time_used.user_cpu_time)
    system_cpu_time_used_micros = db_utils.SecondsToMicros(
        flow_obj.cpu_time_used.system_cpu_time)

    args = {
        "client_id": db_utils.ClientIDToInt(flow_obj.client_id),
        "flow_id": db_utils.FlowIDToInt(flow_obj.flow_id),
        "long_flow_id": flow_obj.long_flow_id,
        "name": flow_obj.flow_class_name,
        "creator": flow_obj.creator,
        "flow": flow_obj.SerializeToBytes(),
        "flow_state": int(flow_obj.flow_state),
        "next_request_to_process": flow_obj.next_request_to_process,
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

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      if e.args[0] == mysql_errors.DUP_ENTRY:
        raise db.FlowExistsError(flow_obj.client_id, flow_obj.flow_id)
      else:
        raise db.UnknownClientError(flow_obj.client_id, cause=e)

  def _FlowObjectFromRow(self, row):
    """Generates a flow object from a database row."""
    datetime = mysql_utils.TimestampToRDFDatetime
    cpu_time = db_utils.MicrosToSeconds

    # pyformat: disable
    (client_id, flow_id, long_flow_id, parent_flow_id, parent_hunt_id,
     name, creator,
     flow, flow_state,
     client_crash_info,
     next_request_to_process,
     processing_deadline, processing_on, processing_since,
     user_cpu_time, system_cpu_time, network_bytes_sent, num_replies_sent,
     timestamp, last_update_timestamp) = row
    # pyformat: enable

    flow_obj = rdf_flow_objects.Flow.FromSerializedBytes(flow)

    # We treat column values as the source of truth, not the proto.
    flow_obj.client_id = db_utils.IntToClientID(client_id)
    flow_obj.flow_id = db_utils.IntToFlowID(flow_id)
    flow_obj.long_flow_id = long_flow_id

    if parent_flow_id is not None:
      flow_obj.parent_flow_id = db_utils.IntToFlowID(parent_flow_id)
    if parent_hunt_id is not None:
      flow_obj.parent_hunt_id = db_utils.IntToHuntID(parent_hunt_id)
    if name is not None:
      flow_obj.flow_class_name = name
    if creator is not None:
      flow_obj.creator = creator
    if flow_state not in [None, rdf_flow_objects.Flow.FlowState.UNSET]:
      flow_obj.flow_state = flow_state
    if client_crash_info is not None:
      deserialize = rdf_client.ClientCrash.FromSerializedBytes
      flow_obj.client_crash_info = deserialize(client_crash_info)
    if next_request_to_process:
      flow_obj.next_request_to_process = next_request_to_process
    if processing_deadline is not None:
      flow_obj.processing_deadline = datetime(processing_deadline)
    if processing_on is not None:
      flow_obj.processing_on = processing_on
    if processing_since is not None:
      flow_obj.processing_since = datetime(processing_since)
    flow_obj.cpu_time_used.user_cpu_time = cpu_time(user_cpu_time)
    flow_obj.cpu_time_used.system_cpu_time = cpu_time(system_cpu_time)
    flow_obj.network_bytes_sent = network_bytes_sent
    if num_replies_sent:
      flow_obj.num_replies_sent = num_replies_sent
    flow_obj.last_update_time = datetime(last_update_timestamp)

    # In case the create time is not stored in the serialized flow (which might
    # be the case), we fallback to the timestamp information stored in the
    # column.
    if flow_obj.create_time is None:
      flow_obj.create_time = datetime(timestamp)

    return flow_obj

  FLOW_DB_FIELDS = ", ".join((
      "client_id",
      "flow_id",
      "long_flow_id",
      "parent_flow_id",
      "parent_hunt_id",
      "name",
      "creator",
      "flow",
      "flow_state",
      "client_crash_info",
      "next_request_to_process",
      "UNIX_TIMESTAMP(processing_deadline)",
      "processing_on",
      "UNIX_TIMESTAMP(processing_since)",
      "user_cpu_time_used_micros",
      "system_cpu_time_used_micros",
      "network_bytes_sent",
      "num_replies_sent",
      "UNIX_TIMESTAMP(timestamp)",
      "UNIX_TIMESTAMP(last_update)",
  ))

  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowObject(self, client_id, flow_id, cursor=None):
    """Reads a flow object from the database."""
    query = (f"SELECT {self.FLOW_DB_FIELDS} "
             f"FROM flows WHERE client_id=%s AND flow_id=%s")
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
  def ReadAllFlowObjects(
      self,
      client_id: Optional[Text] = None,
      parent_flow_id: Optional[str] = None,
      min_create_time: Optional[rdfvalue.RDFDatetime] = None,
      max_create_time: Optional[rdfvalue.RDFDatetime] = None,
      include_child_flows: bool = True,
      not_created_by: Optional[Iterable[str]] = None,
      cursor=None,
  ) -> List[rdf_flow_objects.Flow]:
    """Returns all flow objects."""
    conditions = []
    args = []

    if client_id is not None:
      conditions.append("client_id = %s")
      args.append(db_utils.ClientIDToInt(client_id))

    if parent_flow_id is not None:
      conditions.append("parent_flow_id = %s")
      args.append(db_utils.FlowIDToInt(parent_flow_id))

    if min_create_time is not None:
      conditions.append("timestamp >= FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(min_create_time))

    if max_create_time is not None:
      conditions.append("timestamp <= FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(max_create_time))

    if not include_child_flows:
      conditions.append("parent_flow_id IS NULL")

    if not_created_by is not None:
      conditions.append("creator NOT IN %s")
      # We explicitly convert not_created_by into a list because the cursor
      # implementation does not know how to convert a `frozenset` to a string.
      # The cursor implementation knows how to convert lists and ordinary sets.
      args.append(list(not_created_by))

    query = f"SELECT {self.FLOW_DB_FIELDS} FROM flows"
    if conditions:
      query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, args)
    return [self._FlowObjectFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction()
  def LeaseFlowForProcessing(self,
                             client_id,
                             flow_id,
                             processing_time,
                             cursor=None):
    """Marks a flow as being processed on this worker and returns it."""
    query = (f"SELECT {self.FLOW_DB_FIELDS} "
             f"FROM flows WHERE client_id=%s AND flow_id=%s")
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
                       (flow_id, client_id))

    if rdf_flow.parent_hunt_id is not None:

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
                 processing_on=db.Database.unchanged,
                 processing_since=db.Database.unchanged,
                 processing_deadline=db.Database.unchanged,
                 cursor=None):
    """Updates flow objects in the database."""
    updates = []
    args = []
    if flow_obj != db.Database.unchanged:
      updates.append("flow=%s")
      args.append(flow_obj.SerializeToBytes())
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
      args.append(client_crash_info.SerializeToBytes())
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

  def _WriteFlowProcessingRequests(self, requests, cursor):
    """Returns a (query, args) tuple that inserts the given requests."""
    templates = []
    args = []
    for req in requests:
      templates.append("(%s, %s, %s, FROM_UNIXTIME(%s))")
      args.append(db_utils.ClientIDToInt(req.client_id))
      args.append(db_utils.FlowIDToInt(req.flow_id))
      args.append(req.SerializeToBytes())
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
      templates.append("(%s, %s, %s, %s, %s, %s, %s)")
      args.extend([
          db_utils.ClientIDToInt(r.client_id),
          db_utils.FlowIDToInt(r.flow_id), r.request_id, r.needs_processing,
          r.callback_state, r.next_response_id,
          r.SerializeToBytes()
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
             "(client_id, flow_id, request_id, needs_processing, "
             "callback_state, next_response_id, request) "
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
        args.append(r.SerializeToBytes())
        args.append("")
        args.append("")
      elif isinstance(r, rdf_flow_objects.FlowStatus):
        args.append("")
        args.append(r.SerializeToBytes())
        args.append("")
      elif isinstance(r, rdf_flow_objects.FlowIterator):
        args.append("")
        args.append("")
        args.append(r.SerializeToBytes())
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
        logging.warning("Response for unknown request: %s", responses[0])

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
        flow_requests.request_id,
        COUNT(*)
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
    for client_id_int, flow_id_int, request_id, count in cursor.fetchall():
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

  def _ReadLockAndUpdateAffectedRequests(self, request_keys, response_counts,
                                         cursor):
    """Reads, locks, and updates completed requests."""

    condition_template = """
      (flow_requests.client_id = %s AND
       flow_requests.flow_id = %s AND
       flow_requests.request_id = %s AND
       (responses_expected = %s OR callback_state != ''))"""
    callback_agnostic_condition_template = """
      (flow_requests.client_id = %s AND
       flow_requests.flow_id = %s AND
       flow_requests.request_id = %s AND
       responses_expected = %s)"""

    args = []
    conditions = []
    callback_agnostic_conditions = []
    affected_requests = {}

    for request_key in request_keys:
      client_id, flow_id, request_id = request_key
      if request_key in response_counts:
        conditions.append(condition_template)
        callback_agnostic_conditions.append(
            callback_agnostic_condition_template)
        args.append(db_utils.ClientIDToInt(client_id))
        args.append(db_utils.FlowIDToInt(flow_id))
        args.append(request_id)
        args.append(response_counts[request_key])

    if not args:
      return affected_requests

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
      r = rdf_flow_objects.FlowRequest.FromSerializedBytes(request)
      affected_requests[request_key] = r

    query = """
    UPDATE flow_requests
    SET needs_processing = TRUE
    WHERE ({conditions}) AND NOT needs_processing
    """
    query = query.format(conditions=" OR ".join(callback_agnostic_conditions))
    cursor.execute(query, args)

    return affected_requests

  @mysql_utils.WithTransaction()
  def _UpdateRequestsAndScheduleFPRs(self, responses, cursor=None):
    """Updates requests and writes FlowProcessingRequests if needed."""

    request_keys = set(
        (r.client_id, r.flow_id, r.request_id) for r in responses)
    flow_keys = set((r.client_id, r.flow_id) for r in responses)

    response_counts = self._ReadFlowResponseCounts(request_keys, cursor)

    next_requests = self._ReadAndLockNextRequestsToProcess(flow_keys, cursor)

    affected_requests = self._ReadLockAndUpdateAffectedRequests(
        request_keys, response_counts, cursor)

    if not affected_requests:
      return []

    fprs_to_write = []
    for request_key, r in affected_requests.items():
      client_id, flow_id, request_id = request_key
      if next_requests[(client_id, flow_id)] == request_id:
        fprs_to_write.append(
            rdf_flows.FlowProcessingRequest(
                client_id=r.client_id,
                flow_id=r.flow_id,
                delivery_time=r.start_time))

    if fprs_to_write:
      self._WriteFlowProcessingRequests(fprs_to_write, cursor)

    return affected_requests

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
  def UpdateIncrementalFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      next_response_id_updates: Dict[int, int],
      cursor: Optional[cursors.Cursor] = None) -> None:
    """Updates next response ids of given requests."""
    if not next_response_id_updates:
      return

    for request_id, next_response_id in next_response_id_updates.items():
      query = ("UPDATE flow_requests SET next_response_id=%s WHERE "
               "client_id=%s AND flow_id=%s AND request_id=%s")
      args = [
          next_response_id,
          db_utils.ClientIDToInt(client_id),
          db_utils.FlowIDToInt(flow_id), request_id
      ]
      cursor.execute(query, args)

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
             "callback_state, next_response_id, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_requests WHERE client_id=%s AND flow_id=%s")

    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]
    cursor.execute(query, args)

    requests = []
    for (req, needs_processing, resp_expected, callback_state, next_response_id,
         ts) in cursor.fetchall():
      request = rdf_flow_objects.FlowRequest.FromSerializedBytes(req)
      request.needs_processing = needs_processing
      request.nr_responses_expected = resp_expected
      request.callback_state = callback_state
      request.next_response_id = next_response_id
      request.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      requests.append(request)

    query = ("SELECT response, status, iterator, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_responses WHERE client_id=%s AND flow_id=%s")
    cursor.execute(query, args)

    responses = {}
    for res, status, iterator, ts in cursor.fetchall():
      if status:
        response = rdf_flow_objects.FlowStatus.FromSerializedBytes(status)
      elif iterator:
        response = rdf_flow_objects.FlowIterator.FromSerializedBytes(iterator)
      else:
        response = rdf_flow_objects.FlowResponse.FromSerializedBytes(res)
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
             "callback_state, next_response_id, "
             "UNIX_TIMESTAMP(timestamp) "
             "FROM flow_requests "
             "WHERE client_id=%s AND flow_id=%s")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]
    cursor.execute(query, args)

    requests = {}
    for (req, needs_processing, responses_expected, callback_state,
         next_response_id, ts) in cursor.fetchall():
      request = rdf_flow_objects.FlowRequest.FromSerializedBytes(req)
      request.needs_processing = needs_processing
      request.nr_responses_expected = responses_expected
      request.callback_state = callback_state
      request.next_response_id = next_response_id
      request.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      requests[request.request_id] = request

    query = ("SELECT response, status, iterator, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_responses "
             "WHERE client_id=%s AND flow_id=%s")
    cursor.execute(query, args)

    responses = {}
    for res, status, iterator, ts in cursor.fetchall():
      if status:
        response = rdf_flow_objects.FlowStatus.FromSerializedBytes(status)
      elif iterator:
        response = rdf_flow_objects.FlowIterator.FromSerializedBytes(iterator)
      else:
        response = rdf_flow_objects.FlowResponse.FromSerializedBytes(res)
      response.timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      responses.setdefault(response.request_id, []).append(response)

    res = {}

    # Do a pass for completed requests.
    while next_needed_request in requests:
      req = requests[next_needed_request]

      if not req.needs_processing:
        break

      sorted_responses = sorted(
          responses.get(next_needed_request, []), key=lambda r: r.response_id)
      res[req.request_id] = (req, sorted_responses)
      next_needed_request += 1

    # Do a pass for incremental requests.
    for request_id in requests:
      if request_id < next_needed_request:
        continue

      request = requests[request_id]
      if not request.callback_state:
        continue

      rs = responses.get(request_id, [])
      rs = [r for r in rs if r.response_id >= request.next_response_id]
      rs = sorted(rs, key=lambda r: r.response_id)

      res[request_id] = (request, rs)

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
            clone.SerializeToBytes(),
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
      req = rdf_flows.FlowProcessingRequest.FromSerializedBytes(
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
    expiry = now + rdfvalue.Duration.From(10, rdfvalue.MINUTES)

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

    # Appending a random id here to make the key we lease by unique in cases
    # where we run multiple leasing attempts with the same timestamp - which can
    # happen on Windows where timestamp resolution is lower.
    id_str = "%s:%d" % (utils.ProcessIdString(), random.UInt16())
    expiry_str = mysql_utils.RDFDatetimeToTimestamp(expiry)
    args = {
        "expiry": expiry_str,
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
        "expiry": expiry_str,
        "id": id_str,
        "updated": updated,
    }

    cursor.execute(query, args)

    res = []
    for timestamp, request in cursor.fetchall():
      req = rdf_flows.FlowProcessingRequest.FromSerializedBytes(request)
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
        time.sleep(self._FLOW_REQUEST_POLL_TIME_SECS)

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
      if self.flow_processing_request_handler_thread.is_alive():
        raise RuntimeError("Flow processing handler did not join in time.")
      self.flow_processing_request_handler_thread = None

  @mysql_utils.WithTransaction()
  def _WriteFlowResultsOrErrors(self, table_name, results, cursor=None):
    """Writes flow results/errors for a given flow."""

    query = (f"INSERT INTO {table_name} "
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
      args.append(r.payload.SerializeToBytes())
      args.append(compatibility.GetName(r.payload.__class__))
      args.append(r.tag)

    query += ",".join(templates)

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(
          [(r.client_id, r.flow_id) for r in results], cause=e)

  def WriteFlowResults(self, results):
    """Writes flow results for a given flow."""
    self._WriteFlowResultsOrErrors("flow_results", results)

  @mysql_utils.WithTransaction(readonly=True)
  def _ReadFlowResultsOrErrors(self,
                               table_name,
                               result_cls,
                               client_id,
                               flow_id,
                               offset,
                               count,
                               with_tag=None,
                               with_type=None,
                               with_substring=None,
                               cursor=None):
    """Reads flow results/errors of a given flow using given query options."""
    client_id_int = db_utils.ClientIDToInt(client_id)
    flow_id_int = db_utils.FlowIDToInt(flow_id)

    query = f"""
        SELECT payload, type, UNIX_TIMESTAMP(timestamp), tag, hunt_id
        FROM {table_name}
        FORCE INDEX ({table_name}_by_client_id_flow_id_timestamp)
        WHERE client_id = %s AND flow_id = %s """
    args = [client_id_int, flow_id_int]

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
    for serialized_payload, payload_type, ts, tag, hid in cursor.fetchall():
      if payload_type in rdfvalue.RDFValue.classes:
        payload = rdfvalue.RDFValue.classes[payload_type].FromSerializedBytes(
            serialized_payload)
      else:
        payload = rdf_objects.SerializedValueOfUnrecognizedType(
            type_name=payload_type, value=serialized_payload)

      timestamp = mysql_utils.TimestampToRDFDatetime(ts)
      result = result_cls(
          client_id=db_utils.IntToClientID(client_id_int),
          flow_id=db_utils.IntToFlowID(flow_id_int),
          payload=payload,
          timestamp=timestamp)

      if hid:
        result.hunt_id = db_utils.IntToHuntID(hid)

      if tag:
        result.tag = tag

      ret.append(result)

    return ret

  def ReadFlowResults(self,
                      client_id,
                      flow_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    """Reads flow results of a given flow using given query options."""
    return self._ReadFlowResultsOrErrors(
        "flow_results",
        rdf_flow_objects.FlowResult,
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_substring=with_substring)

  @mysql_utils.WithTransaction(readonly=True)
  def _CountFlowResultsOrErrors(self,
                                table_name,
                                client_id,
                                flow_id,
                                with_tag=None,
                                with_type=None,
                                cursor=None):
    """Counts flow results/errors of a given flow using given query options."""
    query = ("SELECT COUNT(*) "
             f"FROM {table_name} "
             f"FORCE INDEX ({table_name}_by_client_id_flow_id_timestamp) "
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

  def CountFlowResults(self, client_id, flow_id, with_tag=None, with_type=None):
    """Counts flow results of a given flow using given query options."""
    return self._CountFlowResultsOrErrors(
        "flow_results",
        client_id,
        flow_id,
        with_tag=with_tag,
        with_type=with_type)

  @mysql_utils.WithTransaction(readonly=True)
  def _CountFlowResultsOrErrorsByType(self,
                                      table_name,
                                      client_id,
                                      flow_id,
                                      cursor=None):
    """Returns counts of flow results/errors grouped by result type."""
    query = (f"SELECT type, COUNT(*) FROM {table_name} "
             f"FORCE INDEX ({table_name}_by_client_id_flow_id_timestamp) "
             "WHERE client_id = %s AND flow_id = %s "
             "GROUP BY type")
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    cursor.execute(query, args)

    return dict(cursor.fetchall())

  def CountFlowResultsByType(self, client_id, flow_id):
    """Returns counts of flow results grouped by result type."""
    return self._CountFlowResultsOrErrorsByType("flow_results", client_id,
                                                flow_id)

  def WriteFlowErrors(self, errors):
    """Writes flow errors for a given flow."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    self._WriteFlowResultsOrErrors("flow_errors", errors)

  def ReadFlowErrors(self,
                     client_id,
                     flow_id,
                     offset,
                     count,
                     with_tag=None,
                     with_type=None):
    """Reads flow errors of a given flow using given query options."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    return self._ReadFlowResultsOrErrors(
        "flow_errors",
        rdf_flow_objects.FlowError,
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type)

  def CountFlowErrors(self, client_id, flow_id, with_tag=None, with_type=None):
    """Counts flow errors of a given flow using given query options."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    return self._CountFlowResultsOrErrors(
        "flow_errors",
        client_id,
        flow_id,
        with_tag=with_tag,
        with_type=with_type)

  def CountFlowErrorsByType(self, client_id, flow_id):
    """Returns counts of flow errors grouped by error type."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    return self._CountFlowResultsOrErrorsByType("flow_errors", client_id,
                                                flow_id)

  @mysql_utils.WithTransaction()
  def WriteFlowLogEntry(
      self,
      entry: rdf_flow_objects.FlowLogEntry,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a single flow log entry to the database."""
    query = """
    INSERT INTO flow_log_entries
                (client_id, flow_id, hunt_id, message)
         VALUES (%(client_id)s, %(flow_id)s, %(hunt_id)s, %(message)s)
    """
    args = {
        "client_id": db_utils.ClientIDToInt(entry.client_id),
        "flow_id": db_utils.FlowIDToInt(entry.flow_id),
        "message": entry.message
    }

    if entry.hunt_id:
      args["hunt_id"] = db_utils.HuntIDToInt(entry.hunt_id)
    else:
      args["hunt_id"] = 0

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id) from error

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
  def WriteFlowOutputPluginLogEntry(
      self,
      entry: rdf_flow_objects.FlowOutputPluginLogEntry,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes a single output plugin log entry to the database."""
    query = """
    INSERT INTO flow_output_plugin_log_entries
                (client_id, flow_id, hunt_id, output_plugin_id,
                 log_entry_type, message)
         VALUES (%(client_id)s, %(flow_id)s, %(hunt_id)s, %(output_plugin_id)s,
                 %(type)s, %(message)s)
    """
    args = {
        "client_id":
            db_utils.ClientIDToInt(entry.client_id),
        "flow_id":
            db_utils.FlowIDToInt(entry.flow_id),
        "output_plugin_id":
            db_utils.OutputPluginIDToInt(entry.output_plugin_id),
        "type":
            int(entry.log_entry_type),
        "message":
            entry.message,
    }

    if entry.hunt_id:
      args["hunt_id"] = db_utils.HuntIDToInt(entry.hunt_id)
    else:
      args["hunt_id"] = None

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id) from error

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

  @mysql_utils.WithTransaction()
  def WriteScheduledFlow(self,
                         scheduled_flow: rdf_flow_objects.ScheduledFlow,
                         cursor=None) -> None:
    """See base class."""
    sf = scheduled_flow

    args = {
        "client_id": db_utils.ClientIDToInt(sf.client_id),
        "creator_username_hash": mysql_utils.Hash(sf.creator),
        "scheduled_flow_id": db_utils.FlowIDToInt(sf.scheduled_flow_id),
        "flow_name": sf.flow_name,
        "flow_args": sf.flow_args.SerializeToBytes(),
        "runner_args": sf.runner_args.SerializeToBytes(),
        "create_time": mysql_utils.RDFDatetimeToTimestamp(sf.create_time),
        "error": sf.error,
    }

    vals = mysql_utils.NamedPlaceholders(args)
    vals = vals.replace("%(create_time)s", "FROM_UNIXTIME(%(create_time)s)")

    query = """
      REPLACE INTO scheduled_flows {cols}
      VALUES {vals}
    """.format(
        cols=mysql_utils.Columns(args), vals=vals)

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      if "creator_username_hash" in str(error):
        raise db.UnknownGRRUserError(sf.creator, cause=error)
      elif "client_id" in str(error):
        raise db.UnknownClientError(sf.client_id, cause=error)
      raise

  @mysql_utils.WithTransaction()
  def DeleteScheduledFlow(self,
                          client_id: str,
                          creator: str,
                          scheduled_flow_id: str,
                          cursor=None) -> None:
    """See base class."""

    cursor.execute(
        """
      DELETE FROM
        scheduled_flows
      WHERE
        client_id = %s AND
        creator_username_hash = %s AND
        scheduled_flow_id = %s
      """, [
          db_utils.ClientIDToInt(client_id),
          mysql_utils.Hash(creator),
          db_utils.FlowIDToInt(scheduled_flow_id),
      ])

    if cursor.rowcount == 0:
      raise db.UnknownScheduledFlowError(
          client_id=client_id,
          creator=creator,
          scheduled_flow_id=scheduled_flow_id)

  @mysql_utils.WithTransaction(readonly=True)
  def ListScheduledFlows(
      self,
      client_id: str,
      creator: str,
      cursor=None) -> Sequence[rdf_flow_objects.ScheduledFlow]:
    """See base class."""

    query = """
      SELECT
        sf.client_id, u.username, sf.scheduled_flow_id, sf.flow_name,
        sf.flow_args, sf.runner_args, UNIX_TIMESTAMP(sf.create_time), sf.error
      FROM
        scheduled_flows sf
      LEFT JOIN
        grr_users u
      ON
        u.username_hash = sf.creator_username_hash
      WHERE
        client_id = %s AND
        creator_username_hash = %s"""

    args = [
        db_utils.ClientIDToInt(client_id),
        mysql_utils.Hash(creator),
    ]

    cursor.execute(query, args)

    results = []

    for row in cursor.fetchall():
      flow_class = registry.FlowRegistry.FlowClassByName(row[3])
      flow_args = flow_class.args_type.FromSerializedBytes(row[4])
      runner_args = rdf_flow_runner.FlowRunnerArgs.FromSerializedBytes(row[5])

      results.append(
          rdf_flow_objects.ScheduledFlow(
              client_id=db_utils.IntToClientID(row[0]),
              creator=row[1],
              scheduled_flow_id=db_utils.IntToFlowID(row[2]),
              flow_name=row[3],
              flow_args=flow_args,
              runner_args=runner_args,
              create_time=mysql_utils.TimestampToRDFDatetime(row[6]),
              error=row[7]))
    return results
