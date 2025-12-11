#!/usr/bin/env python
"""The MySQL database methods for flow handling."""

from collections.abc import Callable, Collection, Mapping, Sequence, Set
from typing import Optional

import MySQLdb
from MySQLdb import cursors

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.models import hunts as models_hunts

_HUNT_COLUMNS_SELECT = ", ".join((
    "UNIX_TIMESTAMP(create_timestamp)",
    "UNIX_TIMESTAMP(last_update_timestamp)",
    "creator",
    "duration_micros",
    "client_rate",
    "client_limit",
    "hunt_state",
    "hunt_state_comment",
    "UNIX_TIMESTAMP(init_start_time)",
    "UNIX_TIMESTAMP(last_start_time)",
    "num_clients_at_start_time",
    "description",
    "hunt",
))

_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS = (
    "plugin_name",
    "plugin_args",
    "plugin_args_any",
    "plugin_state",
)


class MySQLDBHuntMixin(object):
  """MySQLDB mixin for flow handling."""

  FLOW_DB_FIELDS: str

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteHuntObject(
      self, hunt_obj: hunts_pb2.Hunt, cursor: Optional[cursors.Cursor] = None
  ):
    """Writes a hunt object to the database."""
    assert cursor is not None
    query = """
    INSERT INTO hunts (hunt_id, creator, description, duration_micros,
                       hunt_state,
                       client_rate, client_limit,
                       hunt)
    VALUES (%(hunt_id)s, %(creator)s, %(description)s, %(duration_micros)s,
            %(hunt_state)s,
            %(client_rate)s, %(client_limit)s,
            %(hunt)s)
    """

    args = {
        "hunt_id": db_utils.HuntIDToInt(hunt_obj.hunt_id),
        "creator": hunt_obj.creator,
        "description": hunt_obj.description,
        "duration_micros": hunt_obj.duration * 10**6,
        "hunt_state": int(hunts_pb2.Hunt.HuntState.PAUSED),
        "client_rate": hunt_obj.client_rate,
        "client_limit": hunt_obj.client_limit,
        "hunt": hunt_obj.SerializeToString(),
    }

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.DuplicatedHuntError(hunt_id=hunt_obj.hunt_id, cause=error)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def UpdateHuntObject(
      self,
      hunt_id: str,
      duration: Optional[rdfvalue.Duration] = None,
      client_rate: Optional[float] = None,
      client_limit: Optional[int] = None,
      hunt_state: Optional[hunts_pb2.Hunt.HuntState.ValueType] = None,
      hunt_state_reason: Optional[
          hunts_pb2.Hunt.HuntStateReason.ValueType
      ] = None,
      hunt_state_comment: Optional[str] = None,
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      num_clients_at_start_time: Optional[int] = None,
      cursor: Optional[cursors.Cursor] = None,
  ):
    """Updates the hunt object by applying the update function."""
    assert cursor is not None
    vals = []
    args = {}

    if duration is not None:
      vals.append("duration_micros = %(duration_micros)s")
      args["duration_micros"] = duration.microseconds

    if client_rate is not None:
      vals.append("client_rate = %(client_rate)s")
      args["client_rate"] = client_rate

    if client_limit is not None:
      vals.append("client_limit = %(client_limit)s")
      args["client_limit"] = client_limit

    if hunt_state is not None:
      vals.append("hunt_state = %(hunt_state)s")
      args["hunt_state"] = int(hunt_state)

    if hunt_state_reason is not None:
      vals.append("hunt_state_reason = %(hunt_state_reason)s")
      args["hunt_state_reason"] = int(hunt_state_reason)

    if hunt_state_comment is not None:
      vals.append("hunt_state_comment = %(hunt_state_comment)s")
      args["hunt_state_comment"] = hunt_state_comment

    if start_time is not None:
      vals.append("""
      init_start_time = IFNULL(init_start_time, FROM_UNIXTIME(%(start_time)s))
      """)
      vals.append("""
      last_start_time = FROM_UNIXTIME(%(start_time)s)
      """)
      args["start_time"] = mysql_utils.RDFDatetimeToTimestamp(start_time)

    if num_clients_at_start_time is not None:
      vals.append("num_clients_at_start_time = %(num_clients_at_start_time)s")
      args["num_clients_at_start_time"] = num_clients_at_start_time

    vals.append("last_update_timestamp = NOW(6)")

    query = """
    UPDATE hunts
       SET {updates}
     WHERE hunt_id = %(hunt_id)s
    """.format(updates=", ".join(vals))
    args["hunt_id"] = db_utils.HuntIDToInt(hunt_id)

    rows_modified = cursor.execute(query, args)
    if rows_modified == 0:
      raise db.UnknownHuntError(hunt_id)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteHuntObject(
      self,
      hunt_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Deletes a given hunt object."""
    assert cursor is not None
    query = "DELETE FROM hunts WHERE hunt_id = %s"
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    rows_deleted = cursor.execute(query, [hunt_id_int])
    if rows_deleted == 0:
      raise db.UnknownHuntError(hunt_id)

    query = "DELETE FROM hunt_output_plugins_states WHERE hunt_id = %s"
    cursor.execute(query, [hunt_id_int])

    query = """
    DELETE
      FROM approval_request
     WHERE approval_type = %(approval_type)s
       AND subject_id = %(hunt_id)s
    """
    args = {
        "approval_type": int(
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
        ),
        "hunt_id": hunt_id,
    }
    cursor.execute(query, args)

  def _HuntObjectFromRow(self, row):
    """Generates a flow object from a database row."""
    (
        create_time,
        last_update_time,
        creator,
        duration_micros,
        client_rate,
        client_limit,
        hunt_state,
        hunt_state_comment,
        init_start_time,
        last_start_time,
        num_clients_at_start_time,
        description,
        body,
    ) = row
    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.ParseFromString(body)
    hunt_obj.duration = rdfvalue.DurationSeconds.From(
        duration_micros, rdfvalue.MICROSECONDS
    ).ToInt(rdfvalue.SECONDS)

    hunt_obj.create_time = mysql_utils.TimestampToMicrosecondsSinceEpoch(
        create_time
    )
    hunt_obj.last_update_time = mysql_utils.TimestampToMicrosecondsSinceEpoch(
        last_update_time
    )

    # Checks below are needed for hunts that were written to the database before
    # respective fields became part of F1 schema.
    if creator is not None:
      hunt_obj.creator = creator

    if client_rate is not None:
      hunt_obj.client_rate = client_rate

    if client_limit is not None:
      hunt_obj.client_limit = client_limit

    if hunt_state is not None:
      hunt_obj.hunt_state = hunt_state

    if hunt_state_comment is not None:
      hunt_obj.hunt_state_comment = hunt_state_comment

    if init_start_time is not None:
      hunt_obj.init_start_time = mysql_utils.TimestampToMicrosecondsSinceEpoch(
          init_start_time
      )

    if last_start_time is not None:
      hunt_obj.last_start_time = mysql_utils.TimestampToMicrosecondsSinceEpoch(
          last_start_time
      )

    if num_clients_at_start_time is not None:
      hunt_obj.num_clients_at_start_time = num_clients_at_start_time

    if description is not None:
      hunt_obj.description = description

    return hunt_obj

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntObject(
      self, hunt_id: str, cursor: Optional[cursors.Cursor] = None
  ) -> hunts_pb2.Hunt:
    """Reads a hunt object from the database."""
    assert cursor is not None
    query = "SELECT {columns} FROM hunts WHERE hunt_id = %s".format(
        columns=_HUNT_COLUMNS_SELECT
    )

    nr_results = cursor.execute(query, [db_utils.HuntIDToInt(hunt_id)])
    if nr_results == 0:
      raise db.UnknownHuntError(hunt_id)

    hunt = self._HuntObjectFromRow(cursor.fetchone())
    return hunt

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Set[str]] = None,
      not_created_by: Optional[Set[str]] = None,
      with_states: Optional[
          Collection[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> list[hunts_pb2.Hunt]:
    """Reads multiple hunt objects from the database."""
    assert cursor is not None
    query = "SELECT {columns} FROM hunts ".format(columns=_HUNT_COLUMNS_SELECT)
    args = []

    components = []
    if with_creator is not None:
      components.append("creator = %s ")
      args.append(with_creator)

    if created_by is not None:
      # If it is an empty list of creators, return empty results.
      if not created_by:
        return []
      components.append("creator IN %s ")
      # We explicitly convert created_by into a list because the cursor
      # implementation does not know how to convert a `frozenset` to a string.
      # The cursor implementation knows how to convert lists and ordinary sets.
      args.append(list(created_by))

    if not_created_by:
      components.append("creator NOT IN %s ")
      # We explicitly convert not_created_by into a list because the cursor
      # implementation does not know how to convert a `frozenset` to a string.
      # The cursor implementation knows how to convert lists and ordinary sets.
      args.append(list(not_created_by))
    if created_after is not None:
      components.append("create_timestamp > FROM_UNIXTIME(%s) ")
      args.append(mysql_utils.RDFDatetimeToTimestamp(created_after))

    if with_description_match is not None:
      components.append("description LIKE %s")
      args.append("%" + with_description_match + "%")

    if with_states is not None:
      if not with_states:
        return []
      components.append("hunt_state IN %s ")
      args.append([int(state) for state in with_states])

    if components:
      query += "WHERE " + " AND ".join(components)

    query += " ORDER BY create_timestamp DESC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)
    return [self._HuntObjectFromRow(row) for row in cursor.fetchall()]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ListHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Set[str]] = None,
      not_created_by: Optional[Set[str]] = None,
      with_states: Optional[
          Collection[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> list[hunts_pb2.HuntMetadata]:
    """Reads metadata for hunt objects from the database."""
    assert cursor is not None
    query = """
    SELECT
      hunt_id,
      UNIX_TIMESTAMP(create_timestamp),
      UNIX_TIMESTAMP(last_update_timestamp),
      creator,
      duration_micros,
      client_rate,
      client_limit,
      hunt_state,
      hunt_state_comment,
      UNIX_TIMESTAMP(init_start_time),
      UNIX_TIMESTAMP(last_start_time),
      description
    FROM hunts """
    args = []

    components = []
    if with_creator is not None:
      components.append("creator = %s ")
      args.append(with_creator)

    if created_by is not None:
      # If it is an empty list of creators, return empty results.
      if not created_by:
        return []
      components.append("creator IN %s ")
      # We explicitly convert created_by into a list because the cursor
      # implementation does not know how to convert a `frozenset` to a string.
      # The cursor implementation knows how to convert lists and ordinary sets.
      args.append(list(created_by))

    if not_created_by:
      components.append("creator NOT IN %s ")
      # We explicitly convert not_created_by into a list because the cursor
      # implementation does not know how to convert a `frozenset` to a string.
      # The cursor implementation knows how to convert lists and ordinary sets.
      args.append(list(not_created_by))

    if created_after is not None:
      components.append("create_timestamp > FROM_UNIXTIME(%s) ")
      args.append(mysql_utils.RDFDatetimeToTimestamp(created_after))

    if with_description_match is not None:
      components.append("description LIKE %s")
      args.append("%" + with_description_match + "%")

    if with_states is not None:
      if not with_states:
        return []
      components.append("hunt_state IN %s ")
      args.append([int(state) for state in with_states])

    if components:
      query += "WHERE " + " AND ".join(components)

    query += " ORDER BY create_timestamp DESC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)
    result = []
    for row in cursor.fetchall():
      (
          hunt_id,
          create_timestamp,
          last_update_timestamp,
          creator,
          duration_micros,
          client_rate,
          client_limit,
          hunt_state,
          hunt_state_comment,
          init_start_time,
          last_start_time,
          description,
      ) = row

      hunt_metadata = hunts_pb2.HuntMetadata(
          hunt_id=db_utils.IntToHuntID(hunt_id),
          create_time=int(mysql_utils.TimestampToRDFDatetime(create_timestamp)),
          creator=creator,
          duration=rdfvalue.Duration.From(
              duration_micros, rdfvalue.MICROSECONDS
          ).ToInt(rdfvalue.SECONDS),
          client_rate=client_rate,
          client_limit=client_limit,
          hunt_state=hunt_state,
      )

      if description:
        hunt_metadata.description = description

      if hunt_state_comment:
        hunt_metadata.hunt_state_comment = hunt_state_comment

      if last_update_timestamp := mysql_utils.TimestampToRDFDatetime(
          last_update_timestamp
      ):
        hunt_metadata.last_update_time = int(last_update_timestamp)

      if init_start_time := mysql_utils.TimestampToRDFDatetime(init_start_time):
        hunt_metadata.init_start_time = int(init_start_time)

      if last_start_time := mysql_utils.TimestampToRDFDatetime(last_start_time):
        hunt_metadata.last_start_time = int(last_start_time)

      result.append(hunt_metadata)

    return result

  def _HuntOutputPluginStateFromRow(
      self, row: tuple[str, bytes, bytes, bytes]
  ) -> output_plugin_pb2.OutputPluginState:
    """Builds OutputPluginState object from a DB row."""
    (
        plugin_name,
        plugin_args_bytes,
        plugin_args_any_bytes,
        plugin_state_bytes,
    ) = row

    if plugin_args_any_bytes is not None:
      plugin_args_any = any_pb2.Any()
      plugin_args_any.ParseFromString(plugin_args_any_bytes)
    elif plugin_args_bytes is not None:
      # TODO: The db migration added a new column but didn't
      # backfill the data, so a fallback to parse the old format is implemented
      # here. Remove this fallback mechanism after  the new format has been
      # adopted and old data is not needed anymore.
      if plugin_name in rdfvalue.RDFValue.classes:
        plugin_args_any = any_pb2.Any(
            type_url=db_utils.RDFTypeNameToTypeURL(plugin_name),
            value=plugin_args_bytes,
        )
      else:
        unrecognized = objects_pb2.SerializedValueOfUnrecognizedType(
            type_name=plugin_name, value=plugin_args_bytes
        )
        plugin_args_any = any_pb2.Any()
        plugin_args_any.Pack(unrecognized)
    else:
      plugin_args_any = None

    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=plugin_name, args=plugin_args_any
    )

    plugin_state = jobs_pb2.AttributedDict()
    plugin_state.ParseFromString(plugin_state_bytes)

    return output_plugin_pb2.OutputPluginState(
        plugin_descriptor=plugin_descriptor,
        plugin_state=plugin_state,
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntOutputPluginsStates(
      self,
      hunt_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> list[output_plugin_pb2.OutputPluginState]:
    """Reads all hunt output plugins states of a given hunt."""
    assert cursor is not None

    columns = ", ".join(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS)

    query = (
        "SELECT {columns} FROM hunt_output_plugins_states "
        "WHERE hunt_id = %s".format(columns=columns)
    )
    rows_returned = cursor.execute(query, [db_utils.HuntIDToInt(hunt_id)])
    if rows_returned > 0:
      states = []
      for row in cursor.fetchall():
        states.append(self._HuntOutputPluginStateFromRow(row))
      return states

    query = "SELECT hunt_id FROM hunts WHERE hunt_id = %s"
    rows_returned = cursor.execute(query, [db_utils.HuntIDToInt(hunt_id)])
    if rows_returned == 0:
      raise db.UnknownHuntError(hunt_id)

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteHuntOutputPluginsStates(
      self,
      hunt_id: str,
      states: Collection[output_plugin_pb2.OutputPluginState],
      cursor: Optional[cursors.Cursor] = None,
  ):
    """Writes hunt output plugin states for a given hunt."""
    assert cursor is not None

    columns = ", ".join(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS)
    placeholders = mysql_utils.Placeholders(
        2 + len(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS)
    )
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    for index, state in enumerate(states):
      query = (
          "INSERT INTO hunt_output_plugins_states "
          "(hunt_id, plugin_id, {columns}) "
          "VALUES {placeholders}".format(
              columns=columns, placeholders=placeholders
          )
      )
      args = [hunt_id_int, index, state.plugin_descriptor.plugin_name]

      if state.plugin_descriptor.HasField("args"):
        args.append(state.plugin_descriptor.args.value)
        args.append(state.plugin_descriptor.args.SerializeToString())
      else:
        args.append(None)
        args.append(None)

      args.append(state.plugin_state.SerializeToString())

      try:
        cursor.execute(query, args)
      except MySQLdb.IntegrityError as e:
        raise db.UnknownHuntError(hunt_id=hunt_id, cause=e)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def UpdateHuntOutputPluginState(
      self,
      hunt_id: str,
      state_index: int,
      update_fn: Callable[
          [jobs_pb2.AttributedDict],
          jobs_pb2.AttributedDict,
      ],
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Updates hunt output plugin state for a given output plugin."""
    assert cursor is not None

    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = "SELECT hunt_id FROM hunts WHERE hunt_id = %s"
    rows_returned = cursor.execute(query, [hunt_id_int])
    if rows_returned == 0:
      raise db.UnknownHuntError(hunt_id)

    columns = ", ".join(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS)
    query = (
        "SELECT {columns} FROM hunt_output_plugins_states "
        "WHERE hunt_id = %s AND plugin_id = %s".format(columns=columns)
    )
    rows_returned = cursor.execute(query, [hunt_id_int, state_index])
    if rows_returned == 0:
      raise db.UnknownHuntOutputPluginStateError(hunt_id, state_index)

    state = self._HuntOutputPluginStateFromRow(cursor.fetchone())
    modified_plugin_state = update_fn(state.plugin_state)

    query = (
        "UPDATE hunt_output_plugins_states "
        "SET plugin_state = %s "
        "WHERE hunt_id = %s AND plugin_id = %s"
    )
    args = [modified_plugin_state.SerializeToString(), hunt_id_int, state_index]
    cursor.execute(query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntLogEntries(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads hunt log entries of a given hunt using given query options."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = (
        "SELECT client_id, flow_id, message, UNIX_TIMESTAMP(timestamp) "
        "FROM flow_log_entries "
        "FORCE INDEX(flow_log_entries_by_hunt) "
        "WHERE hunt_id = %s AND flow_id = hunt_id "
    )

    args = [hunt_id_int]

    if with_substring is not None:
      query += "AND message LIKE %s "
      args.append("%" + db_utils.EscapeWildcards(with_substring) + "%")

    query += "ORDER BY timestamp ASC LIMIT %s OFFSET %s"

    args.append(count)
    args.append(offset)

    cursor.execute(query, args)

    flow_log_entries = []
    for client_id_int, flow_id_int, message, timestamp in cursor.fetchall():
      flow_log_entries.append(
          flows_pb2.FlowLogEntry(
              client_id=db_utils.IntToClientID(client_id_int),
              flow_id=db_utils.IntToFlowID(flow_id_int),
              hunt_id=hunt_id,
              message=message,
              timestamp=mysql_utils.TimestampToMicrosecondsSinceEpoch(
                  timestamp
              ),
          )
      )

    return flow_log_entries

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntLogEntries(
      self, hunt_id: str, cursor: Optional[cursors.Cursor] = None
  ) -> int:
    """Returns number of hunt log entries of a given hunt."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = (
        "SELECT COUNT(*) FROM flow_log_entries "
        "FORCE INDEX(flow_log_entries_by_hunt) "
        "WHERE hunt_id = %s AND flow_id = hunt_id"
    )
    cursor.execute(query, [hunt_id_int])
    return cursor.fetchone()[0]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntResults(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      with_substring: Optional[str] = None,
      with_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads hunt results of a given hunt using given query options."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = """
    SELECT client_id, flow_id, payload, type,
           UNIX_TIMESTAMP(timestamp), tag
      FROM flow_results
           FORCE INDEX(flow_results_hunt_id_flow_id_timestamp)
     WHERE hunt_id = %s AND flow_id = %s
    """

    args = [hunt_id_int, hunt_id_int]

    if with_tag:
      query += "AND tag = %s "
      args.append(with_tag)

    if with_proto_type_url:
      with_type = db_utils.TypeURLToRDFTypeName(with_proto_type_url)
    if with_type:
      query += "AND type = %s "
      args.append(with_type)

    if with_substring:
      query += "AND payload LIKE %s "
      args.append("%" + db_utils.EscapeWildcards(with_substring) + "%")

    if with_timestamp:
      query += "AND timestamp = FROM_UNIXTIME(%s) "
      args.append(mysql_utils.RDFDatetimeToTimestamp(with_timestamp))

    query += "ORDER BY timestamp ASC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)

    ret = []
    for (
        client_id_int,
        flow_id_int,
        serialized_payload,
        payload_type,
        timestamp,
        tag,
    ) in cursor.fetchall():

      if payload_type in rdfvalue.RDFValue.classes:
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

      result = flows_pb2.FlowResult(
          client_id=db_utils.IntToClientID(client_id_int),
          flow_id=db_utils.IntToFlowID(flow_id_int),
          hunt_id=hunt_id,
          payload=payload,
          timestamp=mysql_utils.TimestampToMicrosecondsSinceEpoch(timestamp),
      )
      if tag is not None:
        result.tag = tag

      ret.append(result)

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntResults(
      self,
      hunt_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> int:
    """Counts hunt results of a given hunt using given query options."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = """
      SELECT COUNT(*)
      FROM flow_results
      WHERE hunt_id = %s AND flow_id = %s
    """

    args = [hunt_id_int, hunt_id_int]

    if with_tag is not None:
      query += "AND tag = %s "
      args.append(with_tag)

    if with_proto_type_url is not None:
      query += "AND type = %s "
      with_type = db_utils.TypeURLToRDFTypeName(with_proto_type_url)
      args.append(with_type)
    elif with_type is not None:
      query += "AND type = %s "
      args.append(with_type)

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntResultsByType(
      self,
      hunt_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Mapping[str, int]:
    """Counts number of hunts results per type."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = (
        "SELECT type, COUNT(*) FROM flow_results "
        "WHERE hunt_id = %s GROUP BY type"
    )

    cursor.execute(query, [hunt_id_int])
    return dict(cursor.fetchall())

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntResultsByProtoTypeUrl(
      self,
      hunt_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Mapping[str, int]:
    """Returns counts of hunt results grouped by proto result type."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = (
        "SELECT type, COUNT(*) FROM flow_results "
        "WHERE hunt_id = %s GROUP BY type"
    )

    cursor.execute(query, [hunt_id_int])
    rdf_dict = dict(cursor.fetchall())
    proto_dict = {}
    for rdf_type, count in rdf_dict.items():
      proto_type_url = db_utils.RDFTypeNameToTypeURL(rdf_type)
      proto_dict[proto_type_url] = count
    return proto_dict

  def _HuntFlowCondition(self, condition):
    """Builds an SQL condition matching db.HuntFlowsCondition."""
    if condition == db.HuntFlowsCondition.UNSET:
      return "", []
    elif condition == db.HuntFlowsCondition.FAILED_FLOWS_ONLY:
      return (
          "AND flow_state = %s ",
          [int(flows_pb2.Flow.FlowState.ERROR)],
      )
    elif condition == db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY:
      return (
          "AND flow_state = %s ",
          [int(flows_pb2.Flow.FlowState.FINISHED)],
      )
    elif condition == db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY:
      return (
          "AND (flow_state = %s OR flow_state = %s) ",
          [
              int(flows_pb2.Flow.FlowState.FINISHED),
              int(flows_pb2.Flow.FlowState.ERROR),
          ],
      )
    elif condition == db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY:
      return (
          "AND flow_state = %s ",
          [int(flows_pb2.Flow.FlowState.RUNNING)],
      )
    elif condition == db.HuntFlowsCondition.CRASHED_FLOWS_ONLY:
      return (
          "AND flow_state = %s ",
          [int(flows_pb2.Flow.FlowState.CRASHED)],
      )
    else:
      raise ValueError("Invalid condition value: %r" % condition)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntFlows(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      filter_condition: db.HuntFlowsCondition = db.HuntFlowsCondition.UNSET,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.Flow]:
    """Reads hunt flows matching given conditins."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = (
        "SELECT {columns} FROM flows "
        "FORCE INDEX(flows_by_hunt) "
        "WHERE parent_hunt_id = %s AND parent_flow_id IS NULL "
        "{filter_condition} "
        "ORDER BY last_update ASC "
        "LIMIT %s OFFSET %s"
    )

    filter_query, extra_args = self._HuntFlowCondition(filter_condition)
    query = query.format(
        columns=self.FLOW_DB_FIELDS, filter_condition=filter_query
    )
    args = [hunt_id_int] + extra_args + [count, offset]

    cursor.execute(query, args)
    # _FlowObjectFromRow is defined in mysql_flows.py.
    flows = [self._FlowObjectFromRow(row) for row in cursor.fetchall()]  # pytype: disable=attribute-error
    return flows

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntFlows(
      self,
      hunt_id: str,
      filter_condition: Optional[
          db.HuntFlowsCondition
      ] = db.HuntFlowsCondition.UNSET,
      cursor: Optional[cursors.Cursor] = None,
  ) -> int:
    """Counts hunt flows matching given conditions."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = (
        "SELECT COUNT(*) FROM flows "
        "FORCE INDEX(flows_by_hunt) "
        "WHERE parent_hunt_id = %s AND parent_flow_id IS NULL "
        "{filter_condition}"
    )

    filter_query, extra_args = self._HuntFlowCondition(filter_condition)
    args = [hunt_id_int] + extra_args
    query = query.format(filter_condition=filter_query)
    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntsCounters(
      self,
      hunt_ids: Collection[str],
      cursor: Optional[cursors.Cursor] = None,
  ) -> Mapping[str, db.HuntCounters]:
    """Reads hunt counters for several hunt ids."""
    assert cursor is not None
    if not hunt_ids:
      return {}

    hunt_ids_ints = [db_utils.HuntIDToInt(hunt_id) for hunt_id in hunt_ids]

    query = """
      SELECT parent_hunt_id, flow_state, COUNT(*)
          FROM flows
          FORCE INDEX(flows_by_hunt)
          WHERE parent_hunt_id IN %(hunt_ids)s
            AND parent_flow_id IS NULL
          GROUP BY parent_hunt_id, flow_state
    """
    cursor.execute(query, {"hunt_ids": tuple(hunt_ids_ints)})

    counts_by_state_per_hunt = dict.fromkeys(hunt_ids_ints, {})
    for hunt_id, state, count in cursor.fetchall():
      counts_by_state_per_hunt[hunt_id][state] = count

    hunt_counters = dict.fromkeys(
        hunt_ids,
        db.HuntCounters(
            num_clients=0,
            num_successful_clients=0,
            num_failed_clients=0,
            num_clients_with_results=0,
            num_crashed_clients=0,
            num_running_clients=0,
            num_results=0,
            total_cpu_seconds=0,
            total_network_bytes_sent=0,
        ),
    )

    query = """
        SELECT
          parent_hunt_id,
          SUM(user_cpu_time_used_micros + system_cpu_time_used_micros),
          SUM(network_bytes_sent),
          SUM(num_replies_sent),
          COUNT(IF(num_replies_sent > 0, client_id, NULL))
        FROM flows
        FORCE INDEX(flows_by_hunt)
        WHERE parent_hunt_id IN %(hunt_ids)s
          AND parent_flow_id IS NULL
        GROUP BY parent_hunt_id
    """
    cursor.execute(query, {"hunt_ids": tuple(hunt_ids_ints)})

    for (
        hunt_id,
        total_cpu_seconds,
        total_network_bytes_sent,
        num_results,
        num_clients_with_results,
    ) in cursor.fetchall():
      counts_by_state = counts_by_state_per_hunt[hunt_id]
      num_successful_clients = counts_by_state.get(
          int(flows_pb2.Flow.FlowState.FINISHED), 0
      )
      num_failed_clients = counts_by_state.get(
          int(flows_pb2.Flow.FlowState.ERROR), 0
      )
      num_crashed_clients = counts_by_state.get(
          int(flows_pb2.Flow.FlowState.CRASHED), 0
      )
      num_running_clients = counts_by_state.get(
          int(flows_pb2.Flow.FlowState.RUNNING), 0
      )
      num_clients = sum(counts_by_state_per_hunt[hunt_id].values())

      hunt_counters[db_utils.IntToHuntID(hunt_id)] = db.HuntCounters(
          num_clients=num_clients,
          num_successful_clients=num_successful_clients,
          num_failed_clients=num_failed_clients,
          num_clients_with_results=num_clients_with_results,
          num_crashed_clients=num_crashed_clients,
          num_running_clients=num_running_clients,
          num_results=int(num_results or 0),
          total_cpu_seconds=db_utils.MicrosToSeconds(
              int(total_cpu_seconds or 0)
          ),
          total_network_bytes_sent=int(total_network_bytes_sent or 0),
      )
    return hunt_counters

  def _BinsToQuery(self, bins: list[int], column_name: str) -> str:
    """Builds an SQL query part to fetch counts corresponding to given bins."""
    result = []
    # With the current StatsHistogram implementation the last bin simply
    # takes all the values that are greater than range_max_value of
    # the one-before-the-last bin. range_max_value of the last bin
    # is thus effectively ignored.
    for prev_b, next_b in zip([0] + bins[:-1], bins[:-1] + [None]):
      query = "COUNT(CASE WHEN %s >= %f" % (column_name, prev_b)
      if next_b is not None:
        query += " AND %s < %f" % (column_name, next_b)

      query += " THEN 1 END)"

      result.append(query)

    return ", ".join(result)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntClientResourcesStats(
      self, hunt_id: str, cursor: Optional[cursors.Cursor] = None
  ) -> jobs_pb2.ClientResourcesStats:
    """Read/calculate hunt client resources stats."""
    assert cursor is not None
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = """
      SELECT
        COUNT(*),
        SUM(user_cpu_time_used_micros),
        STDDEV_POP(user_cpu_time_used_micros),
        SUM(system_cpu_time_used_micros),
        STDDEV_POP(system_cpu_time_used_micros),
        SUM(network_bytes_sent),
        STDDEV_POP(network_bytes_sent),
    """

    scaled_bins = [int(1000000 * b) for b in models_hunts.CPU_STATS_BINS]

    query += ", ".join([
        self._BinsToQuery(scaled_bins, "(user_cpu_time_used_micros)"),
        self._BinsToQuery(scaled_bins, "(system_cpu_time_used_micros)"),
        self._BinsToQuery(
            models_hunts.NETWORK_STATS_BINS,
            "network_bytes_sent",
        ),
    ])

    query += " FROM flows "
    query += "FORCE INDEX(flows_by_hunt) "
    query += "WHERE parent_hunt_id = %s "
    query += "AND parent_flow_id IS NULL "
    query += "AND flow_id = %s"

    cursor.execute(query, [hunt_id_int, hunt_id_int])

    response = cursor.fetchone()
    (
        count,
        user_sum,
        user_stddev,
        system_sum,
        system_stddev,
        network_sum,
        network_stddev,
    ) = response[:7]

    stats = jobs_pb2.ClientResourcesStats(
        user_cpu_stats=jobs_pb2.RunningStats(
            num=count,
            sum=db_utils.MicrosToSeconds(int(user_sum or 0)),
            stddev=int(user_stddev or 0) / 1e6,
        ),
        system_cpu_stats=jobs_pb2.RunningStats(
            num=count,
            sum=db_utils.MicrosToSeconds(int(system_sum or 0)),
            stddev=int(system_stddev or 0) / 1e6,
        ),
        network_bytes_sent_stats=jobs_pb2.RunningStats(
            num=count,
            sum=float(network_sum or 0),
            stddev=float(network_stddev or 0),
        ),
    )

    offset = 7
    user_cpu_histogram = jobs_pb2.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], models_hunts.CPU_STATS_BINS
    ):
      user_cpu_histogram.bins.append(
          jobs_pb2.StatsHistogramBin(range_max_value=b_max_value, num=b_num)
      )
    stats.user_cpu_stats.histogram.CopyFrom(user_cpu_histogram)

    offset += len(models_hunts.CPU_STATS_BINS)
    system_cpu_histogram = jobs_pb2.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], models_hunts.CPU_STATS_BINS
    ):
      system_cpu_histogram.bins.append(
          jobs_pb2.StatsHistogramBin(range_max_value=b_max_value, num=b_num)
      )
    stats.system_cpu_stats.histogram.CopyFrom(system_cpu_histogram)

    offset += len(models_hunts.CPU_STATS_BINS)
    network_bytes_histogram = jobs_pb2.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], models_hunts.NETWORK_STATS_BINS
    ):
      network_bytes_histogram.bins.append(
          jobs_pb2.StatsHistogramBin(range_max_value=b_max_value, num=b_num)
      )
    stats.network_bytes_sent_stats.histogram.CopyFrom(network_bytes_histogram)

    query = """
      SELECT
        client_id, flow_id, user_cpu_time_used_micros,
        system_cpu_time_used_micros, network_bytes_sent
      FROM flows
      FORCE INDEX(flows_by_hunt)
      WHERE parent_hunt_id = %s AND parent_flow_id IS NULL AND flow_id = %s AND
            (user_cpu_time_used_micros > 0 OR
             system_cpu_time_used_micros > 0 OR
             network_bytes_sent > 0)
      ORDER BY (user_cpu_time_used_micros + system_cpu_time_used_micros) DESC
      LIMIT 10
    """

    cursor.execute(query, [hunt_id_int, hunt_id_int])

    for cid, fid, ucpu, scpu, nbs in cursor.fetchall():
      client_id = db_utils.IntToClientID(cid)
      flow_id = db_utils.IntToFlowID(fid)
      stats.worst_performers.append(
          jobs_pb2.ClientResources(
              client_id=str(rdf_client.ClientURN.FromHumanReadable(client_id)),
              session_id=str(rdfvalue.RDFURN(client_id).Add(flow_id)),
              cpu_usage=jobs_pb2.CpuSeconds(
                  user_cpu_time=db_utils.MicrosToSeconds(ucpu),
                  system_cpu_time=db_utils.MicrosToSeconds(scpu),
              ),
              network_bytes_sent=nbs,
          )
      )

    return stats

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntFlowsStatesAndTimestamps(
      self,
      hunt_id: str,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[db.FlowStateAndTimestamps]:
    """Reads hunt flows states and timestamps."""
    assert cursor is not None

    query = """
      SELECT
        flow_state, UNIX_TIMESTAMP(timestamp), UNIX_TIMESTAMP(last_update)
      FROM flows
      FORCE INDEX(flows_by_hunt)
      WHERE parent_hunt_id = %s AND parent_flow_id IS NULL
    """

    cursor.execute(query, [db_utils.HuntIDToInt(hunt_id)])

    result = []
    for fs, ct, lup in cursor.fetchall():
      result.append(
          db.FlowStateAndTimestamps(
              flow_state=fs,
              create_time=mysql_utils.TimestampToRDFDatetime(ct),
              last_update_time=mysql_utils.TimestampToRDFDatetime(lup),
          )
      )

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads hunt output plugin log entries."""
    assert cursor is not None
    query = (
        "SELECT client_id, flow_id, log_entry_type, message, "
        "UNIX_TIMESTAMP(timestamp) "
        "FROM flow_output_plugin_log_entries "
        "FORCE INDEX (flow_output_plugin_log_entries_by_hunt) "
        "WHERE hunt_id = %s AND output_plugin_id = %s "
    )
    args = [
        db_utils.HuntIDToInt(hunt_id),
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
    for (
        client_id_int,
        flow_id_int,
        log_entry_type,
        message,
        timestamp,
    ) in cursor.fetchall():
      ret.append(
          flows_pb2.FlowOutputPluginLogEntry(
              hunt_id=hunt_id,
              client_id=db_utils.IntToClientID(client_id_int),
              flow_id=db_utils.IntToFlowID(flow_id_int),
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
  def CountHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
      cursor: Optional[cursors.Cursor] = None,
  ):
    """Counts hunt output plugin log entries."""
    assert cursor is not None
    query = (
        "SELECT COUNT(*) "
        "FROM flow_output_plugin_log_entries "
        "FORCE INDEX (flow_output_plugin_log_entries_by_hunt) "
        "WHERE hunt_id = %s AND output_plugin_id = %s "
    )
    args = [
        db_utils.HuntIDToInt(hunt_id),
        db_utils.OutputPluginIDToInt(output_plugin_id),
    ]

    if with_type is not None:
      query += "AND log_entry_type = %s"
      args.append(int(with_type))

    cursor.execute(query, args)
    return cursor.fetchone()[0]
