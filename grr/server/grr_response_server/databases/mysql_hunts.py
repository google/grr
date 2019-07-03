#!/usr/bin/env python
"""The MySQL database methods for flow handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import MySQLdb

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin

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
    "plugin_state",
)


class MySQLDBHuntMixin(object):
  """MySQLDB mixin for flow handling."""

  @mysql_utils.WithTransaction()
  def WriteHuntObject(self, hunt_obj, cursor=None):
    """Writes a hunt object to the database."""
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
        "duration_micros": hunt_obj.duration.microseconds,
        "hunt_state": int(rdf_hunt_objects.Hunt.HuntState.PAUSED),
        "client_rate": hunt_obj.client_rate,
        "client_limit": hunt_obj.client_limit,
        "hunt": hunt_obj.SerializeToString(),
    }

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError as error:
      raise db.DuplicatedHuntError(hunt_id=hunt_obj.hunt_id, cause=error)

  @mysql_utils.WithTransaction()
  def UpdateHuntObject(self,
                       hunt_id,
                       duration=None,
                       client_rate=None,
                       client_limit=None,
                       hunt_state=None,
                       hunt_state_comment=None,
                       start_time=None,
                       num_clients_at_start_time=None,
                       cursor=None):
    """Updates the hunt object by applying the update function."""
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

  @mysql_utils.WithTransaction()
  def DeleteHuntObject(self, hunt_id, cursor=None):
    """Deletes a given hunt object."""
    query = "DELETE FROM hunts WHERE hunt_id = %s"
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    rows_deleted = cursor.execute(query, [hunt_id_int])
    if rows_deleted == 0:
      raise db.UnknownHuntError(hunt_id)

    query = "DELETE FROM hunt_output_plugins_states WHERE hunt_id = %s"
    cursor.execute(query, [hunt_id_int])

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
    hunt_obj = rdf_hunt_objects.Hunt.FromSerializedString(body)
    hunt_obj.duration = rdfvalue.Duration.FromMicroseconds(duration_micros)
    hunt_obj.create_time = mysql_utils.TimestampToRDFDatetime(create_time)
    hunt_obj.last_update_time = mysql_utils.TimestampToRDFDatetime(
        last_update_time)

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
      hunt_obj.init_start_time = mysql_utils.TimestampToRDFDatetime(
          init_start_time)

    if last_start_time is not None:
      hunt_obj.last_start_time = mysql_utils.TimestampToRDFDatetime(
          last_start_time)

    if num_clients_at_start_time is not None:
      hunt_obj.num_clients_at_start_time = num_clients_at_start_time

    if description is not None:
      hunt_obj.description = description

    return hunt_obj

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntObject(self, hunt_id, cursor=None):
    """Reads a hunt object from the database."""
    query = ("SELECT {columns} "
             "FROM hunts WHERE hunt_id = %s".format(
                 columns=_HUNT_COLUMNS_SELECT))

    nr_results = cursor.execute(query, [db_utils.HuntIDToInt(hunt_id)])
    if nr_results == 0:
      raise db.UnknownHuntError(hunt_id)

    return self._HuntObjectFromRow(cursor.fetchone())

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntObjects(self,
                      offset,
                      count,
                      with_creator=None,
                      created_after=None,
                      with_description_match=None,
                      cursor=None):
    """Reads multiple hunt objects from the database."""
    query = "SELECT {columns} FROM hunts ".format(columns=_HUNT_COLUMNS_SELECT)
    args = []

    components = []
    if with_creator is not None:
      components.append("creator = %s ")
      args.append(with_creator)

    if created_after is not None:
      components.append("create_timestamp > FROM_UNIXTIME(%s) ")
      args.append(mysql_utils.RDFDatetimeToTimestamp(created_after))

    if with_description_match is not None:
      components.append("description LIKE %s")
      args.append("%" + with_description_match + "%")

    if components:
      query += "WHERE " + " AND ".join(components)

    query += " ORDER BY create_timestamp DESC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)
    return [self._HuntObjectFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction(readonly=True)
  def ListHuntObjects(self,
                      offset,
                      count,
                      with_creator=None,
                      created_after=None,
                      with_description_match=None,
                      cursor=None):
    """Reads metadata for hunt objects from the database."""
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

    if created_after is not None:
      components.append("create_timestamp > FROM_UNIXTIME(%s) ")
      args.append(mysql_utils.RDFDatetimeToTimestamp(created_after))

    if with_description_match is not None:
      components.append("description LIKE %s")
      args.append("%" + with_description_match + "%")

    if components:
      query += "WHERE " + " AND ".join(components)

    query += " ORDER BY create_timestamp DESC LIMIT %s OFFSET %s"
    args.append(count)
    args.append(offset)

    cursor.execute(query, args)
    result = []
    for row in cursor.fetchall():
      (hunt_id, create_timestamp, last_update_timestamp, creator,
       duration_micros, client_rate, client_limit, hunt_state,
       hunt_state_comment, init_start_time, last_start_time, description) = row
      result.append(
          rdf_hunt_objects.HuntMetadata(
              hunt_id=db_utils.IntToHuntID(hunt_id),
              description=description or None,
              create_time=mysql_utils.TimestampToRDFDatetime(create_timestamp),
              creator=creator,
              duration=rdfvalue.Duration.FromMicroseconds(duration_micros),
              client_rate=client_rate,
              client_limit=client_limit,
              hunt_state=hunt_state,
              hunt_state_comment=hunt_state_comment or None,
              last_update_time=mysql_utils.TimestampToRDFDatetime(
                  last_update_timestamp),
              init_start_time=mysql_utils.TimestampToRDFDatetime(
                  init_start_time),
              last_start_time=mysql_utils.TimestampToRDFDatetime(
                  last_start_time)))

    return result

  def _HuntOutputPluginStateFromRow(self, row):
    """Builds OutputPluginState object from a DB row."""
    plugin_name, plugin_args_bytes, plugin_state_bytes = row

    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=plugin_name)
    if plugin_args_bytes is not None:
      plugin_args_cls = plugin_descriptor.GetPluginArgsClass()
      # If plugin_args_cls is None, we have no clue what class plugin args
      # should be and therefore no way to deserialize it. This can happen if
      # a plugin got renamed or removed, for example. In this case we
      # still want to get plugin's definition and state back and not fail hard,
      # so that all other plugins can be read.
      if plugin_args_cls is not None:
        plugin_descriptor.plugin_args = plugin_args_cls.FromSerializedString(
            plugin_args_bytes)

    plugin_state = rdf_protodict.AttributedDict.FromSerializedString(
        plugin_state_bytes)
    return rdf_flow_runner.OutputPluginState(
        plugin_descriptor=plugin_descriptor, plugin_state=plugin_state)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntOutputPluginsStates(self, hunt_id, cursor=None):
    """Reads all hunt output plugins states of a given hunt."""

    columns = ", ".join(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS)

    query = ("SELECT {columns} FROM hunt_output_plugins_states "
             "WHERE hunt_id = %s".format(columns=columns))
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

  @mysql_utils.WithTransaction()
  def WriteHuntOutputPluginsStates(self, hunt_id, states, cursor=None):
    """Writes hunt output plugin states for a given hunt."""

    columns = ", ".join(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS)
    placeholders = mysql_utils.Placeholders(
        2 + len(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS))
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    for index, state in enumerate(states):
      query = ("INSERT INTO hunt_output_plugins_states "
               "(hunt_id, plugin_id, {columns}) "
               "VALUES {placeholders}".format(
                   columns=columns, placeholders=placeholders))
      args = [hunt_id_int, index, state.plugin_descriptor.plugin_name]

      if state.plugin_descriptor.plugin_args is None:
        args.append(None)
      else:
        args.append(state.plugin_descriptor.plugin_args.SerializeToString())

      args.append(state.plugin_state.SerializeToString())

      try:
        cursor.execute(query, args)
      except MySQLdb.IntegrityError as e:
        raise db.UnknownHuntError(hunt_id=hunt_id, cause=e)

  @mysql_utils.WithTransaction()
  def UpdateHuntOutputPluginState(self,
                                  hunt_id,
                                  state_index,
                                  update_fn,
                                  cursor=None):
    """Updates hunt output plugin state for a given output plugin."""

    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = "SELECT hunt_id FROM hunts WHERE hunt_id = %s"
    rows_returned = cursor.execute(query, [hunt_id_int])
    if rows_returned == 0:
      raise db.UnknownHuntError(hunt_id)

    columns = ", ".join(_HUNT_OUTPUT_PLUGINS_STATES_COLUMNS)
    query = ("SELECT {columns} FROM hunt_output_plugins_states "
             "WHERE hunt_id = %s AND plugin_id = %s".format(columns=columns))
    rows_returned = cursor.execute(query, [hunt_id_int, state_index])
    if rows_returned == 0:
      raise db.UnknownHuntOutputPluginStateError(hunt_id, state_index)

    state = self._HuntOutputPluginStateFromRow(cursor.fetchone())
    modified_plugin_state = update_fn(state.plugin_state)

    query = ("UPDATE hunt_output_plugins_states "
             "SET plugin_state = %s "
             "WHERE hunt_id = %s AND plugin_id = %s")
    args = [modified_plugin_state.SerializeToString(), hunt_id_int, state_index]
    cursor.execute(query, args)
    return state

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntLogEntries(self,
                         hunt_id,
                         offset,
                         count,
                         with_substring=None,
                         cursor=None):
    """Reads hunt log entries of a given hunt using given query options."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = ("SELECT client_id, flow_id, message, UNIX_TIMESTAMP(timestamp) "
             "FROM flow_log_entries "
             "FORCE INDEX(flow_log_entries_by_hunt) "
             "WHERE hunt_id = %s AND flow_id = hunt_id ")

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
          rdf_flow_objects.FlowLogEntry(
              client_id=db_utils.IntToClientID(client_id_int),
              flow_id=db_utils.IntToFlowID(flow_id_int),
              hunt_id=hunt_id,
              message=message,
              timestamp=mysql_utils.TimestampToRDFDatetime(timestamp)))

    return flow_log_entries

  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntLogEntries(self, hunt_id, cursor=None):
    """Returns number of hunt log entries of a given hunt."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = ("SELECT COUNT(*) FROM flow_log_entries "
             "FORCE INDEX(flow_log_entries_by_hunt) "
             "WHERE hunt_id = %s AND flow_id = hunt_id")
    cursor.execute(query, [hunt_id_int])
    return cursor.fetchone()[0]

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntResults(self,
                      hunt_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None,
                      with_timestamp=None,
                      cursor=None):
    """Reads hunt results of a given hunt using given query options."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = ("SELECT client_id, flow_id, hunt_id, payload, type, "
             "UNIX_TIMESTAMP(timestamp), tag "
             "FROM flow_results "
             "FORCE INDEX(flow_results_hunt_id_flow_id_timestamp) "
             "WHERE hunt_id = %s ")

    args = [hunt_id_int]

    if with_tag:
      query += "AND tag = %s "
      args.append(with_tag)

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
        hunt_id_int,
        serialized_payload,
        payload_type,
        timestamp,
        tag,
    ) in cursor.fetchall():
      if payload_type in rdfvalue.RDFValue.classes:
        payload = rdfvalue.RDFValue.classes[payload_type]()
        payload.ParseFromString(serialized_payload)
      else:
        payload = rdf_objects.SerializedValueOfUnrecognizedType(
            type_name=payload_type, value=serialized_payload)

      result = rdf_flow_objects.FlowResult(
          client_id=db_utils.IntToClientID(client_id_int),
          flow_id=db_utils.IntToFlowID(flow_id_int),
          hunt_id=hunt_id,
          payload=payload,
          timestamp=mysql_utils.TimestampToRDFDatetime(timestamp))
      if tag is not None:
        result.tag = tag

      ret.append(result)

    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntResults(self,
                       hunt_id,
                       with_tag=None,
                       with_type=None,
                       cursor=None):
    """Counts hunt results of a given hunt using given query options."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = "SELECT COUNT(*) FROM flow_results WHERE hunt_id = %s "

    args = [hunt_id_int]

    if with_tag is not None:
      query += "AND tag = %s "
      args.append(with_tag)

    if with_type is not None:
      query += "AND type = %s "
      args.append(with_type)

    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntResultsByType(self, hunt_id, cursor=None):
    """Counts number of hunts results per type."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = ("SELECT type, COUNT(*) FROM flow_results "
             "WHERE hunt_id = %s GROUP BY type")

    cursor.execute(query, [hunt_id_int])
    return dict(cursor.fetchall())

  def _HuntFlowCondition(self, condition):
    """Builds an SQL condition matching db.HuntFlowsCondition."""
    if condition == db.HuntFlowsCondition.UNSET:
      return "", []
    elif condition == db.HuntFlowsCondition.FAILED_FLOWS_ONLY:
      return ("AND flow_state = %s ",
              [int(rdf_flow_objects.Flow.FlowState.ERROR)])
    elif condition == db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY:
      return ("AND flow_state = %s ",
              [int(rdf_flow_objects.Flow.FlowState.FINISHED)])
    elif condition == db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY:
      return ("AND (flow_state = %s OR flow_state = %s) ", [
          int(rdf_flow_objects.Flow.FlowState.FINISHED),
          int(rdf_flow_objects.Flow.FlowState.ERROR)
      ])
    elif condition == db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY:
      return ("AND flow_state = %s ",
              [int(rdf_flow_objects.Flow.FlowState.RUNNING)])
    elif condition == db.HuntFlowsCondition.CRASHED_FLOWS_ONLY:
      return ("AND flow_state = %s ",
              [int(rdf_flow_objects.Flow.FlowState.CRASHED)])
    else:
      raise ValueError("Invalid condition value: %r" % condition)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntFlows(self,
                    hunt_id,
                    offset,
                    count,
                    filter_condition=db.HuntFlowsCondition.UNSET,
                    cursor=None):
    """Reads hunt flows matching given conditins."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = ("SELECT {columns} FROM flows "
             "FORCE INDEX(flows_by_hunt) "
             "WHERE parent_hunt_id = %s AND parent_flow_id IS NULL "
             "{filter_condition} "
             "ORDER BY last_update ASC "
             "LIMIT %s OFFSET %s")

    filter_query, extra_args = self._HuntFlowCondition(filter_condition)
    query = query.format(
        columns=self.FLOW_DB_FIELDS, filter_condition=filter_query)
    args = [hunt_id_int] + extra_args + [count, offset]

    cursor.execute(query, args)
    return [self._FlowObjectFromRow(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntFlows(self,
                     hunt_id,
                     filter_condition=db.HuntFlowsCondition.UNSET,
                     cursor=None):
    """Counts hunt flows matching given conditions."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = ("SELECT COUNT(*) FROM flows "
             "FORCE INDEX(flows_by_hunt) "
             "WHERE parent_hunt_id = %s AND parent_flow_id IS NULL "
             "{filter_condition}")

    filter_query, extra_args = self._HuntFlowCondition(filter_condition)
    args = [hunt_id_int] + extra_args
    query = query.format(filter_condition=filter_query)
    cursor.execute(query, args)
    return cursor.fetchone()[0]

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntCounters(self, hunt_id, cursor=None):
    """Reads hunt counters."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = ("SELECT flow_state, COUNT(*) "
             "FROM flows "
             "FORCE INDEX(flows_by_hunt) "
             "WHERE parent_hunt_id = %s AND parent_flow_id IS NULL "
             "GROUP BY flow_state")

    cursor.execute(query, [hunt_id_int])
    counts_by_state = dict(cursor.fetchall())

    num_successful_clients = counts_by_state.get(
        int(rdf_flow_objects.Flow.FlowState.FINISHED), 0)
    num_failed_clients = counts_by_state.get(
        int(rdf_flow_objects.Flow.FlowState.ERROR), 0)
    num_crashed_clients = counts_by_state.get(
        int(rdf_flow_objects.Flow.FlowState.CRASHED), 0)
    num_clients = sum(counts_by_state.values())

    query = """
    SELECT * FROM

      (
      SELECT COUNT(client_id)
      FROM flows
      FORCE INDEX(flows_by_hunt)
      WHERE parent_hunt_id = %s AND parent_flow_id IS NULL AND
            num_replies_sent > 0) counters,

      (
      SELECT SUM(user_cpu_time_used_micros + system_cpu_time_used_micros),
             SUM(network_bytes_sent),
             SUM(num_replies_sent)
      FROM flows
      FORCE INDEX(flows_by_hunt)
      WHERE parent_hunt_id = %s AND parent_flow_id IS NULL) resources
    """

    cursor.execute(query, [hunt_id_int, hunt_id_int])
    (
        num_clients_with_results,
        total_cpu_seconds,
        total_network_bytes_sent,
        num_results,
    ) = cursor.fetchone()

    return db.HuntCounters(
        num_clients=num_clients,
        num_successful_clients=num_successful_clients,
        num_failed_clients=num_failed_clients,
        num_clients_with_results=num_clients_with_results,
        num_crashed_clients=num_crashed_clients,
        num_results=int(num_results or 0),
        total_cpu_seconds=db_utils.MicrosToSeconds(int(total_cpu_seconds or 0)),
        total_network_bytes_sent=int(total_network_bytes_sent or 0))

  def _BinsToQuery(self, bins, column_name):
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

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntClientResourcesStats(self, hunt_id, cursor=None):
    """Read/calculate hunt client resources stats."""
    hunt_id_int = db_utils.HuntIDToInt(hunt_id)

    query = """
      SELECT
        COUNT(*),
        SUM(user_cpu_time_used_micros),
        SUM((user_cpu_time_used_micros) * (user_cpu_time_used_micros)),
        SUM(system_cpu_time_used_micros),
        SUM((system_cpu_time_used_micros) * (system_cpu_time_used_micros)),
        SUM(network_bytes_sent),
        SUM(network_bytes_sent * network_bytes_sent),
    """

    scaled_bins = [
        int(1000000 * b) for b in rdf_stats.ClientResourcesStats.CPU_STATS_BINS
    ]

    query += self._BinsToQuery(scaled_bins, "(user_cpu_time_used_micros)")
    query += ","
    query += self._BinsToQuery(scaled_bins, "(system_cpu_time_used_micros)")
    query += ","
    query += self._BinsToQuery(
        rdf_stats.ClientResourcesStats.NETWORK_STATS_BINS, "network_bytes_sent")

    query += " FROM flows "
    query += "FORCE INDEX(flows_by_hunt) "
    query += "WHERE parent_hunt_id = %s AND parent_flow_id IS NULL"

    cursor.execute(query, [hunt_id_int])

    response = cursor.fetchone()
    (count, user_sum, user_sq_sum, system_sum, system_sq_sum, network_sum,
     network_sq_sum) = response[:7]

    stats = rdf_stats.ClientResourcesStats(
        user_cpu_stats=rdf_stats.RunningStats(
            num=count,
            sum=db_utils.MicrosToSeconds(int(user_sum or 0)),
            sum_sq=int(user_sq_sum or 0) / 1e12,
        ),
        system_cpu_stats=rdf_stats.RunningStats(
            num=count,
            sum=db_utils.MicrosToSeconds(int(system_sum or 0)),
            sum_sq=int(system_sq_sum or 0) / 1e12,
        ),
        network_bytes_sent_stats=rdf_stats.RunningStats(
            num=count,
            sum=float(network_sum or 0),
            sum_sq=float(network_sq_sum or 0),
        ),
    )

    offset = 7
    stats.user_cpu_stats.histogram = rdf_stats.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], rdf_stats.ClientResourcesStats.CPU_STATS_BINS):
      stats.user_cpu_stats.histogram.bins.append(
          rdf_stats.StatsHistogramBin(range_max_value=b_max_value, num=b_num))

    offset += len(rdf_stats.ClientResourcesStats.CPU_STATS_BINS)
    stats.system_cpu_stats.histogram = rdf_stats.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], rdf_stats.ClientResourcesStats.CPU_STATS_BINS):
      stats.system_cpu_stats.histogram.bins.append(
          rdf_stats.StatsHistogramBin(range_max_value=b_max_value, num=b_num))

    offset += len(rdf_stats.ClientResourcesStats.CPU_STATS_BINS)
    stats.network_bytes_sent_stats.histogram = rdf_stats.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], rdf_stats.ClientResourcesStats.NETWORK_STATS_BINS):
      stats.network_bytes_sent_stats.histogram.bins.append(
          rdf_stats.StatsHistogramBin(range_max_value=b_max_value, num=b_num))

    query = """
      SELECT
        client_id, flow_id, user_cpu_time_used_micros,
        system_cpu_time_used_micros, network_bytes_sent
      FROM flows
      FORCE INDEX(flows_by_hunt)
      WHERE parent_hunt_id = %s AND parent_flow_id IS NULL AND
            (user_cpu_time_used_micros > 0 OR
             system_cpu_time_used_micros > 0 OR
             network_bytes_sent > 0)
      ORDER BY (user_cpu_time_used_micros + system_cpu_time_used_micros) DESC
      LIMIT 10
    """

    cursor.execute(query, [hunt_id_int])

    for cid, fid, ucpu, scpu, nbs in cursor.fetchall():
      client_id = db_utils.IntToClientID(cid)
      flow_id = db_utils.IntToFlowID(fid)
      stats.worst_performers.append(
          rdf_client_stats.ClientResources(
              client_id=client_id,
              session_id=rdfvalue.RDFURN(client_id).Add(flow_id),
              cpu_usage=rdf_client_stats.CpuSeconds(
                  user_cpu_time=db_utils.MicrosToSeconds(ucpu),
                  system_cpu_time=db_utils.MicrosToSeconds(scpu),
              ),
              network_bytes_sent=nbs))

    return stats

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntFlowsStatesAndTimestamps(self, hunt_id, cursor=None):
    """Reads hunt flows states and timestamps."""

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
              flow_state=rdf_flow_objects.Flow.FlowState.FromInt(fs),
              create_time=mysql_utils.TimestampToRDFDatetime(ct),
              last_update_time=mysql_utils.TimestampToRDFDatetime(lup)))

    return result

  @mysql_utils.WithTransaction(readonly=True)
  def ReadHuntOutputPluginLogEntries(self,
                                     hunt_id,
                                     output_plugin_id,
                                     offset,
                                     count,
                                     with_type=None,
                                     cursor=None):
    """Reads hunt output plugin log entries."""
    query = ("SELECT client_id, flow_id, log_entry_type, message, "
             "UNIX_TIMESTAMP(timestamp) "
             "FROM flow_output_plugin_log_entries "
             "FORCE INDEX (flow_output_plugin_log_entries_by_hunt) "
             "WHERE hunt_id = %s AND output_plugin_id = %s ")
    args = [
        db_utils.HuntIDToInt(hunt_id),
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
    for (client_id_int, flow_id_int, log_entry_type, message,
         timestamp) in cursor.fetchall():
      ret.append(
          rdf_flow_objects.FlowOutputPluginLogEntry(
              hunt_id=hunt_id,
              client_id=db_utils.IntToClientID(client_id_int),
              flow_id=db_utils.IntToFlowID(flow_id_int),
              output_plugin_id=output_plugin_id,
              log_entry_type=log_entry_type,
              message=message,
              timestamp=mysql_utils.TimestampToRDFDatetime(timestamp)))

    return ret

  @mysql_utils.WithTransaction(readonly=True)
  def CountHuntOutputPluginLogEntries(self,
                                      hunt_id,
                                      output_plugin_id,
                                      with_type=None,
                                      cursor=None):
    """Counts hunt output plugin log entries."""
    query = ("SELECT COUNT(*) "
             "FROM flow_output_plugin_log_entries "
             "FORCE INDEX (flow_output_plugin_log_entries_by_hunt) "
             "WHERE hunt_id = %s AND output_plugin_id = %s ")
    args = [
        db_utils.HuntIDToInt(hunt_id),
        db_utils.OutputPluginIDToInt(output_plugin_id)
    ]

    if with_type is not None:
      query += "AND log_entry_type = %s"
      args.append(int(with_type))

    cursor.execute(query, args)
    return cursor.fetchone()[0]
