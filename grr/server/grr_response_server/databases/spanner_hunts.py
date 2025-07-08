#!/usr/bin/env python
"""A module with hunt methods of the Spanner database implementation."""
import base64

from typing import AbstractSet, Callable, Collection, Iterable, List, Mapping, Optional, Sequence, Set

from google.api_core.exceptions import AlreadyExists, NotFound

from google.cloud import spanner as spanner_lib
from google.cloud.spanner_v1 import param_types

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_flows
from grr_response_server.databases import spanner_utils
from grr_response_server.models import hunts as models_hunts

def _HuntOutputPluginStateFromRow(
    plugin_name: str,
    plugin_args: Optional[bytes],
    plugin_state: bytes,
) -> output_plugin_pb2.OutputPluginState:
  """Creates OutputPluginState from the corresponding table's row data."""
  plugin_args_any = None
  if plugin_args is not None:
    plugin_args_any = any_pb2.Any()
    plugin_args_any.ParseFromString(plugin_args)

  plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
      plugin_name=plugin_name, args=plugin_args_any
  )

  plugin_state_any = any_pb2.Any()
  plugin_state_any.ParseFromString(plugin_state)
  # currently AttributedDict is used to store output
  # plugins' states. This is suboptimal and unsafe and should be refactored
  # towards using per-plugin protos.
  attributed_dict = jobs_pb2.AttributedDict()
  plugin_state_any.Unpack(attributed_dict)

  return output_plugin_pb2.OutputPluginState(
      plugin_descriptor=plugin_descriptor, plugin_state=attributed_dict
  )


def _BinsToQuery(bins: list[int], column_name: str) -> str:
  """Builds an SQL query part to fetch counts corresponding to given bins."""
  result = []
  # With the current StatsHistogram implementation the last bin simply
  # takes all the values that are greater than range_max_value of
  # the one-before-the-last bin. range_max_value of the last bin
  # is thus effectively ignored.
  for prev_b, next_b in zip([0] + bins[:-1], bins[:-1] + [None]):
    query = f"COUNT(CASE WHEN {column_name} >= {prev_b}"
    if next_b is not None:
      query += f" AND {column_name} < {next_b}"

    query += " THEN 1 END)"

    result.append(query)

  return ", ".join(result)


_HUNT_FLOW_CONDITION_TO_FLOW_STATE_MAPPING = {
    abstract_db.HuntFlowsCondition.FAILED_FLOWS_ONLY: (
        flows_pb2.Flow.FlowState.ERROR,
    ),
    abstract_db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY: (
        flows_pb2.Flow.FlowState.FINISHED,
    ),
    abstract_db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY: (
        flows_pb2.Flow.FlowState.ERROR,
        flows_pb2.Flow.FlowState.FINISHED,
    ),
    abstract_db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY: (
        flows_pb2.Flow.FlowState.RUNNING,
    ),
    abstract_db.HuntFlowsCondition.CRASHED_FLOWS_ONLY: (
        flows_pb2.Flow.FlowState.CRASHED,
    ),
}

