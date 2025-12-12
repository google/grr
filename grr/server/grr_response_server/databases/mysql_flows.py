#!/usr/bin/env python
"""The MySQL database methods for flow handling."""

from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
import logging
import threading
import time
from typing import Optional, Union

import MySQLdb
from MySQLdb import cursors
from MySQLdb.constants import ER as mysql_errors

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import random
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import threadpool
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.models import hunts as models_hunts
from grr_response_proto import rrg_pb2


class MySQLDBFlowMixin:
  """MySQLDB mixin for flow handling."""

  flow_processing_request_handler_pool: threadpool.ThreadPool
  flow_processing_request_handler_thread: threading.Thread
  handler_thread: threading.Thread
  _WRITE_ROWS_BATCH_SIZE: int
  _DELETE_ROWS_BATCH_SIZE: int

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteMessageHandlerRequests(
      self,
      requests: Iterable[objects_pb2.MessageHandlerRequest],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a list of message handler requests to the database."""
    assert cursor is not None

    query = (
        "INSERT IGNORE INTO message_handler_requests "
        "(handlername, request_id, request) VALUES "
    )

    value_templates = []
    args = []
    for r in requests:
      args.extend([r.handler_name, r.request_id, r.SerializeToString()])
      value_templates.append("(%s, %s, %s)")

    query += ",".join(value_templates)
    cursor.execute(query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadMessageHandlerRequests(
      self,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[objects_pb2.MessageHandlerRequest]:
    """Reads all message handler requests from the database."""
    assert cursor is not None

    query = (
        "SELECT UNIX_TIMESTAMP(timestamp), request,"
        "       UNIX_TIMESTAMP(leased_until), leased_by "
        "FROM message_handler_requests "
        "ORDER BY timestamp DESC"
    )

    cursor.execute(query)

    res = []
    for timestamp, request, leased_until, leased_by in cursor.fetchall():
      req = objects_pb2.MessageHandlerRequest()
      req.ParseFromString(request)
      req.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(timestamp)
      if leased_by is not None:
        req.leased_by = leased_by
      if leased_until is not None:
        req.leased_until = mysql_utils.TimestampToMicrosecondsSinceEpoch(
            leased_until
        )
      res.append(req)
    return res

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteMessageHandlerRequests(
      self,
      requests: Iterable[objects_pb2.MessageHandlerRequest],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Deletes a list of message handler requests from the database."""
    assert cursor is not None

    query = "DELETE FROM message_handler_requests WHERE request_id IN ({})"
    request_ids = set([r.request_id for r in requests])
    query = query.format(",".join(["%s"] * len(request_ids)))
    cursor.execute(query, request_ids)

  def RegisterMessageHandler(
      self,
      handler: Callable[[Sequence[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    """Leases a number of message handler requests up to the indicated limit."""
    self.UnregisterMessageHandler()

    if handler:
      self.handler_stop = False
      self.handler_thread = threading.Thread(
          name="message_handler",
          target=self._MessageHandlerLoop,
          args=(handler, lease_time, limit),
      )
      self.handler_thread.daemon = True
      self.handler_thread.start()

  def UnregisterMessageHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered message handler."""
    if self.handler_thread:
      self.handler_stop = True
      self.handler_thread.join(timeout)
      if self.handler_thread.is_alive():
        raise RuntimeError("Message handler thread did not join in time.")
      self.handler_thread = None

  _MESSAGE_HANDLER_POLL_TIME_SECS = 5

  def _MessageHandlerLoop(
      self,
      handler: Callable[[Iterable[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    """Loop to handle outstanding requests."""
    while not self.handler_stop:
      try:
        msgs = self._LeaseMessageHandlerRequests(lease_time, limit)
        if msgs:
          handler(msgs)
        else:
          time.sleep(self._MESSAGE_HANDLER_POLL_TIME_SECS)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("_LeaseMessageHandlerRequests raised %s.", e)

  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def _LeaseMessageHandlerRequests(
      self,
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Iterable[objects_pb2.MessageHandlerRequest]:
    """Leases a number of message handler requests up to the indicated limit."""
    assert cursor is not None

    now = rdfvalue.RDFDatetime.Now()
    now_str = mysql_utils.RDFDatetimeToTimestamp(now)

    expiry = now + lease_time
    expiry_str = mysql_utils.RDFDatetimeToTimestamp(expiry)

    query = (
        "UPDATE message_handler_requests "
        "SET leased_until=FROM_UNIXTIME(%s), leased_by=%s "
        "WHERE leased_until IS NULL OR leased_until < FROM_UNIXTIME(%s) "
        "LIMIT %s"
    )

    id_str = utils.ProcessIdString()
    args = (expiry_str, id_str, now_str, limit)
    updated = cursor.execute(query, args)

    if updated == 0:
      return []

    cursor.execute(
        "SELECT UNIX_TIMESTAMP(timestamp), request "
        "FROM message_handler_requests "
        "WHERE leased_by=%s AND leased_until=FROM_UNIXTIME(%s) LIMIT %s",
        (id_str, expiry_str, updated),
    )
    res = []
    for timestamp, request in cursor.fetchall():
      req = objects_pb2.MessageHandlerRequest()
      req.ParseFromString(request)
      req.timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(timestamp)
      req.leased_until = expiry.AsMicrosecondsSinceEpoch()
      req.leased_by = id_str
      res.append(req)
    return res

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteFlowObject(
      self,
      flow_obj: flows_pb2.Flow,
      allow_update: bool = True,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a flow object to the database."""
    assert cursor is not None

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
        flow_obj.cpu_time_used.user_cpu_time
    )
    system_cpu_time_used_micros = db_utils.SecondsToMicros(
        flow_obj.cpu_time_used.system_cpu_time
    )

    args = {
        "client_id": db_utils.ClientIDToInt(flow_obj.client_id),
        "flow_id": db_utils.FlowIDToInt(flow_obj.flow_id),
        "long_flow_id": flow_obj.long_flow_id,
        "name": flow_obj.flow_class_name,
        "creator": flow_obj.creator,
        "flow": flow_obj.SerializeToString(),
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

  def _FlowObjectFromRow(self, row) -> flows_pb2.Flow:
    """Generates a flow object from a database row."""
    datetime = mysql_utils.TimestampToRDFDatetime
    cpu_time = db_utils.MicrosToSeconds

    # fmt: off
    (client_id, flow_id, long_flow_id, parent_flow_id, parent_hunt_id,
     name, creator,
     flow, flow_state,
     client_crash_info,
     next_request_to_process,
     processing_deadline, processing_on, processing_since,
     user_cpu_time, system_cpu_time, network_bytes_sent, num_replies_sent,
     timestamp, last_update_timestamp) = row
    # fmt: on

    flow_obj = flows_pb2.Flow()
    flow_obj.ParseFromString(flow)

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
    if flow_state not in [None, flows_pb2.Flow.FlowState.UNSET]:
      flow_obj.flow_state = flow_state
    if next_request_to_process:
      flow_obj.next_request_to_process = next_request_to_process

    # In case the create time is not stored in the serialized flow (which might
    # be the case), we fallback to the timestamp information stored in the
    # column.
    if not flow_obj.HasField("create_time"):
      flow_obj.create_time = int(datetime(timestamp))
    flow_obj.last_update_time = int(datetime(last_update_timestamp))

    if client_crash_info is not None:
      flow_obj.client_crash_info.ParseFromString(client_crash_info)

    flow_obj.ClearField("processing_on")
    if processing_on is not None:
      flow_obj.processing_on = processing_on

    flow_obj.ClearField("processing_since")
    if processing_since is not None:
      flow_obj.processing_since = int(datetime(processing_since))

    flow_obj.ClearField("processing_deadline")
    if processing_deadline is not None:
      flow_obj.processing_deadline = int(datetime(processing_deadline))

    flow_obj.cpu_time_used.user_cpu_time = cpu_time(user_cpu_time)
    flow_obj.cpu_time_used.system_cpu_time = cpu_time(system_cpu_time)
    flow_obj.network_bytes_sent = network_bytes_sent

    if num_replies_sent:
      flow_obj.num_replies_sent = num_replies_sent

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

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowObject(
      self,
      client_id: str,
      flow_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> flows_pb2.Flow:
    """Reads a flow object from the database."""
    assert cursor is not None

    query = (
        f"SELECT {self.FLOW_DB_FIELDS} "
        "FROM flows WHERE client_id=%s AND flow_id=%s"
    )
    cursor.execute(
        query,
        [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)],
    )
    result = cursor.fetchall()
    if not result:
      raise db.UnknownFlowError(client_id, flow_id)
    (row,) = result
    return self._FlowObjectFromRow(row)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllFlowObjects(
      self,
      client_id: Optional[str] = None,
      parent_flow_id: Optional[str] = None,
      min_create_time: Optional[rdfvalue.RDFDatetime] = None,
      max_create_time: Optional[rdfvalue.RDFDatetime] = None,
      include_child_flows: bool = True,
      not_created_by: Optional[Iterable[str]] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> list[flows_pb2.Flow]:
    """Returns all flow objects."""
    assert cursor is not None

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

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def LeaseFlowForProcessing(
      self,
      client_id: str,
      flow_id: str,
      processing_time: rdfvalue.Duration,
      cursor: Optional[cursors.Cursor] = None,
  ) -> flows_pb2.Flow:
    """Marks a flow as being processed on this worker and returns it."""
    assert cursor is not None

    query = (
        f"SELECT {self.FLOW_DB_FIELDS} "
        "FROM flows WHERE client_id=%s AND flow_id=%s"
    )
    cursor.execute(
        query,
        [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)],
    )
    response = cursor.fetchall()
    if not response:
      raise db.UnknownFlowError(client_id, flow_id)

    (row,) = response
    flow = self._FlowObjectFromRow(row)

    now = rdfvalue.RDFDatetime.Now()
    if flow.processing_on and flow.processing_deadline > int(now):
      raise ValueError(
          "Flow %s on client %s is already being processed."
          % (flow_id, client_id)
      )

    if flow.parent_hunt_id is not None:

      query = "SELECT hunt_state FROM hunts WHERE hunt_id=%s"
      args = [db_utils.HuntIDToInt(flow.parent_hunt_id)]
      rows_found = cursor.execute(query, args)
      if rows_found == 1:
        (hunt_state,) = cursor.fetchone()
        if (
            hunt_state is not None
            and not models_hunts.IsHuntSuitableForFlowProcessing(hunt_state)
        ):
          raise db.ParentHuntIsNotRunningError(
              client_id, flow_id, flow.parent_hunt_id, hunt_state
          )

    update_query = (
        "UPDATE flows SET "
        "processing_on=%s, "
        "processing_since=FROM_UNIXTIME(%s), "
        "processing_deadline=FROM_UNIXTIME(%s) "
        "WHERE client_id=%s and flow_id=%s"
    )
    processing_deadline = now + processing_time
    process_id_string = utils.ProcessIdString()

    args = [
        process_id_string,
        mysql_utils.RDFDatetimeToTimestamp(now),
        mysql_utils.RDFDatetimeToTimestamp(processing_deadline),
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id),
    ]
    cursor.execute(update_query, args)

    # This needs to happen after we are sure that the write has succeeded.
    flow.processing_on = process_id_string
    flow.processing_since = int(now)
    flow.processing_deadline = int(processing_deadline)
    return flow

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def UpdateFlow(
      self,
      client_id: str,
      flow_id: str,
      flow_obj: Union[
          flows_pb2.Flow, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      flow_state: Union[
          flows_pb2.Flow.FlowState.ValueType, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      client_crash_info: Union[
          jobs_pb2.ClientCrash, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      processing_on: Optional[
          Union[str, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
      processing_since: Optional[
          Union[rdfvalue.RDFDatetime, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
      processing_deadline: Optional[
          Union[rdfvalue.RDFDatetime, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Updates flow objects in the database."""
    assert cursor is not None

    updates = []
    args = []
    if isinstance(flow_obj, flows_pb2.Flow):
      updates.append("flow=%s")
      args.append(flow_obj.SerializeToString())
      updates.append("flow_state=%s")
      args.append(int(flow_obj.flow_state))
      updates.append("user_cpu_time_used_micros=%s")
      args.append(
          db_utils.SecondsToMicros(flow_obj.cpu_time_used.user_cpu_time)
      )
      updates.append("system_cpu_time_used_micros=%s")
      args.append(
          db_utils.SecondsToMicros(flow_obj.cpu_time_used.system_cpu_time)
      )
      updates.append("network_bytes_sent=%s")
      args.append(flow_obj.network_bytes_sent)
      updates.append("num_replies_sent=%s")
      args.append(flow_obj.num_replies_sent)

    if isinstance(flow_state, flows_pb2.Flow.FlowState.ValueType):
      updates.append("flow_state=%s")
      args.append(int(flow_state))
    if isinstance(client_crash_info, jobs_pb2.ClientCrash):
      updates.append("client_crash_info=%s")
      args.append(client_crash_info.SerializeToString())
    if (
        isinstance(processing_on, str)
        and processing_on is not db.Database.UNCHANGED
    ) or processing_on is None:
      updates.append("processing_on=%s")
      args.append(processing_on)
    if (
        isinstance(processing_since, rdfvalue.RDFDatetime)
        or processing_since is None
    ):
      updates.append("processing_since=FROM_UNIXTIME(%s)")
      args.append(mysql_utils.RDFDatetimeToTimestamp(processing_since))
    if (
        isinstance(processing_deadline, rdfvalue.RDFDatetime)
        or processing_deadline is None
    ):
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

  def _WriteFlowProcessingRequests(
      self,
      requests: Sequence[flows_pb2.FlowProcessingRequest],
      cursor: Optional[cursors.Cursor],
  ) -> None:
    """Returns a (query, args) tuple that inserts the given requests."""
    assert cursor is not None

    templates = []
    args = []
    for req in requests:
      templates.append("(%s, %s, %s, FROM_UNIXTIME(%s))")
      args.append(db_utils.ClientIDToInt(req.client_id))
      args.append(db_utils.FlowIDToInt(req.flow_id))
      args.append(req.SerializeToString())
      if req.delivery_time:
        args.append(
            mysql_utils.MicrosecondsSinceEpochToTimestamp(req.delivery_time)
        )
      else:
        args.append(None)

    query = (
        "INSERT INTO flow_processing_requests "
        "(client_id, flow_id, request, delivery_time) VALUES "
    )
    query += ", ".join(templates)
    cursor.execute(query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteFlowRequests(
      self,
      requests: Collection[flows_pb2.FlowRequest],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a list of flow requests to the database."""
    assert cursor is not None

    args = []
    templates = []
    flow_keys = []
    needs_processing = {}

    for r in requests:
      if r.needs_processing:
        needs_processing.setdefault((r.client_id, r.flow_id), []).append(r)

      start_time = None
      if r.start_time:
        start_time = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            r.start_time
        ).AsDatetime()

      flow_keys.append((r.client_id, r.flow_id))
      templates.append("(%s, %s, %s, %s, %s, %s, %s, %s)")
      args.extend([
          db_utils.ClientIDToInt(r.client_id),
          db_utils.FlowIDToInt(r.flow_id),
          r.request_id,
          r.needs_processing,
          r.callback_state,
          r.next_response_id,
          start_time,
          r.SerializeToString(),
      ])

    if needs_processing:
      flow_processing_requests = []
      nr_conditions = []
      nr_args = []
      for client_id, flow_id in needs_processing:
        nr_conditions.append("(client_id=%s AND flow_id=%s)")
        nr_args.append(db_utils.ClientIDToInt(client_id))
        nr_args.append(db_utils.FlowIDToInt(flow_id))

      nr_query = (
          "SELECT client_id, flow_id, next_request_to_process FROM flows WHERE "
      )
      nr_query += " OR ".join(nr_conditions)

      cursor.execute(nr_query, nr_args)

      db_result = cursor.fetchall()
      for client_id_int, flow_id_int, next_request_to_process in db_result:
        client_id = db_utils.IntToClientID(client_id_int)
        flow_id = db_utils.IntToFlowID(flow_id_int)
        candidate_requests = needs_processing.get((client_id, flow_id), [])
        for r in candidate_requests:
          if next_request_to_process == r.request_id or r.start_time:
            flow_processing_request = flows_pb2.FlowProcessingRequest(
                client_id=client_id,
                flow_id=flow_id,
            )
            if r.start_time:
              flow_processing_request.delivery_time = r.start_time
            flow_processing_requests.append(flow_processing_request)

      if flow_processing_requests:
        self._WriteFlowProcessingRequests(flow_processing_requests, cursor)

    query = (
        "INSERT INTO flow_requests "
        "(client_id, flow_id, request_id, needs_processing, "
        "callback_state, next_response_id, start_time, request) "
        "VALUES "
    )
    query += ", ".join(templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(flow_keys, cause=e)

  def _WriteResponses(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
      cursor: Optional[cursors.Cursor],
  ) -> None:
    """Builds the writes to store the given responses in the db."""
    assert cursor is not None

    query = (
        "INSERT IGNORE INTO flow_responses "
        "(client_id, flow_id, request_id, response_id, "
        "response, status, iterator, timestamp) VALUES "
    )

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
      if isinstance(r, flows_pb2.FlowResponse):
        args.append(r.SerializeToString())
        args.append("")
        args.append("")
      elif isinstance(r, flows_pb2.FlowStatus):
        args.append("")
        args.append(r.SerializeToString())
        args.append("")
      elif isinstance(r, flows_pb2.FlowIterator):
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
        logging.warning("Response for unknown request: %s", responses[0])

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def _WriteFlowResponsesAndExpectedUpdates(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ]
      ],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a flow responses and updates flow requests expected counts."""
    assert cursor is not None

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
      if isinstance(r, flows_pb2.FlowStatus):
        args = {
            "client_id": db_utils.ClientIDToInt(r.client_id),
            "flow_id": db_utils.FlowIDToInt(r.flow_id),
            "request_id": r.request_id,
            "responses_expected": r.response_id,
        }
        cursor.execute(query, args)

  def _ReadFlowResponseCounts(
      self,
      request_keys: set[tuple[str, str, int]],
      cursor: Optional[cursors.Cursor] = None,
  ) -> Mapping[tuple[str, str, str], int]:
    """Reads counts of responses for the given requests."""
    assert cursor is not None

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
      request_key = (
          db_utils.IntToClientID(client_id_int),
          db_utils.IntToFlowID(flow_id_int),
          request_id,
      )
      response_counts[request_key] = count
    return response_counts

  def _ReadAndLockNextRequestsToProcess(
      self,
      flow_keys: set[tuple[str, str]],
      cursor: Optional[cursors.Cursor] = None,
  ) -> Mapping[tuple[str, str], str]:
    """Reads and locks the next_request_to_process for a number of flows."""
    assert cursor is not None

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
    for (
        client_id_int,
        flow_id_int,
        next_request,
    ) in cursor.fetchall():
      flow_key = (
          db_utils.IntToClientID(client_id_int),
          db_utils.IntToFlowID(flow_id_int),
      )
      next_requests[flow_key] = next_request

    return next_requests

  def _ReadLockAndUpdateAffectedRequests(
      self,
      request_keys: set[tuple[str, str, int]],
      response_counts: Mapping[tuple[str, str, str], int],
      cursor: Optional[cursors.Cursor] = None,
  ) -> Mapping[tuple[str, str, str], flows_pb2.FlowRequest]:
    """Reads, locks, and updates completed requests."""
    assert cursor is not None

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
            callback_agnostic_condition_template
        )
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
      request_key = (
          db_utils.IntToClientID(client_id_int),
          db_utils.IntToFlowID(flow_id_int),
          request_id,
      )
      parsed_request = flows_pb2.FlowRequest()
      parsed_request.ParseFromString(request)

      affected_requests[request_key] = parsed_request

    query = """
    UPDATE flow_requests
    SET needs_processing = TRUE
    WHERE ({conditions}) AND NOT needs_processing
    """
    query = query.format(conditions=" OR ".join(callback_agnostic_conditions))
    cursor.execute(query, args)

    return affected_requests

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def _UpdateRequestsAndScheduleFPRs(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Updates requests and writes FlowProcessingRequests if needed."""
    assert cursor is not None

    request_keys = set(
        (r.client_id, r.flow_id, r.request_id) for r in responses
    )
    flow_keys = set((r.client_id, r.flow_id) for r in responses)

    response_counts = self._ReadFlowResponseCounts(request_keys, cursor)

    next_requests = self._ReadAndLockNextRequestsToProcess(flow_keys, cursor)

    affected_requests = self._ReadLockAndUpdateAffectedRequests(
        request_keys, response_counts, cursor
    )

    if not affected_requests:
      return

    fprs_to_write = []
    for request_key, request in affected_requests.items():
      client_id, flow_id, request_id = request_key
      if next_requests[(client_id, flow_id)] == request_id:
        flow_processing_request = flows_pb2.FlowProcessingRequest(
            client_id=request.client_id,
            flow_id=request.flow_id,
        )
        if request.HasField("start_time"):
          flow_processing_request.delivery_time = request.start_time

        fprs_to_write.append(flow_processing_request)

    if fprs_to_write:
      self._WriteFlowProcessingRequests(fprs_to_write, cursor)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowResponses(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
  ) -> None:
    """Writes FlowResponse/FlowStatus/FlowIterator and updates corresponding requests."""

    if not responses:
      return

    for batch in collection.Batch(responses, self._WRITE_ROWS_BATCH_SIZE):
      self._WriteFlowResponsesAndExpectedUpdates(batch)
      self._UpdateRequestsAndScheduleFPRs(batch)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def UpdateIncrementalFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      next_response_id_updates: Mapping[int, int],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Updates next response ids of given requests."""
    assert cursor is not None

    if not next_response_id_updates:
      return

    for request_id, next_response_id in next_response_id_updates.items():
      query = (
          "UPDATE flow_requests SET next_response_id=%s WHERE "
          "client_id=%s AND flow_id=%s AND request_id=%s"
      )
      args = [
          next_response_id,
          db_utils.ClientIDToInt(client_id),
          db_utils.FlowIDToInt(flow_id),
          request_id,
      ]
      cursor.execute(query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteFlowRequests(
      self,
      requests: Sequence[flows_pb2.FlowRequest],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Deletes a list of flow requests from the database."""
    assert cursor is not None

    if not requests:
      return

    for batch in collection.Batch(requests, self._DELETE_ROWS_BATCH_SIZE):
      # Each iteration might delete more than BATCH_SIZE flow_responses.
      # This is acceptable, because batching should only prevent the statement
      # size from growing too large.
      args = []

      for r in batch:
        args.append(db_utils.ClientIDToInt(r.client_id))
        args.append(db_utils.FlowIDToInt(r.flow_id))
        args.append(r.request_id)

      key_match_list = ", ".join(("(%s, %s, %s)",) * len(batch))
      request_query = f"""
        DELETE
          FROM flow_requests
         WHERE (client_id, flow_id, request_id) IN ({key_match_list})
      """
      response_query = f"""
        DELETE
          FROM flow_responses
         WHERE (client_id, flow_id, request_id) IN ({key_match_list})
      """

      cursor.execute(response_query, args)
      cursor.execute(request_query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Iterable[
      tuple[
          flows_pb2.FlowRequest,
          dict[
              int,
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ]
  ]:
    """Reads all requests and responses for a given flow from the database."""
    assert cursor is not None

    query = (
        "SELECT request, needs_processing, responses_expected, "
        "callback_state, next_response_id, UNIX_TIMESTAMP(timestamp) "
        "FROM flow_requests WHERE client_id=%s AND flow_id=%s"
    )

    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]
    cursor.execute(query, args)

    requests = []
    for (
        req,
        needs_processing,
        resp_expected,
        callback_state,
        next_response_id,
        ts,
    ) in cursor.fetchall():
      request = flows_pb2.FlowRequest()
      request.ParseFromString(req)
      request.needs_processing = needs_processing
      if resp_expected is not None:
        request.nr_responses_expected = resp_expected
      request.callback_state = callback_state
      request.next_response_id = next_response_id
      request.timestamp = int(mysql_utils.TimestampToRDFDatetime(ts))
      requests.append(request)

    query = (
        "SELECT response, status, iterator, UNIX_TIMESTAMP(timestamp) "
        "FROM flow_responses WHERE client_id=%s AND flow_id=%s"
    )
    cursor.execute(query, args)

    responses = {}
    for res, status, iterator, ts in cursor.fetchall():
      if status:
        response = flows_pb2.FlowStatus()
        response.ParseFromString(status)
      elif iterator:
        response = flows_pb2.FlowIterator()
        response.ParseFromString(iterator)
      else:
        response = flows_pb2.FlowResponse()
        response.ParseFromString(res)
      response.timestamp = int(mysql_utils.TimestampToRDFDatetime(ts))
      responses.setdefault(response.request_id, {})[
          response.response_id
      ] = response

    ret = []
    for req in sorted(requests, key=lambda r: r.request_id):
      ret.append((req, responses.get(req.request_id, {})))
    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Deletes all requests and responses for a given flow from the database."""
    assert cursor is not None

    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]
    res_query = "DELETE FROM flow_responses WHERE client_id=%s AND flow_id=%s"
    cursor.execute(res_query, args)
    req_query = "DELETE FROM flow_requests WHERE client_id=%s AND flow_id=%s"
    cursor.execute(req_query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> dict[
      int,
      tuple[
          flows_pb2.FlowRequest,
          Sequence[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ]:
    """Reads all requests for a flow that can be processed by the worker."""
    assert cursor is not None

    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    query = (
        "SELECT response, status, iterator, UNIX_TIMESTAMP(timestamp) "
        "FROM flow_responses "
        "WHERE client_id=%s AND flow_id=%s"
    )
    cursor.execute(query, args)

    responses = {}
    for res, status, iterator, ts in cursor.fetchall():
      if status:
        response = flows_pb2.FlowStatus()
        response.ParseFromString(status)
      elif iterator:
        response = flows_pb2.FlowIterator()
        response.ParseFromString(iterator)
      else:
        response = flows_pb2.FlowResponse()
        response.ParseFromString(res)
      response.timestamp = int(mysql_utils.TimestampToRDFDatetime(ts))
      responses.setdefault(response.request_id, []).append(response)

    query = (
        "SELECT request, needs_processing, responses_expected, "
        "callback_state, next_response_id, "
        "UNIX_TIMESTAMP(timestamp) "
        "FROM flow_requests "
        "WHERE client_id=%s AND flow_id=%s"
    )
    cursor.execute(query, args)

    requests = {}
    for (
        req,
        needs_processing,
        responses_expected,
        callback_state,
        next_response_id,
        ts,
    ) in cursor.fetchall():
      request = flows_pb2.FlowRequest()
      request.ParseFromString(req)
      request.needs_processing = needs_processing
      if responses_expected is not None:
        request.nr_responses_expected = responses_expected
      request.callback_state = callback_state
      request.next_response_id = next_response_id
      request.timestamp = int(mysql_utils.TimestampToRDFDatetime(ts))
      requests[request.request_id] = (
          request,
          sorted(
              responses.get(request.request_id, []), key=lambda r: r.response_id
          ),
      )

    return requests

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def ReleaseProcessedFlow(
      self,
      flow_obj: flows_pb2.Flow,
      cursor: Optional[cursors.Cursor] = None,
  ) -> bool:
    """Releases a flow that the worker was processing to the database."""
    assert cursor is not None

    update_query = """
    UPDATE flows
    LEFT OUTER JOIN (
      SELECT client_id, flow_id, needs_processing
      FROM flow_requests
      WHERE
        client_id = %(client_id)s AND
        flow_id = %(flow_id)s AND
        request_id = %(next_request_to_process)s AND
        (start_time IS NULL OR start_time < NOW(6)) AND
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
    clone = flows_pb2.Flow()
    clone.CopyFrom(flow_obj)
    clone.ClearField("processing_on")
    clone.ClearField("processing_since")
    clone.ClearField("processing_deadline")

    args = {
        "client_id": db_utils.ClientIDToInt(flow_obj.client_id),
        "flow": clone.SerializeToString(),
        "flow_id": db_utils.FlowIDToInt(flow_obj.flow_id),
        "flow_state": int(clone.flow_state),
        "network_bytes_sent": flow_obj.network_bytes_sent,
        "next_request_to_process": flow_obj.next_request_to_process,
        "num_replies_sent": flow_obj.num_replies_sent,
        "system_cpu_time_used_micros": db_utils.SecondsToMicros(
            flow_obj.cpu_time_used.system_cpu_time
        ),
        "user_cpu_time_used_micros": db_utils.SecondsToMicros(
            flow_obj.cpu_time_used.user_cpu_time
        ),
    }
    rows_updated = cursor.execute(update_query, args)
    return rows_updated == 1

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteFlowProcessingRequests(
      self,
      requests: Sequence[flows_pb2.FlowProcessingRequest],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a list of flow processing requests to the database."""
    self._WriteFlowProcessingRequests(requests, cursor)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowProcessingRequests(
      self,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.FlowProcessingRequest]:
    """Reads all flow processing requests from the database."""
    assert cursor is not None

    query = (
        "SELECT request, UNIX_TIMESTAMP(timestamp) "
        "FROM flow_processing_requests"
    )
    cursor.execute(query)

    res = []
    for serialized_request, ts in cursor.fetchall():
      req = flows_pb2.FlowProcessingRequest()
      req.ParseFromString(serialized_request)
      req.creation_time = int(mysql_utils.TimestampToRDFDatetime(ts))
      res.append(req)
    return res

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def AckFlowProcessingRequests(
      self,
      requests: Iterable[flows_pb2.FlowProcessingRequest],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Deletes a list of flow processing requests from the database."""
    assert cursor is not None

    if not requests:
      return

    query = "DELETE FROM flow_processing_requests WHERE "

    conditions = []
    args = []
    for r in requests:
      conditions.append(
          "(client_id=%s AND flow_id=%s AND timestamp=FROM_UNIXTIME(%s))"
      )
      args.append(db_utils.ClientIDToInt(r.client_id))
      args.append(db_utils.FlowIDToInt(r.flow_id))
      args.append(
          mysql_utils.MicrosecondsSinceEpochToTimestamp(r.creation_time)
      )

    query += " OR ".join(conditions)
    cursor.execute(query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteAllFlowProcessingRequests(
      self, cursor: Optional[cursors.Cursor] = None
  ) -> None:
    """Deletes all flow processing requests from the database."""
    assert cursor is not None

    query = "DELETE FROM flow_processing_requests WHERE true"
    cursor.execute(query)

  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def _LeaseFlowProcessingRequests(
      self, limit: int, cursor=None
  ) -> Sequence[flows_pb2.FlowProcessingRequest]:
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
        "limit": limit,
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
      req = flows_pb2.FlowProcessingRequest()
      req.ParseFromString(request)
      req.creation_time = mysql_utils.TimestampToMicrosecondsSinceEpoch(
          timestamp
      )
      res.append(req)

    return res

  _FLOW_REQUEST_POLL_TIME_SECS = 3

  def _FlowProcessingRequestHandlerLoop(
      self, handler: Callable[[flows_pb2.FlowProcessingRequest], None]
  ) -> None:
    """The main loop for the flow processing request queue."""
    self.flow_processing_request_handler_pool.Start()

    while not self.flow_processing_request_handler_stop:
      thread_pool = self.flow_processing_request_handler_pool
      free_threads = thread_pool.max_threads - thread_pool.busy_threads
      if free_threads == 0:
        time.sleep(self._FLOW_REQUEST_POLL_TIME_SECS)
        continue
      try:
        msgs = self._LeaseFlowProcessingRequests(free_threads)
        if msgs:
          for m in msgs:
            self.flow_processing_request_handler_pool.AddTask(
                target=handler, args=(m,)
            )
        else:
          time.sleep(self._FLOW_REQUEST_POLL_TIME_SECS)

      except Exception as e:  # pylint: disable=broad-except
        logging.exception("_FlowProcessingRequestHandlerLoop raised %s.", e)
        time.sleep(self._FLOW_REQUEST_POLL_TIME_SECS)

    self.flow_processing_request_handler_pool.Stop()

  def RegisterFlowProcessingHandler(
      self, handler: Callable[[flows_pb2.FlowProcessingRequest], None]
  ) -> None:
    """Registers a handler to receive flow processing messages."""
    self.UnregisterFlowProcessingHandler()

    if handler:
      self.flow_processing_request_handler_stop = False
      self.flow_processing_request_handler_thread = threading.Thread(
          name="flow_processing_request_handler",
          target=self._FlowProcessingRequestHandlerLoop,
          args=(handler,),
      )
      self.flow_processing_request_handler_thread.daemon = True
      self.flow_processing_request_handler_thread.start()

  def UnregisterFlowProcessingHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered flow processing handler."""
    if self.flow_processing_request_handler_thread:
      self.flow_processing_request_handler_stop = True
      self.flow_processing_request_handler_thread.join(timeout)
      if self.flow_processing_request_handler_thread.is_alive():
        raise RuntimeError("Flow processing handler did not join in time.")
      self.flow_processing_request_handler_thread = None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def _WriteFlowResultsOrErrors(
      self,
      table_name: str,
      results: Sequence[Union[flows_pb2.FlowResult, flows_pb2.FlowError]],
      cursor: Optional[cursors.Cursor] = None,
  ):
    """Writes flow results/errors for a given flow."""
    assert cursor is not None

    query = f"""
      INSERT INTO {table_name} (
        client_id, flow_id, hunt_id, timestamp, payload, payload_any, type, tag
      ) VALUES
    """
    templates = []

    args = []
    for r in results:
      templates.append("(%s, %s, %s, FROM_UNIXTIME(%s), %s, %s, %s, %s)")
      args.append(db_utils.ClientIDToInt(r.client_id))
      args.append(db_utils.FlowIDToInt(r.flow_id))
      if r.hunt_id:
        args.append(db_utils.HuntIDToInt(r.hunt_id))
      else:
        args.append(0)
      args.append(
          mysql_utils.RDFDatetimeToTimestamp(rdfvalue.RDFDatetime.Now())
      )
      # TODO: Remove writing to payload column after a transition
      # period.
      args.append(r.payload.value)
      args.append(r.payload.SerializeToString())
      args.append(db_utils.TypeURLToRDFTypeName(r.payload.type_url))
      args.append(r.tag)

    query += ",".join(templates)

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as e:
      raise db.AtLeastOneUnknownFlowError(
          [(r.client_id, r.flow_id) for r in results], cause=e
      )

  def WriteFlowResults(self, results: Sequence[flows_pb2.FlowResult]) -> None:
    """Writes flow results for a given flow."""
    self._WriteFlowResultsOrErrors("flow_results", results)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def _ReadFlowResultsOrErrors(
      self,
      table_name: str,
      result_cls: Union[type[flows_pb2.FlowResult], type[flows_pb2.FlowError]],
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_substring: Optional[str] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Union[Sequence[flows_pb2.FlowResult], Sequence[flows_pb2.FlowError]]:
    """Reads flow results/errors of a given flow using given query options."""
    assert cursor is not None

    client_id_int = db_utils.ClientIDToInt(client_id)
    flow_id_int = db_utils.FlowIDToInt(flow_id)

    query = f"""
        SELECT payload, payload_any, type, UNIX_TIMESTAMP(timestamp), tag, hunt_id
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
    for (
        serialized_payload,
        payload_any,
        payload_type,
        ts,
        tag,
        hid,
    ) in cursor.fetchall():
      if payload_any is not None:
        payload = any_pb2.Any.FromString(payload_any)
      elif payload_type in rdfvalue.RDFValue.classes:
        payload = any_pb2.Any(
            type_url=db_utils.RDFTypeNameToTypeURL(payload_type),
            value=serialized_payload,
        )
      else:
        unrecognized = objects_pb2.SerializedValueOfUnrecognizedType(
            type_name=payload_type, value=serialized_payload
        )
        payload = any_pb2.Any()
        payload.Pack(unrecognized)

      timestamp = mysql_utils.TimestampToMicrosecondsSinceEpoch(ts)
      result = result_cls(
          client_id=db_utils.IntToClientID(client_id_int),
          flow_id=db_utils.IntToFlowID(flow_id_int),
          timestamp=timestamp,
      )
      result.payload.CopyFrom(payload)

      if hid:
        result.hunt_id = db_utils.IntToHuntID(hid)

      if tag:
        result.tag = tag

      ret.append(result)

    return ret

  def ReadFlowResults(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads flow results of a given flow using given query options."""
    if with_proto_type_url is not None:
      with_type = db_utils.TypeURLToRDFTypeName(with_proto_type_url)

    return self._ReadFlowResultsOrErrors(
        "flow_results",
        flows_pb2.FlowResult,
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_substring=with_substring,
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def _CountFlowResultsOrErrors(
      self,
      table_name: str,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> int:
    """Counts flow results/errors of a given flow using given query options."""
    assert cursor is not None

    query = (
        "SELECT COUNT(*) "
        f"FROM {table_name} "
        f"FORCE INDEX ({table_name}_by_client_id_flow_id_timestamp) "
        "WHERE client_id = %s AND flow_id = %s "
    )
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    if with_tag is not None:
      query += "AND tag = %s "
      args.append(with_tag)

    if with_type is not None:
      query += "AND type = %s "
      args.append(with_type)

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  def CountFlowResults(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts flow results of a given flow using given query options."""
    return self._CountFlowResultsOrErrors(
        "flow_results",
        client_id,
        flow_id,
        with_tag=with_tag,
        with_type=with_type,
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def _CountFlowResultsOrErrorsByType(
      self,
      table_name: str,
      client_id: str,
      flow_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Mapping[str, int]:
    """Returns counts of flow results/errors grouped by result type."""
    assert cursor is not None

    query = (
        f"SELECT type, COUNT(*) FROM {table_name} "
        f"FORCE INDEX ({table_name}_by_client_id_flow_id_timestamp) "
        "WHERE client_id = %s AND flow_id = %s "
        "GROUP BY type"
    )
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    cursor.execute(query, args)

    return dict(cursor.fetchall())

  def CountFlowResultsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow results grouped by result type."""
    return self._CountFlowResultsOrErrorsByType(
        "flow_results", client_id, flow_id
    )

  def CountFlowResultsByProtoTypeUrl(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow results grouped by proto result type."""
    rdf_counts = self._CountFlowResultsOrErrorsByType(
        "flow_results", client_id, flow_id
    )
    proto_counts = {}
    for rdf_type, count in rdf_counts.items():
      proto_type = db_utils.RDFTypeNameToTypeURL(rdf_type)
      proto_counts[proto_type] = count
    return proto_counts

  def WriteFlowErrors(self, errors: Sequence[flows_pb2.FlowError]) -> None:
    """Writes flow errors for a given flow."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    self._WriteFlowResultsOrErrors("flow_errors", errors)

  def ReadFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowError]:
    """Reads flow errors of a given flow using given query options."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    return self._ReadFlowResultsOrErrors(
        "flow_errors",
        flows_pb2.FlowError,
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
    )

  def CountFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
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
        with_type=with_type,
    )

  def CountFlowErrorsByType(
      self,
      client_id: str,
      flow_id: str,
  ) -> Mapping[str, int]:
    """Returns counts of flow errors grouped by error type."""
    # Errors are similar to results, as they represent a somewhat related
    # concept. Error is a kind of a negative result. Given the structural
    # similarity, we can share large chunks of implementation between
    # errors and results DB code.
    return self._CountFlowResultsOrErrorsByType(
        "flow_errors", client_id, flow_id
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteFlowLogEntry(
      self,
      entry: flows_pb2.FlowLogEntry,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a single flow log entry to the database."""
    assert cursor is not None

    query = """
    INSERT INTO flow_log_entries
                (client_id, flow_id, hunt_id, message)
         VALUES (%(client_id)s, %(flow_id)s, %(hunt_id)s, %(message)s)
    """
    args = {
        "client_id": db_utils.ClientIDToInt(entry.client_id),
        "flow_id": db_utils.FlowIDToInt(entry.flow_id),
        "message": entry.message,
    }

    if entry.hunt_id:
      args["hunt_id"] = db_utils.HuntIDToInt(entry.hunt_id)
    else:
      args["hunt_id"] = 0

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads flow log entries of a given flow using given query options."""
    assert cursor is not None

    query = (
        "SELECT message, UNIX_TIMESTAMP(timestamp) "
        "FROM flow_log_entries "
        "FORCE INDEX (flow_log_entries_by_flow) "
        "WHERE client_id = %s AND flow_id = %s "
    )
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
          flows_pb2.FlowLogEntry(
              message=message,
              timestamp=mysql_utils.TimestampToMicrosecondsSinceEpoch(
                  timestamp
              ),
          )
      )

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountFlowLogEntries(
      self,
      client_id: str,
      flow_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> int:
    """Returns number of flow log entries of a given flow."""
    assert cursor is not None

    query = (
        "SELECT COUNT(*) "
        "FROM flow_log_entries "
        "FORCE INDEX (flow_log_entries_by_flow) "
        "WHERE client_id = %s AND flow_id = %s "
    )
    args = [db_utils.ClientIDToInt(client_id), db_utils.FlowIDToInt(flow_id)]

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      request_id: int,
      logs: Mapping[int, rrg_pb2.Log],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes new log entries for a particular action request."""
    assert cursor is not None

    query = """
    INSERT
    INTO flow_rrg_logs (
      client_id, flow_id, request_id, response_id,
      log_level, log_time, log_message
    )
    VALUES (
      %(client_id)s, %(flow_id)s, %(request_id)s, %(response_id)s,
      %(log_level)s, FROM_UNIXTIME(%(log_time)s), %(log_message)s
    )
    """

    args = []

    for response_id, log in logs.items():
      args.append({
          "client_id": db_utils.ClientIDToInt(client_id),
          "flow_id": db_utils.FlowIDToInt(flow_id),
          "request_id": request_id,
          "response_id": response_id,
          "log_level": log.level,
          "log_time": mysql_utils.RDFDatetimeToTimestamp(
              rdfvalue.RDFDatetime.FromProtoTimestamp(log.timestamp),
          ),
          "log_message": log.message,
      })

    try:
      cursor.executemany(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.UnknownFlowError(client_id, flow_id, cause=error) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[rrg_pb2.Log]:
    """Reads log entries logged by actions issued by a particular flow."""
    assert cursor is not None

    query = """
    SELECT
      log_level, UNIX_TIMESTAMP(log_time), log_message
    FROM
      flow_rrg_logs
    WHERE
      client_id = %(client_id)s AND flow_id = %(flow_id)s
    ORDER BY
      request_id, response_id
    LIMIT
      %(count)s
    OFFSET
      %(offset)s
    """
    args = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "flow_id": db_utils.FlowIDToInt(flow_id),
        "offset": offset,
        "count": count,
    }
    cursor.execute(query, args)

    results: list[rrg_pb2.Log] = []

    for level, timestamp, message in cursor.fetchall():
      log = rrg_pb2.Log()
      log.level = level
      log.timestamp.CopyFrom(
          mysql_utils.TimestampToRDFDatetime(timestamp).AsProtoTimestamp()
      )
      log.message = message

      results.append(log)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteFlowOutputPluginLogEntry(
      self,
      entry: flows_pb2.FlowOutputPluginLogEntry,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes a single output plugin log entry to the database."""
    self.WriteMultipleFlowOutputPluginLogEntries([entry], cursor=cursor)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteMultipleFlowOutputPluginLogEntries(
      self,
      entries: Sequence[flows_pb2.FlowOutputPluginLogEntry],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Writes multiple output plugin log entries to the database."""
    if not entries:
      return

    assert cursor is not None

    query = """
    INSERT INTO flow_output_plugin_log_entries
                (client_id, flow_id, hunt_id, output_plugin_id,
                 log_entry_type, message)
         VALUES """

    args = []
    templates = []
    for entry in entries:
      templates.append("(%s, %s, %s, %s, %s, %s)")
      args.extend([
          db_utils.ClientIDToInt(entry.client_id),
          db_utils.FlowIDToInt(entry.flow_id),
          db_utils.HuntIDToInt(entry.hunt_id) if entry.hunt_id else None,
          db_utils.OutputPluginIDToInt(entry.output_plugin_id),
          int(entry.log_entry_type),
          entry.message,
      ])

    query += ", ".join(templates)
    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.AtLeastOneUnknownFlowError(
          [(e.client_id, e.flow_id) for e in entries], cause=error
      ) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads flow output plugin log entries."""
    assert cursor is not None

    query = (
        "SELECT log_entry_type, message, UNIX_TIMESTAMP(timestamp) "
        "FROM flow_output_plugin_log_entries "
        "FORCE INDEX (flow_output_plugin_log_entries_by_flow) "
        "WHERE client_id = %s AND flow_id = %s AND output_plugin_id = %s "
    )
    args = [
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id),
        db_utils.OutputPluginIDToInt(output_plugin_id),
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
          flows_pb2.FlowOutputPluginLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              output_plugin_id=output_plugin_id,
              log_entry_type=log_entry_type,
              message=message,
              timestamp=mysql_utils.TimestampToMicrosecondsSinceEpoch(
                  timestamp
              ),
          )
      )

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          "flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType"
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads flow output plugin log entries for all plugins of a given flow."""
    assert cursor is not None

    query = (
        "SELECT output_plugin_id, hunt_id, log_entry_type, message, "
        "UNIX_TIMESTAMP(timestamp) "
        "FROM flow_output_plugin_log_entries "
        "FORCE INDEX (flow_output_plugin_log_entries_by_flow) "
        "WHERE client_id = %s AND flow_id = %s "
    )
    args = [
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id),
    ]

    if with_type is not None:
      query += "AND log_entry_type = %s "
      args.append(int(with_type))

    query += "ORDER BY log_id ASC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)

    ret = []
    for (
        output_plugin_id,
        hunt_id,
        log_entry_type,
        message,
        timestamp,
    ) in cursor.fetchall():
      ret.append(
          flows_pb2.FlowOutputPluginLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=db_utils.IntToHuntID(hunt_id) if hunt_id else None,
              output_plugin_id=db_utils.IntToOutputPluginID(output_plugin_id),
              log_entry_type=log_entry_type,
              message=message,
              timestamp=mysql_utils.TimestampToMicrosecondsSinceEpoch(
                  timestamp
              ),
          )
      )

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> int:
    """Returns number of flow output plugin log entries of a given flow."""
    assert cursor is not None

    query = (
        "SELECT COUNT(*) "
        "FROM flow_output_plugin_log_entries "
        "FORCE INDEX (flow_output_plugin_log_entries_by_flow) "
        "WHERE client_id = %s AND flow_id = %s AND output_plugin_id = %s "
    )
    args = [
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id),
        output_plugin_id,
    ]

    if with_type is not None:
      query += "AND log_entry_type = %s"
      args.append(int(with_type))

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountAllFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      with_type: Optional[
          "flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType"
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> int:
    """Returns number of flow output plugin log entries of a given flow."""
    assert cursor is not None

    query = (
        "SELECT COUNT(*) "
        "FROM flow_output_plugin_log_entries "
        "FORCE INDEX (flow_output_plugin_log_entries_by_flow) "
        "WHERE client_id = %s AND flow_id = %s "
    )
    args = [
        db_utils.ClientIDToInt(client_id),
        db_utils.FlowIDToInt(flow_id),
    ]

    if with_type is not None:
      query += "AND log_entry_type = %s"
      args.append(int(with_type))

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteScheduledFlow(
      self,
      scheduled_flow: flows_pb2.ScheduledFlow,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """See base class."""
    assert cursor is not None

    sf = scheduled_flow

    args = {
        "client_id": db_utils.ClientIDToInt(sf.client_id),
        "creator_username_hash": mysql_utils.Hash(sf.creator),
        "scheduled_flow_id": db_utils.FlowIDToInt(sf.scheduled_flow_id),
        "flow_name": sf.flow_name,
        "flow_args": sf.flow_args.SerializeToString(),
        "runner_args": sf.runner_args.SerializeToString(),
        "create_time": mysql_utils.RDFDatetimeToTimestamp(
            rdfvalue.RDFDatetime(sf.create_time)
        ),
        "error": sf.error,
    }

    vals = mysql_utils.NamedPlaceholders(args)
    vals = vals.replace("%(create_time)s", "FROM_UNIXTIME(%(create_time)s)")

    query = """
      REPLACE INTO scheduled_flows {cols}
      VALUES {vals}
    """.format(cols=mysql_utils.Columns(args), vals=vals)

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      if "creator_username_hash" in str(error):
        raise db.UnknownGRRUserError(sf.creator, cause=error)
      elif "client_id" in str(error):
        raise db.UnknownClientError(sf.client_id, cause=error)
      raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteScheduledFlow(
      self,
      client_id: str,
      creator: str,
      scheduled_flow_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """See base class."""
    assert cursor is not None

    cursor.execute(
        """
      DELETE FROM
        scheduled_flows
      WHERE
        client_id = %s AND
        creator_username_hash = %s AND
        scheduled_flow_id = %s
      """,
        [
            db_utils.ClientIDToInt(client_id),
            mysql_utils.Hash(creator),
            db_utils.FlowIDToInt(scheduled_flow_id),
        ],
    )

    if cursor.rowcount == 0:
      raise db.UnknownScheduledFlowError(
          client_id=client_id,
          creator=creator,
          scheduled_flow_id=scheduled_flow_id,
      )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ListScheduledFlows(
      self,
      client_id: str,
      creator: str,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.ScheduledFlow]:
    """See base class."""
    assert cursor is not None

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
      flow = flows_pb2.ScheduledFlow()
      flow.client_id = db_utils.IntToClientID(row[0])
      flow.creator = row[1]
      flow.scheduled_flow_id = db_utils.IntToFlowID(row[2])
      flow.flow_name = row[3]
      flow.flow_args.ParseFromString(row[4])
      flow.runner_args.ParseFromString(row[5])
      flow.create_time = int(mysql_utils.TimestampToRDFDatetime(row[6]))
      flow.error = row[7]

      results.append(flow)

    return results