class HuntsMixin:
  """A Spanner database mixin with implementation of flow methods."""

  db: spanner_utils.Database
  _write_rows_batch_size: int

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteHuntObject(self, hunt_obj: hunts_pb2.Hunt):
    """Writes a hunt object to the database."""
    row = {
        "HuntId": hunt_obj.hunt_id,
        "CreationTime": spanner_lib.COMMIT_TIMESTAMP,
        "LastUpdateTime": spanner_lib.COMMIT_TIMESTAMP,
        "Creator": hunt_obj.creator,
        "DurationMicros": hunt_obj.duration * 10**6,
        "Description": hunt_obj.description,
        "ClientRate": float(hunt_obj.client_rate),
        "ClientLimit": hunt_obj.client_limit,
        "State": int(hunt_obj.hunt_state),
        "StateReason": int(hunt_obj.hunt_state_reason),
        "StateComment": hunt_obj.hunt_state_comment,
        "InitStartTime": None,
        "LastStartTime": None,
        "ClientCountAtStartTime": hunt_obj.num_clients_at_start_time,
        "Hunt": hunt_obj,
    }

    try:
      self.db.Insert(table="Hunts", row=row, txn_tag="WriteHuntObject")
    except AlreadyExists as error:
      raise abstract_db.DuplicatedHuntError(
          hunt_id=hunt_obj.hunt_id, cause=error
      )


  def _UpdateHuntObject(
      self,
      txn,
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
  ):
    """Updates the hunt object within a given transaction."""
    params = {
        "hunt_id": hunt_id,
    }
    params_types = {
        "hunt_id": param_types.STRING
    }
    assignments = ["h.LastUpdateTime = PENDING_COMMIT_TIMESTAMP()"]

    if duration is not None:
      assignments.append("h.DurationMicros = @duration_micros")
      params["duration_micros"] = int(duration.microseconds)
      params_types["duration_micros"] = param_types.INT64

    if client_rate is not None:
      assignments.append("h.ClientRate = @client_rate")
      params["client_rate"] = float(client_rate)
      params_types["client_rate"] = param_types.FLOAT64

    if client_limit is not None:
      assignments.append("h.ClientLimit = @client_limit")
      params["client_limit"] = int(client_limit)
      params_types["client_limit"] = param_types.INT64

    if hunt_state is not None:
      assignments.append("h.State = @hunt_state")
      params["hunt_state"] = int(hunt_state)
      params_types["hunt_state"] = param_types.INT64

    if hunt_state_reason is not None:
      assignments.append("h.StateReason = @hunt_state_reason")
      params["hunt_state_reason"] = int(hunt_state_reason)
      params_types["hunt_state_reason"] = param_types.INT64

    if hunt_state_comment is not None:
      assignments.append("h.StateComment = @hunt_state_comment")
      params["hunt_state_comment"] = hunt_state_comment
      params_types["hunt_state_comment"] = param_types.STRING

    if start_time is not None:
      assignments.append(
          "h.InitStartTime = IFNULL(h.InitStartTime, @start_time)"
      )
      assignments.append("h.LastStartTime = @start_time")
      params["start_time"] = start_time.AsDatetime()
      params_types["start_time"] = param_types.TIMESTAMP

    if num_clients_at_start_time is not None:
      assignments.append(
          "h.ClientCountAtStartTime = @client_count_at_start_time"
      )
      params["client_count_at_start_time"] = int(
          num_clients_at_start_time
      )
      params_types["client_count_at_start_time"] = param_types.INT64

    query = f"""
    UPDATE Hunts AS h
    SET {", ".join(assignments)}
    WHERE h.HuntId = @hunt_id
    """

    txn.execute_update(query, params=params, param_types=params_types,
                       request_options={"request_tag": "_UpdateHuntObject:Hunts:execute_update"})

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateHuntObject(
      self,
      hunt_id: str,
      duration: Optional[rdfvalue.Duration] = None,
      client_rate: Optional[int] = None,
      client_limit: Optional[int] = None,
      hunt_state: Optional[hunts_pb2.Hunt.HuntState.ValueType] = None,
      hunt_state_reason: Optional[
          hunts_pb2.Hunt.HuntStateReason.ValueType
      ] = None,
      hunt_state_comment: Optional[str] = None,
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      num_clients_at_start_time: Optional[int] = None,
  ):
    """Updates the hunt object."""

    def Txn(txn) -> None:
      # Make sure the hunt is there.
      try:
        keyset = spanner_lib.KeySet(keys=[[hunt_id]])
        txn.read(table="Hunts", keyset=keyset, columns=["HuntId",]).one()
      except NotFound as e:
        raise abstract_db.UnknownHuntError(hunt_id) from e

      # Then update the hunt.
      self._UpdateHuntObject(
          txn,
          hunt_id,
          duration=duration,
          client_rate=client_rate,
          client_limit=client_limit,
          hunt_state=hunt_state,
          hunt_state_reason=hunt_state_reason,
          hunt_state_comment=hunt_state_comment,
          start_time=start_time,
          num_clients_at_start_time=num_clients_at_start_time,
      )

    self.db.Transact(Txn, txn_tag="UpdateHuntObject")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteHuntObject(self, hunt_id: str) -> None:
    """Deletes a hunt object with a given id."""
    self.db.Delete(
        table="Hunts", key=[hunt_id], txn_tag="DeleteHuntObject"
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntObject(self, hunt_id: str) -> hunts_pb2.Hunt:
    """Reads a hunt object from the database."""

    cols = [
        "Hunt",
        "CreationTime",
        "LastUpdateTime",
        "DurationMicros",
        "Description",
        "Creator",
        "ClientRate",
        "ClientLimit",
        "State",
        "StateReason",
        "StateComment",
        "InitStartTime",
        "LastStartTime",
        "ClientCountAtStartTime",
    ]

    try:
      row = self.db.Read(table="Hunts",
                         key=[hunt_id],
                         cols=cols,
                         txn_tag="ReadHuntObject")
    except NotFound as e:
      raise abstract_db.UnknownHuntError(hunt_id) from e

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.ParseFromString(row[0])
    hunt_obj.create_time = int(
        rdfvalue.RDFDatetime.FromDatetime(row[1])
    )
    hunt_obj.last_update_time = int(
        rdfvalue.RDFDatetime.FromDatetime(row[2])
    )
    hunt_obj.duration = rdfvalue.DurationSeconds.From(
        row[3], rdfvalue.MICROSECONDS
    ).ToInt(rdfvalue.SECONDS)
    hunt_obj.description = row[4]
    hunt_obj.creator = row[5]
    hunt_obj.client_rate = row[6]
    hunt_obj.client_limit = row[7]
    hunt_obj.hunt_state = row[8]
    hunt_obj.hunt_state_reason = row[9]
    hunt_obj.hunt_state_comment = row[10]
    if row[11] is not None:
      hunt_obj.init_start_time = int(
          rdfvalue.RDFDatetime.FromDatetime(row[11])
      )
    if row[12] is not None:
      hunt_obj.last_start_time = int(
          rdfvalue.RDFDatetime.FromDatetime(row[12])
      )
    hunt_obj.num_clients_at_start_time = row[13]

    return hunt_obj

  @db_utils.CallLogged
  @db_utils.CallAccounted
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
          Iterable[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None
  ) -> list[hunts_pb2.Hunt]:
    """Reads hunt objects from the database."""

    conditions = []
    params = {
        "limit": count,
        "offset": offset,
    }
    param_type = {}

    if with_creator is not None:
      conditions.append("h.Creator = {creator}")
      params["creator"] = with_creator

    if created_by is not None:
      conditions.append("h.Creator IN UNNEST({created_by})")
      params["created_by"] = list(created_by)
      param_type["created_by"] = param_types.Array(param_types.STRING)

    if not_created_by is not None:
      conditions.append("h.Creator NOT IN UNNEST({not_created_by})")
      params["not_created_by"] = list(not_created_by)
      param_type["not_created_by"] = param_types.Array(param_types.STRING)

    if created_after is not None:
      conditions.append("h.CreationTime > {creation_time}")
      params["creation_time"] = created_after.AsDatetime()

    if with_description_match is not None:
      conditions.append("h.Description LIKE {description}")
      params["description"] = f"%{with_description_match}%"

    if with_states is not None:
      if not with_states:
        return []
      ors = []
      for i, state in enumerate(with_states):
        ors.append(f"h.State = {{state_{i}}}")
        params[f"state_{i}"] = int(state)
      conditions.append("(" + " OR ".join(ors) + ")")

    query = """
    SELECT
      h.HuntId,
      h.CreationTime,
      h.LastUpdateTime,
      h.Creator,
      h.DurationMicros,
      h.Description,
      h.ClientRate,
      h.ClientLimit,
      h.State,
      h.StateReason,
      h.StateComment,
      h.InitStartTime,
      h.LastStartTime,
      h.ClientCountAtStartTime,
      h.Hunt
    FROM Hunts AS h
    """

    if conditions:
      query += " WHERE " + " AND ".join(conditions)

    query += """
    ORDER BY h.CreationTime DESC
    LIMIT {limit} OFFSET {offset}
    """

    result = []
    for row in self.db.ParamQuery(query, params, param_type=param_type, txn_tag="ReadHuntObjects"):
      hunt_obj = hunts_pb2.Hunt()
      hunt_obj.ParseFromString(row[14])

      hunt_obj.create_time = int(rdfvalue.RDFDatetime.FromDatetime(row[1]))
      hunt_obj.last_update_time = int(rdfvalue.RDFDatetime.FromDatetime(row[2]))
      hunt_obj.creator = row[3]
      hunt_obj.duration = rdfvalue.DurationSeconds.From(
          row[4], rdfvalue.MICROSECONDS
      ).ToInt(rdfvalue.SECONDS)

      hunt_obj.description = row[5]
      hunt_obj.client_rate = row[6]
      hunt_obj.client_limit = row[7]
      hunt_obj.hunt_state = row[8]
      hunt_obj.hunt_state_reason = row[9]
      hunt_obj.hunt_state_comment = row[10]

      if row[11] is not None:
        hunt_obj.init_start_time = int(
            rdfvalue.RDFDatetime.FromDatetime(row[11])
        )

      if row[12] is not None:
        hunt_obj.last_start_time = int(
            rdfvalue.RDFDatetime.FromDatetime(row[12])
        )

      hunt_obj.num_clients_at_start_time = row[13]

      result.append(hunt_obj)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Iterable[str]] = None,
      not_created_by: Optional[Iterable[str]] = None,
      with_states: Optional[
          Iterable[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
  ) -> Iterable[hunts_pb2.HuntMetadata]:
    """Reads metadata for hunt objects from the database."""

    conditions = []
    params = {
        "limit": count,
        "offset": offset,
    }
    param_type = {}

    if with_creator is not None:
      conditions.append("h.Creator = {creator}")
      params["creator"] = with_creator

    if created_by is not None:
      conditions.append("h.Creator IN UNNEST({created_by})")
      params["created_by"] = list(created_by)
      param_type["created_by"] = param_types.Array(param_types.STRING)

    if not_created_by is not None:
      conditions.append("h.Creator NOT IN UNNEST({not_created_by})")
      params["not_created_by"] = list(not_created_by)
      param_type["not_created_by"] = param_types.Array(param_types.STRING)

    if created_after is not None:
      conditions.append("h.CreationTime > {creation_time}")
      params["creation_time"] = created_after.AsDatetime()

    if with_description_match is not None:
      conditions.append("h.Description LIKE {description}")
      params["description"] = f"%{with_description_match}%"

    if with_states is not None:
      if not with_states:
        return []
      ors = []
      for i, state in enumerate(with_states):
        ors.append(f"h.State = {{state_{i}}}")
        params[f"state_{i}"] = int(state)
      conditions.append("(" + " OR ".join(ors) + ")")

    query = """
    SELECT
      h.HuntId,
      h.CreationTime,
      h.LastUpdateTime,
      h.Creator,
      h.DurationMicros,
      h.Description,
      h.ClientRate,
      h.ClientLimit,
      h.State,
      h.StateComment,
      h.InitStartTime,
      h.LastStartTime,
    FROM Hunts AS h
    """

    if conditions:
      query += " WHERE " + " AND ".join(conditions)

    query += """
    ORDER BY h.CreationTime DESC
    LIMIT {limit} OFFSET {offset}
    """

    result = []
    for row in self.db.ParamQuery(query, params,
                                  param_type=param_type, txn_tag="ListHuntObjects"):
      hunt_mdata = hunts_pb2.HuntMetadata()
      hunt_mdata.hunt_id = row[0]

      hunt_mdata.create_time = int(rdfvalue.RDFDatetime.FromDatetime(row[1]))
      hunt_mdata.last_update_time = int(
          rdfvalue.RDFDatetime.FromDatetime(row[2])
      )
      hunt_mdata.creator = row[3]
      hunt_mdata.duration = int(
          rdfvalue.Duration.From(row[4], rdfvalue.MICROSECONDS).ToInt(
              rdfvalue.SECONDS
          )
      )
      if row[5]:
        hunt_mdata.description = row[5]
      hunt_mdata.client_rate = row[6]
      hunt_mdata.client_limit = row[7]
      hunt_mdata.hunt_state = row[8]
      if row[9]:
        hunt_mdata.hunt_state_comment = row[9]

      if row[10] is not None:
        hunt_mdata.init_start_time = int(
            rdfvalue.RDFDatetime.FromDatetime(row[10])
        )

      if row[11] is not None:
        hunt_mdata.last_start_time = int(
            rdfvalue.RDFDatetime.FromDatetime(row[11])
        )

      result.append(hunt_mdata)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntResults(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_substring: Optional[str] = None,
      with_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Iterable[flows_pb2.FlowResult]:
    """Reads hunt results of a given hunt using given query options."""
    params = {
        "hunt_id": hunt_id,
        "offset": offset,
        "count": count,
    }
    param_type = {}

    query = """
    SELECT t.Payload, t.CreationTime, t.Tag, t.ClientId, t.FlowId
    FROM FlowResults AS t
    WHERE t.HuntId = {hunt_id}
      AND t.FlowId = {hunt_id}
    """

    if with_tag is not None:
      query += " AND t.Tag = {tag} "
      params["tag"] = with_tag
      param_type["tag"] = param_types.STRING

    if with_type is not None:
      query += " AND t.RdfType = {type}"
      params["type"] = with_type
      param_type["type"] = param_types.STRING

    if with_substring is not None:
      query += (
          " AND STRPOS(SAFE_CONVERT_BYTES_TO_STRING(t.Payload.value), "
          "{substring}) != 0"
      )
      params["substring"] = with_substring
      param_type["substring"] = param_types.STRING

    if with_timestamp is not None:
      query += " AND t.CreationTime = {creation_time}"
      params["creation_time"] = with_timestamp.AsDatetime()
      param_type["creation_time"] = param_types.TIMESTAMP

    query += """
    ORDER BY t.CreationTime ASC LIMIT {count} OFFSET {offset}
    """

    results = []
    for (
        payload_bytes,
        creation_time,
        tag,
        client_id,
        flow_id,
    ) in self.db.ParamQuery(query, params, param_type=param_type,
                            txn_tag="ReadHuntResults"):
      result = flows_pb2.FlowResult()
      result.hunt_id = hunt_id
      result.client_id = client_id
      result.flow_id = flow_id
      result.timestamp = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))
      result.payload.ParseFromString(payload_bytes)

      if tag is not None:
        result.tag = tag

      results.append(result)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntResults(
      self,
      hunt_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts hunt results of a given hunt using given query options."""
    params = {
        "hunt_id": hunt_id,
    }
    param_type = {}

    query = """
    SELECT COUNT(*)
    FROM FlowResults AS t
    WHERE t.HuntId = {hunt_id}
    """

    if with_tag is not None:
      query += " AND t.Tag = {tag} "
      params["tag"] = with_tag
      param_type["tag"] = param_types.STRING

    if with_type is not None:
      query += " AND t.RdfType = {type}"
      params["type"] = with_type
      param_type["type"] = param_types.STRING

    (count,) = self.db.ParamQuerySingle(
        query, params,
        param_type=param_type,
        txn_tag="CountHuntResults"
    )
    return count

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntResultsByType(self, hunt_id: str) -> Mapping[str, int]:
    """Returns counts of items in hunt results grouped by type."""
    params = {
        "hunt_id": hunt_id,
    }

    query = """
    SELECT t.RdfType, COUNT(*)
    FROM FlowResults AS t
    WHERE t.HuntId = {hunt_id}
    GROUP BY t.RdfType
    """

    result = {}
    for type_name, count in self.db.ParamQuery(
        query, params, txn_tag="CountHuntResultsByType"
    ):
      result[type_name] = count

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntLogEntries(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads hunt log entries of a given hunt using given query options."""
    params = {
        "hunt_id": hunt_id,
        "offset": offset,
        "count": count,
    }

    query = """
    SELECT l.ClientId,
           l.FlowId,
           l.CreationTime,
           l.Message
      FROM FlowLogEntries AS l
     WHERE l.HuntId = {hunt_id}
       AND l.FlowId = {hunt_id}
    """

    if with_substring is not None:
      query += " AND STRPOS(l.Message, {substring}) != 0"
      params["substring"] = with_substring

    query += """
     LIMIT {count}
    OFFSET {offset}
    """
    params["offset"] = offset
    params["count"] = count

    results = []
    for row in self.db.ParamQuery(query, params, txn_tag="ReadHuntLogEntries"):
      client_id, flow_id, creation_time, message = row

      result = flows_pb2.FlowLogEntry()
      result.hunt_id = hunt_id
      result.client_id = client_id
      result.flow_id = flow_id
      result.timestamp = rdfvalue.RDFDatetime.FromDatetime(
          creation_time
      ).AsMicrosecondsSinceEpoch()
      result.message = message

      results.append(result)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntLogEntries(self, hunt_id: str) -> int:
    """Returns number of hunt log entries of a given hunt."""
    params = {
        "hunt_id": hunt_id,
    }

    query = """
    SELECT COUNT(*)
      FROM FlowLogEntries AS l
     WHERE l.HuntId = {hunt_id}
       AND l.FlowId = {hunt_id}
    """

    (count,) = self.db.ParamQuerySingle(
        query, params, txn_tag="CountHuntLogEntries"
    )
    return count

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads hunt output plugin log entries."""

    query = """
    SELECT l.ClientId,
           l.FlowId,
           l.CreationTime,
           l.Type,
           l.Message
    FROM FlowOutputPluginLogEntries AS l
    WHERE l.HuntId = {hunt_id}
       AND l.OutputPluginId = {output_plugin_id}
    """
    params = {
        "hunt_id": hunt_id,
        "output_plugin_id": output_plugin_id,
    }
    param_type = {}

    if with_type is not None:
      query += " AND l.Type = {type}"
      params["type"] = int(with_type)
      param_type["type"] = param_types.INT64

    query += """
     LIMIT {count}
    OFFSET {offset}
    """
    params["offset"] = offset
    params["count"] = count

    results = []
    for row in self.db.ParamQuery(
        query, params, param_type=param_type,
        txn_tag="ReadHuntOutputPluginLogEntries"
    ):
      client_id, flow_id, creation_time, int_type, message = row

      result = flows_pb2.FlowOutputPluginLogEntry()
      result.hunt_id = hunt_id
      result.client_id = client_id
      result.flow_id = flow_id
      result.output_plugin_id = output_plugin_id
      result.timestamp = rdfvalue.RDFDatetime.FromDatetime(
          creation_time
      ).AsMicrosecondsSinceEpoch()
      result.log_entry_type = int_type
      result.message = message

      results.append(result)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      with_type: Optional[str] = None,
  ) -> int:
    """Returns number of hunt output plugin log entries of a given hunt."""
    query = """
    SELECT COUNT(*)
      FROM FlowOutputPluginLogEntries AS l
     WHERE l.HuntId = {hunt_id}
       AND l.OutputPluginId = {output_plugin_id}
    """
    params = {
        "hunt_id": hunt_id,
        "output_plugin_id": output_plugin_id,
    }

    if with_type is not None:
      query += " AND l.Type = {type}"
      params["type"] = int(with_type)

    (count,) = self.db.ParamQuerySingle(
        query, params, txn_tag="CountHuntOutputPluginLogEntries"
    )
    return count

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntOutputPluginsStates(
      self, hunt_id: str
  ) -> list[output_plugin_pb2.OutputPluginState]:
    """Reads all hunt output plugins states of a given hunt."""
    # Make sure the hunt is there.
    try:
      self.db.Read(table="Hunts",
                   key=[hunt_id,],
                   cols=("HuntId",),
                   txn_tag="ReadHuntOutputPluginsStates")
    except NotFound as e:
      raise abstract_db.UnknownHuntError(hunt_id) from e

    params = {
        "hunt_id": hunt_id,
    }

    query = """
    SELECT s.Name,
           s.Args,
           s.State
      FROM HuntOutputPlugins AS s
     WHERE s.HuntId = {hunt_id}
    """

    results = []
    for row in self.db.ParamQuery(
        query, params, txn_tag="ReadHuntOutputPluginsStates"
    ):
      name, args, state = row
      results.append(_HuntOutputPluginStateFromRow(name, args, state))

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteHuntOutputPluginsStates(
      self,
      hunt_id: str,
      states: Collection[output_plugin_pb2.OutputPluginState],
  ) -> None:
    """Writes hunt output plugin states for a given hunt."""

    def Mutation(mut) -> None:
      for index, state in enumerate(states):
        state_any = any_pb2.Any()
        state_any.Pack(state.plugin_state)
        columns = ["HuntId", "OutputPluginId",
                   "Name",
                   "State"
                  ]
        row = [hunt_id, index,
               state.plugin_descriptor.plugin_name,
               base64.b64encode(state_any.SerializeToString()),
               ]

        if state.plugin_descriptor.HasField("args"):
          columns.append("Args")
          row.append(base64.b64encode(state.plugin_descriptor.args.SerializeToString()))

        mut.insert_or_update(table="HuntOutputPlugins", columns=columns, values=[row])

    try:
      self.db.Mutate(Mutation, txn_tag="WriteHuntOutputPluginsStates")
    except NotFound as e:
      raise abstract_db.UnknownHuntError(hunt_id) from e

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateHuntOutputPluginState(
      self,
      hunt_id: str,
      state_index: int,
      update_fn: Callable[[jobs_pb2.AttributedDict], jobs_pb2.AttributedDict],
  ) -> None:
    """Updates hunt output plugin state for a given output plugin."""

    def Txn(txn) -> None:
      row = txn.read(
          table="HuntOutputPlugins",
          keyset=spanner_lib.KeySet(keys=[[hunt_id, state_index]]),
          columns=["Name", "Args", "State"],
          request_options={"request_tag": "UpdateHuntOutputPluginState:HuntOutputPlugins:read"}
      ).one()
      state = _HuntOutputPluginStateFromRow(
          row[0], row[1], row[2]
      )

      modified_plugin_state = update_fn(state.plugin_state)
      modified_plugin_state_any = any_pb2.Any()
      modified_plugin_state_any.Pack(modified_plugin_state)
      columns = ["HuntId", "OutputPluginId", "State"]
      row = [hunt_id,state_index,
             base64.b64encode(modified_plugin_state_any.SerializeToString())]
      txn.update("HuntOutputPlugins", columns=columns, values=[row])

    try:
      self.db.Transact(Txn, txn_tag="UpdateHuntOutputPluginState")
    except NotFound as e:
      raise abstract_db.UnknownHuntError(hunt_id) from e

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntFlows(  # pytype: disable=annotation-type-mismatch
      self,
      hunt_id: str,
      offset: int,
      count: int,
      filter_condition: abstract_db.HuntFlowsCondition = abstract_db.HuntFlowsCondition.UNSET,
  ) -> Sequence[flows_pb2.Flow]:
    """Reads hunt flows matching given conditions."""

    params = {
        "hunt_id": hunt_id,
    }

    query = """
    SELECT
      f.ClientId,
      f.Creator,
      f.Name,
      f.State,
      f.CreationTime,
      f.UpdateTime,
      f.Crash,
      f.ProcessingWorker,
      f.ProcessingStartTime,
      f.ProcessingEndTime,
      f.NextRequestToProcess,
      f.Flow
    FROM Flows AS f
    WHERE f.ParentHuntId = {hunt_id}
      AND f.FlowId = {hunt_id}
    """

    if filter_condition != abstract_db.HuntFlowsCondition.UNSET:
      states = _HUNT_FLOW_CONDITION_TO_FLOW_STATE_MAPPING[filter_condition]  # pytype: disable=unsupported-operands
      conditions = (f"f.State = {{state_{i}}}" for i in range(len(states)))
      query += "AND (" + " OR ".join(conditions) + ")"
      for i, state in enumerate(states):
        params[f"state_{i}"] = int(state)

    query += """
    ORDER BY f.UpdateTime ASC LIMIT {count} OFFSET {offset}
    """
    params["offset"] = offset
    params["count"] = count

    results = []
    for row in self.db.ParamQuery(query, params, txn_tag="ReadHuntFlows"):
      (
          client_id,
          creator,
          name,
          state,
          creation_time,
          update_time,
          crash,
          processing_worker,
          processing_start_time,
          processing_end_time,
          next_request_to_process,
          flow_payload_bytes,
      ) = row

      result = flows_pb2.Flow()
      result.ParseFromString(flow_payload_bytes)
      result.client_id = client_id
      result.parent_hunt_id = hunt_id
      result.creator = creator
      result.flow_class_name = name
      result.flow_state = state
      result.next_request_to_process = int(next_request_to_process)
      result.create_time = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))
      result.last_update_time = int(
          rdfvalue.RDFDatetime.FromDatetime(update_time)
      )

      if crash is not None:
        client_crash = jobs_pb2.ClientCrash()
        client_crash.ParseFromString(crash)
        result.client_crash_info.CopyFrom(client_crash)

      if processing_worker:
        result.processing_on = processing_worker

      if processing_start_time is not None:
        result.processing_since = int(
            rdfvalue.RDFDatetime.FromDatetime(processing_start_time)
        )
      if processing_end_time is not None:
        result.processing_deadline = int(
            rdfvalue.RDFDatetime.FromDatetime(processing_end_time)
        )

      results.append(result)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntFlowErrors(
      self,
      hunt_id: str,
      offset: int,
      count: int,
  ) -> Mapping[str, abstract_db.FlowErrorInfo]:
    """Returns errors for flows of the given hunt."""
    results = {}

    query = """
      SELECT f.ClientId,
             f.UpdateTime,
             f.Flow.error_message,
             f.Flow.backtrace,
        FROM Flows@{{FORCE_INDEX=FlowsByParentHuntIdFlowIdState}} AS f
       WHERE f.ParentHuntId = {hunt_id}
         AND f.FlowId = {hunt_id}
         AND f.State = 'ERROR'
    ORDER BY f.UpdateTime ASC LIMIT {count}
      OFFSET {offset}
    """

    params = {
        "hunt_id": hunt_id,
        "offset": offset,
        "count": count,
    }

    for row in self.db.ParamQuery(query, params, txn_tag="ReadHuntFlowErrors"):
      (client_id, time, message, backtrace) = row

      info = abstract_db.FlowErrorInfo(
          message=message,
          time=rdfvalue.RDFDatetime.FromDate(time),
      )
      if backtrace:
        info.backtrace = backtrace

      results[client_id] = info

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntFlows(  # pytype: disable=annotation-type-mismatch
      self,
      hunt_id: str,
      filter_condition: Optional[
          abstract_db.HuntFlowsCondition
      ] = abstract_db.HuntFlowsCondition.UNSET,
  ) -> int:
    """Counts hunt flows matching given conditions."""

    params = {
        "hunt_id": hunt_id,
    }

    query = """
    SELECT COUNT(*)
    FROM Flows@{{FORCE_INDEX=FlowsByParentHuntIdFlowIdState}} AS f
    WHERE f.ParentHuntId = {hunt_id}
      AND f.FlowId = {hunt_id}
    """

    if filter_condition != abstract_db.HuntFlowsCondition.UNSET:
      states = _HUNT_FLOW_CONDITION_TO_FLOW_STATE_MAPPING[filter_condition]  # pytype: disable=unsupported-operands
      query += f""" AND({
        " OR ".join(f"f.State = {{state_{i}}}" for i in range(len(states)))
      })"""
      for i, state in enumerate(states):
        params[f"state_{i}"] = int(state)

    (count,) = self.db.ParamQuerySingle(query, params, txn_tag="CountHuntFlows")
    return count

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntFlowsStatesAndTimestamps(
      self,
      hunt_id: str,
  ) -> Sequence[abstract_db.FlowStateAndTimestamps]:
    """Reads hunt flows states and timestamps."""

    params = {
        "hunt_id": hunt_id,
    }

    query = """
    SELECT f.State, f.CreationTime, f.UpdateTime
    FROM Flows AS f
    WHERE f.ParentHuntId = {hunt_id}
      AND f.FlowId = {hunt_id}
    """

    results = []
    for row in self.db.ParamQuery(
        query, params, txn_tag="ReadHuntFlowsStatesAndTimestamps"
    ):
      int_state, creation_time, update_time = row

      results.append(
          abstract_db.FlowStateAndTimestamps(
              flow_state=int_state,
              create_time=rdfvalue.RDFDatetime.FromDatetime(creation_time),
              last_update_time=rdfvalue.RDFDatetime.FromDatetime(update_time),
          )
      )

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntsCounters(
      self,
      hunt_ids: Collection[str],
  ) -> Mapping[str, abstract_db.HuntCounters]:
    """Reads hunt counters for several of hunt ids."""

    params = {
        "hunt_ids": hunt_ids,
    }
    param_type = {
        "hunt_ids": param_types.Array(param_types.STRING)
    }

    states_query = """
      SELECT f.ParentHuntID, f.State, COUNT(*)
      FROM Flows@{{FORCE_INDEX=FlowsByParentHuntIdFlowIdState}} AS f
      WHERE f.ParentHuntID IN UNNEST({hunt_ids})
        AND f.FlowId IN UNNEST({hunt_ids})
        AND f.FlowId = f.ParentHuntID
      GROUP BY f.ParentHuntID, f.State
    """
    counts_by_state_per_hunt = dict.fromkeys(hunt_ids, {})
    for hunt_id, state, count in self.db.ParamQuery(
        states_query, params, param_type=param_type, txn_tag="ReadHuntCounters_1"
    ):
      counts_by_state_per_hunt[hunt_id][state] = count

    hunt_counters = dict.fromkeys(
        hunt_ids,
        abstract_db.HuntCounters(
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

    resources_results_query = """
      SELECT
        f.ParentHuntID,
        SUM(f.UserCpuTimeUsed + f.SystemCpuTimeUsed),
        SUM(f.NetworkBytesSent),
        SUM(f.ReplyCount),
        COUNT(IF(f.ReplyCount > 0, f.ClientId, NULL))
      FROM Flows@{{FORCE_INDEX=FlowsByParentHuntIdFlowIdState}} AS f
      WHERE f.ParentHuntID IN UNNEST({hunt_ids})
        AND f.FlowId IN UNNEST({hunt_ids})
        AND f.ParentHuntID = f.FlowID
      GROUP BY f.ParentHuntID
    """
    for (
        hunt_id,
        total_cpu_seconds,
        total_network_bytes_sent,
        num_results,
        num_clients_with_results,
    ) in self.db.ParamQuery(
        resources_results_query, params,
        param_type=param_type, txn_tag="ReadHuntCounters_2"
    ):
      counts_by_state = counts_by_state_per_hunt[hunt_id]
      num_successful_clients = counts_by_state.get(
          flows_pb2.Flow.FlowState.FINISHED, 0
      )
      num_failed_clients = counts_by_state.get(
          flows_pb2.Flow.FlowState.ERROR, 0
      )
      num_crashed_clients = counts_by_state.get(
          flows_pb2.Flow.FlowState.CRASHED, 0
      )
      num_running_clients = counts_by_state.get(
          flows_pb2.Flow.FlowState.RUNNING, 0
      )
      num_clients = sum(counts_by_state.values())

      hunt_counters[hunt_id] = abstract_db.HuntCounters(
          num_clients=num_clients,
          num_successful_clients=num_successful_clients,
          num_failed_clients=num_failed_clients,
          num_clients_with_results=num_clients_with_results,
          num_crashed_clients=num_crashed_clients,
          num_running_clients=num_running_clients,
          # Spanner's SUM on no elements returns NULL - accounting for
          # this here.
          num_results=num_results or 0,
          total_cpu_seconds=total_cpu_seconds or 0,
          total_network_bytes_sent=total_network_bytes_sent or 0,
      )
    return hunt_counters

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntClientResourcesStats(
      self,
      hunt_id: str,
  ) -> jobs_pb2.ClientResourcesStats:
    """Read hunt client resources stats."""

    params = {
        "hunt_id": hunt_id,
    }

    # For some reason Spanner SQL doesn't have STDDEV_POP aggregate
    # function. Thus, we have to effectively reimplement it ourselves
    # using other aggregate functions.
    # For the reference, see:
    # http://google3/ops/security/grr/core/grr_response_core/lib/rdfvalues/stats.py;l=121;rcl=379683316
    query = """
    SELECT
      COUNT(*),
      SUM(f.UserCpuTimeUsed),
      SQRT(SUM(POW(f.UserCpuTimeUsed, 2)) / COUNT(*) - POW(AVG(f.UserCpuTimeUsed), 2)),
      SUM(f.SystemCpuTimeUsed),
      SQRT(SUM(POW(f.SystemCpuTimeUsed, 2)) / COUNT(*) - POW(AVG(f.SystemCpuTimeUsed), 2)),
      SUM(f.NetworkBytesSent),
      SQRT(SUM(POW(f.NetworkBytesSent, 2)) / COUNT(*) - POW(AVG(f.NetworkBytesSent), 2)),
    """

    query += ", ".join([
        _BinsToQuery(models_hunts.CPU_STATS_BINS, "f.UserCpuTimeUsed"),
        _BinsToQuery(models_hunts.CPU_STATS_BINS, "f.SystemCpuTimeUsed"),
        _BinsToQuery(models_hunts.NETWORK_STATS_BINS, "f.NetworkBytesSent"),
    ])

    query += """
    FROM Flows@{{FORCE_INDEX=FlowsByParentHuntIdFlowIdState}} AS f
    WHERE f.ParentHuntID = {hunt_id} AND f.FlowId = {hunt_id}
    """

    response = self.db.ParamQuerySingle(
        query, params, txn_tag="ReadHuntClientResourcesStats_1"
    )

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
            sum=user_sum,
            stddev=user_stddev,
        ),
        system_cpu_stats=jobs_pb2.RunningStats(
            num=count,
            sum=system_sum,
            stddev=system_stddev,
        ),
        network_bytes_sent_stats=jobs_pb2.RunningStats(
            num=count,
            sum=network_sum,
            stddev=network_stddev,
        ),
    )

    offset = 7
    user_cpu_stats_histogram = jobs_pb2.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], models_hunts.CPU_STATS_BINS
    ):
      user_cpu_stats_histogram.bins.append(
          jobs_pb2.StatsHistogramBin(range_max_value=b_max_value, num=b_num)
      )
    stats.user_cpu_stats.histogram.CopyFrom(user_cpu_stats_histogram)

    offset += len(models_hunts.CPU_STATS_BINS)
    system_cpu_stats_histogram = jobs_pb2.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], models_hunts.CPU_STATS_BINS
    ):
      system_cpu_stats_histogram.bins.append(
          jobs_pb2.StatsHistogramBin(range_max_value=b_max_value, num=b_num)
      )
    stats.system_cpu_stats.histogram.CopyFrom(system_cpu_stats_histogram)

    offset += len(models_hunts.CPU_STATS_BINS)
    network_bytes_histogram = jobs_pb2.StatsHistogram()
    for b_num, b_max_value in zip(
        response[offset:], models_hunts.NETWORK_STATS_BINS
    ):
      network_bytes_histogram.bins.append(
          jobs_pb2.StatsHistogramBin(range_max_value=b_max_value, num=b_num)
      )
    stats.network_bytes_sent_stats.histogram.CopyFrom(network_bytes_histogram)

    clients_query = """
    SELECT
      f.ClientID,
      f.FlowID,
      f.UserCPUTimeUsed,
      f.SystemCPUTimeUsed,
      f.NetworkBytesSent
    FROM Flows@{{FORCE_INDEX=FlowsByParentHuntIdFlowIdState}} AS f
    WHERE
      f.ParentHuntID = {hunt_id} AND
      f.FlowId = {hunt_id} AND
      (f.UserCpuTimeUsed > 0 OR
        f.SystemCpuTimeUsed > 0 OR
        f.NetworkBytesSent > 0)
    ORDER BY (f.UserCPUTimeUsed + f.SystemCPUTimeUsed) DESC
    LIMIT 10
    """

    responses = self.db.ParamQuery(
        clients_query, params, txn_tag="ReadHuntClientResourcesStats_2"
    )
    for cid, fid, ucpu, scpu, nbs in responses:
      client_id = cid
      flow_id = fid
      stats.worst_performers.append(
          jobs_pb2.ClientResources(
              client_id=str(rdf_client.ClientURN.FromHumanReadable(client_id)),
              session_id=str(rdfvalue.RDFURN(client_id).Add(flow_id)),
              cpu_usage=jobs_pb2.CpuSeconds(
                  user_cpu_time=ucpu,
                  system_cpu_time=scpu,
              ),
              network_bytes_sent=nbs,
          )
      )

    return stats
