#!/usr/bin/env python
"""The in memory database methods for hunt handling."""

import collections
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence, Set
import math
import sys
from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.models import hunts as models_hunts


def UpdateHistogram(histogram: jobs_pb2.StatsHistogram, value: float):
  """Puts a given value into an appropriate bin."""
  for b in histogram.bins:
    if b.range_max_value > value:
      b.num += 1
      return

  if histogram.bins:
    histogram.bins[-1].num += 1


def UpdateStats(running_stats: jobs_pb2.RunningStats, values: Iterable[float]):
  """Updates running stats with the given values."""
  sum_sq = 0
  for value in values:
    running_stats.num += 1
    running_stats.sum += value
    sum_sq += value**2
    mean = running_stats.sum / running_stats.num if running_stats.num > 0 else 0
    running_stats.stddev = math.sqrt(sum_sq / running_stats.num - mean**2)
    UpdateHistogram(running_stats.histogram, value)


def InitializeClientResourcesStats(
    client_resources: list[jobs_pb2.ClientResources],
) -> jobs_pb2.ClientResourcesStats:
  """Initialized ClientResourcesStats with resources consumed by a single client."""

  stats = jobs_pb2.ClientResourcesStats()
  stats.user_cpu_stats.histogram.bins.extend([
      jobs_pb2.StatsHistogramBin(range_max_value=b)
      for b in models_hunts.CPU_STATS_BINS
  ])
  stats.system_cpu_stats.histogram.bins.extend([
      jobs_pb2.StatsHistogramBin(range_max_value=b)
      for b in models_hunts.CPU_STATS_BINS
  ])
  stats.network_bytes_sent_stats.histogram.bins.extend([
      jobs_pb2.StatsHistogramBin(range_max_value=b)
      for b in models_hunts.NETWORK_STATS_BINS
  ])
  UpdateStats(
      stats.user_cpu_stats,
      [r.cpu_usage.user_cpu_time for r in client_resources],
  )
  UpdateStats(
      stats.system_cpu_stats,
      [r.cpu_usage.system_cpu_time for r in client_resources],
  )
  UpdateStats(
      stats.network_bytes_sent_stats,
      [r.network_bytes_sent for r in client_resources],
  )

  client_resources.sort(
      key=lambda s: s.cpu_usage.user_cpu_time + s.cpu_usage.system_cpu_time,
      reverse=True,
  )
  stats.worst_performers.extend(
      client_resources[: models_hunts.NUM_WORST_PERFORMERS]
  )

  return stats


class InMemoryDBHuntMixin(object):
  """Hunts-related DB methods implementation."""

  hunts: dict[str, hunts_pb2.Hunt]
  flows: dict[str, flows_pb2.Flow]
  hunt_output_plugins_states: dict[str, list[bytes]]
  approvals_by_username: dict[str, dict[str, objects_pb2.ApprovalRequest]]
  flow_results: dict[tuple[str, str], list[flows_pb2.FlowResult]]

  def _GetHuntFlows(self, hunt_id: str) -> list[flows_pb2.Flow]:
    hunt_flows = [
        f
        for f in self.flows.values()
        if f.parent_hunt_id == hunt_id and f.flow_id == hunt_id
    ]
    return sorted(hunt_flows, key=lambda f: f.client_id)

  @utils.Synchronized
  def WriteHuntObject(self, hunt_obj: hunts_pb2.Hunt):
    """Writes a hunt object to the database."""
    if hunt_obj.hunt_id in self.hunts:
      raise db.DuplicatedHuntError(hunt_id=hunt_obj.hunt_id)

    clone = hunts_pb2.Hunt()
    clone.CopyFrom(hunt_obj)
    clone.create_time = int(rdfvalue.RDFDatetime.Now())
    clone.last_update_time = int(rdfvalue.RDFDatetime.Now())
    self.hunts[hunt_obj.hunt_id] = clone

  @utils.Synchronized
  def UpdateHuntObject(
      self,
      hunt_id: str,
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      duration: Optional[rdfvalue.Duration] = None,
      **kwargs,
  ):
    """Updates the hunt object by applying the update function."""
    hunt_obj = self.ReadHuntObject(hunt_id)

    delta_suffix = "_delta"

    for k, v in kwargs.items():
      if v is None:
        continue

      if k.endswith(delta_suffix):
        key = k[: -len(delta_suffix)]
        current_value = getattr(hunt_obj, key)
        setattr(hunt_obj, key, current_value + v)
      else:
        setattr(hunt_obj, k, v)

    if duration is not None:
      hunt_obj.duration = duration.ToInt(rdfvalue.SECONDS)

    if start_time is not None:
      hunt_obj.init_start_time = hunt_obj.init_start_time or int(start_time)
      hunt_obj.last_start_time = int(start_time)

    hunt_obj.last_update_time = int(rdfvalue.RDFDatetime.Now())
    self.hunts[hunt_obj.hunt_id] = hunt_obj

  @utils.Synchronized
  def ReadHuntOutputPluginsStates(
      self,
      hunt_id: str,
  ) -> list[output_plugin_pb2.OutputPluginState]:
    """Reads hunt output plugin states for a given hunt."""
    if hunt_id not in self.hunts:
      raise db.UnknownHuntError(hunt_id)

    serialized_states = self.hunt_output_plugins_states.get(hunt_id, [])
    result = []
    for s in serialized_states:
      output_plugin_state = output_plugin_pb2.OutputPluginState()
      output_plugin_state.ParseFromString(s)
      result.append(output_plugin_state)

    return result

  @utils.Synchronized
  def WriteHuntOutputPluginsStates(
      self,
      hunt_id: str,
      states: Collection[output_plugin_pb2.OutputPluginState],
  ) -> None:

    if hunt_id not in self.hunts:
      raise db.UnknownHuntError(hunt_id)

    self.hunt_output_plugins_states[hunt_id] = [
        s.SerializeToString() for s in states
    ]

  @utils.Synchronized
  def UpdateHuntOutputPluginState(
      self,
      hunt_id: str,
      state_index: int,
      update_fn: Callable[
          [jobs_pb2.AttributedDict],
          jobs_pb2.AttributedDict,
      ],
  ) -> None:
    """Updates hunt output plugin state for a given output plugin."""
    if hunt_id not in self.hunts:
      raise db.UnknownHuntError(hunt_id)

    state = output_plugin_pb2.OutputPluginState()
    try:
      state.ParseFromString(
          self.hunt_output_plugins_states[hunt_id][state_index]
      )
    except KeyError as ex:
      raise db.UnknownHuntOutputPluginStateError(hunt_id, state_index) from ex

    modified_plugin_state = update_fn(state.plugin_state)
    state.plugin_state.CopyFrom(modified_plugin_state)

    self.hunt_output_plugins_states[hunt_id][
        state_index
    ] = state.SerializeToString()

  @utils.Synchronized
  def DeleteHuntObject(self, hunt_id: str) -> None:
    """Deletes a hunt object with a given id."""
    try:
      del self.hunts[hunt_id]
    except KeyError:
      raise db.UnknownHuntError(hunt_id)

    for approvals in self.approvals_by_username.values():
      # We use `list` around dictionary items iterator to avoid errors about
      # dictionary modification during iteration.
      for approval_id, approval in list(approvals.items()):
        if (
            approval.approval_type
            != objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
        ):
          continue
        if approval.subject_id != hunt_id:
          continue
        del approvals[approval_id]

  @utils.Synchronized
  def ReadHuntObject(self, hunt_id: str) -> hunts_pb2.Hunt:
    """Reads a hunt object from the database."""
    hunt = hunts_pb2.Hunt()
    try:
      hunt_instance = self.hunts[hunt_id]
    except KeyError as ex:
      raise db.UnknownHuntError(hunt_id) from ex
    hunt.CopyFrom(hunt_instance)
    return hunt

  @utils.Synchronized
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
  ) -> list[hunts_pb2.Hunt]:
    """Reads metadata for hunt objects from the database."""
    filter_fns = []
    if with_creator is not None:
      filter_fns.append(lambda h: h.creator == with_creator)
    if created_by is not None:
      filter_fns.append(lambda h: h.creator in created_by)
    if not_created_by is not None:
      filter_fns.append(lambda h: h.creator not in not_created_by)
    if created_after is not None:
      filter_fns.append(lambda h: h.create_time > int(created_after))
    if with_description_match is not None:
      filter_fns.append(lambda h: with_description_match in h.description)
    if with_states is not None:
      filter_fns.append(lambda h: h.hunt_state in with_states)
    filter_fn = lambda h: all(f(h) for f in filter_fns)

    result = []
    for h in self.hunts.values():
      if filter_fn(h):
        hunt_obj = hunts_pb2.Hunt()
        hunt_obj.CopyFrom(h)
        result.append(hunt_obj)
    result.sort(key=lambda h: h.create_time, reverse=True)
    return result[offset : offset + (count or db.MAX_COUNT)]

  @utils.Synchronized
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
  ) -> list[hunts_pb2.HuntMetadata]:
    """Reads all hunt objects from the database."""
    filter_fns = []
    if with_creator is not None:
      filter_fns.append(lambda h: h.creator == with_creator)
    if created_by is not None:
      filter_fns.append(lambda h: h.creator in created_by)
    if not_created_by is not None:
      filter_fns.append(lambda h: h.creator not in not_created_by)
    if created_after is not None:
      filter_fns.append(lambda h: h.create_time > int(created_after))
    if with_description_match is not None:
      filter_fns.append(lambda h: with_description_match in h.description)
    if with_states is not None:
      filter_fns.append(lambda h: h.hunt_state in with_states)
    filter_fn = lambda h: all(f(h) for f in filter_fns)

    result = []
    for h in self.hunts.values():
      if not filter_fn(h):
        continue
      hunt_metadata = models_hunts.InitHuntMetadataFromHunt(h)
      result.append(hunt_metadata)

    result.sort(key=lambda h: h.create_time, reverse=True)
    return result[offset : offset + (count or db.MAX_COUNT)]

  @utils.Synchronized
  def ReadHuntLogEntries(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads hunt log entries of a given hunt using given query options."""
    all_entries = []
    for flow_obj in self._GetHuntFlows(hunt_id):
      # ReadFlowLogEntries is implemented in the db.Database class.
      # pytype: disable=attribute-error
      for entry in self.ReadFlowLogEntries(
          flow_obj.client_id,
          flow_obj.flow_id,
          0,
          sys.maxsize,
          with_substring=with_substring,
      ):
        # pytype: enable=attribute-error
        all_entries.append(
            flows_pb2.FlowLogEntry(
                hunt_id=hunt_id,
                client_id=flow_obj.client_id,
                flow_id=flow_obj.flow_id,
                timestamp=entry.timestamp,
                message=entry.message,
            )
        )

    all_entries.sort(key=lambda x: x.timestamp)
    return all_entries[offset : offset + count]

  @utils.Synchronized
  def CountHuntLogEntries(self, hunt_id: str) -> int:
    """Returns number of hunt log entries of a given hunt."""
    return len(self.ReadHuntLogEntries(hunt_id, 0, sys.maxsize))

  @utils.Synchronized
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
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads hunt results of a given hunt using given query options."""
    all_results = []
    for flow_obj in self._GetHuntFlows(hunt_id):
      # ReadFlowResults is implemented in the db.Database class.
      # pytype: disable=attribute-error
      for entry in self.ReadFlowResults(
          flow_obj.client_id,
          flow_obj.flow_id,
          0,
          sys.maxsize,
          with_tag=with_tag,
          with_type=with_type,
          with_proto_type_url=with_proto_type_url,
          with_substring=with_substring,
      ):
        # pytype: enable=attribute-error
        all_results.append(
            flows_pb2.FlowResult(
                hunt_id=hunt_id,
                client_id=flow_obj.client_id,
                flow_id=flow_obj.flow_id,
                timestamp=entry.timestamp,
                tag=entry.tag,
                payload=entry.payload,
            )
        )

    if with_timestamp:
      all_results = [r for r in all_results if r.timestamp == with_timestamp]

    all_results.sort(key=lambda x: x.timestamp)
    return all_results[offset : offset + count]

  @utils.Synchronized
  def CountHuntResults(
      self,
      hunt_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_proto_type_url: Optional[str] = None,
  ) -> int:
    """Counts hunt results of a given hunt using given query options."""
    return len(
        self.ReadHuntResults(
            hunt_id,
            0,
            sys.maxsize,
            with_tag=with_tag,
            with_type=with_type,
            with_proto_type_url=with_proto_type_url,
        )
    )

  @utils.Synchronized
  def CountHuntResultsByType(self, hunt_id: str) -> Mapping[str, int]:
    result = {}
    for hr in self.ReadHuntResults(hunt_id, 0, sys.maxsize):
      key = db_utils.TypeURLToRDFTypeName(hr.payload.type_url)
      result[key] = result.setdefault(key, 0) + 1

    return result

  @utils.Synchronized
  def CountHuntResultsByProtoTypeUrl(self, hunt_id: str) -> Mapping[str, int]:
    results_by_type_url = collections.Counter()
    for flow_result in self.ReadHuntResults(hunt_id, 0, sys.maxsize):
      results_by_type_url[flow_result.payload.type_url] += 1
    return results_by_type_url

  @utils.Synchronized
  def ReadHuntFlows(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      filter_condition: db.HuntFlowsCondition = db.HuntFlowsCondition.UNSET,
  ) -> Sequence[flows_pb2.Flow]:
    """Reads hunt flows matching given conditins."""
    if filter_condition == db.HuntFlowsCondition.UNSET:
      filter_fn = lambda _: True
    elif filter_condition == db.HuntFlowsCondition.FAILED_FLOWS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.ERROR
    elif filter_condition == db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.FINISHED
    elif filter_condition == db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY:
      filter_fn = lambda f: f.flow_state in [
          f.FlowState.ERROR,
          f.FlowState.FINISHED,
      ]
    elif filter_condition == db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.RUNNING
    elif filter_condition == db.HuntFlowsCondition.CRASHED_FLOWS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.CRASHED
    else:
      raise ValueError("Invalid filter condition: %d" % filter_condition)

    results = [
        flow_obj
        for flow_obj in self._GetHuntFlows(hunt_id)
        if filter_fn(flow_obj)
    ]
    results.sort(key=lambda f: f.last_update_time)
    results = results[offset : offset + count]
    return results

  @utils.Synchronized
  def CountHuntFlows(
      self,
      hunt_id: str,
      filter_condition: Optional[
          db.HuntFlowsCondition
      ] = db.HuntFlowsCondition.UNSET,
  ) -> int:
    """Counts hunt flows matching given conditions."""

    return len(
        self.ReadHuntFlows(
            hunt_id, 0, sys.maxsize, filter_condition=filter_condition
        )
    )

  @utils.Synchronized
  def ReadHuntsCounters(
      self,
      hunt_ids: Collection[str],
  ) -> Mapping[str, db.HuntCounters]:
    """Reads hunt counters for several hunt ids."""
    hunt_counters = {}
    for hunt_id in hunt_ids:
      num_clients = self.CountHuntFlows(hunt_id)
      num_successful_clients = self.CountHuntFlows(
          hunt_id, filter_condition=db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY
      )
      num_failed_clients = self.CountHuntFlows(
          hunt_id, filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY
      )
      num_clients_with_results = len(
          set(
              r[0].client_id
              for r in self.flow_results.values()
              if r and r[0].hunt_id == hunt_id
          )
      )
      num_crashed_clients = self.CountHuntFlows(
          hunt_id, filter_condition=db.HuntFlowsCondition.CRASHED_FLOWS_ONLY
      )
      num_running_clients = self.CountHuntFlows(
          hunt_id, filter_condition=db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY
      )
      num_results = self.CountHuntResults(hunt_id)

      total_cpu_seconds = 0
      total_network_bytes_sent = 0
      for f in self.ReadHuntFlows(hunt_id, 0, sys.maxsize):
        total_cpu_seconds += (
            f.cpu_time_used.user_cpu_time + f.cpu_time_used.system_cpu_time
        )
        total_network_bytes_sent += f.network_bytes_sent

      hunt_counters[hunt_id] = db.HuntCounters(
          num_clients=num_clients,
          num_successful_clients=num_successful_clients,
          num_failed_clients=num_failed_clients,
          num_clients_with_results=num_clients_with_results,
          num_crashed_clients=num_crashed_clients,
          num_running_clients=num_running_clients,
          num_results=num_results,
          total_cpu_seconds=total_cpu_seconds,
          total_network_bytes_sent=total_network_bytes_sent,
      )
    return hunt_counters

  @utils.Synchronized
  def ReadHuntClientResourcesStats(
      self,
      hunt_id: str,
  ) -> jobs_pb2.ClientResourcesStats:
    """Read/calculate hunt client resources stats."""

    client_resources = []

    for f in self._GetHuntFlows(hunt_id):
      cr = jobs_pb2.ClientResources(
          session_id=str(rdfvalue.RDFURN(f.client_id).Add(f.flow_id)),
          client_id=str(rdf_client.ClientURN.FromHumanReadable(f.client_id)),
          cpu_usage=f.cpu_time_used,
          network_bytes_sent=f.network_bytes_sent,
      )
      client_resources.append(cr)

    result = InitializeClientResourcesStats(client_resources)

    return result

  @utils.Synchronized
  def ReadHuntFlowsStatesAndTimestamps(
      self,
      hunt_id: str,
  ) -> Sequence[db.FlowStateAndTimestamps]:
    """Reads hunt flows states and timestamps."""

    result = []
    for f in self._GetHuntFlows(hunt_id):
      result.append(
          db.FlowStateAndTimestamps(
              flow_state=f.flow_state,
              create_time=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                  f.create_time
              ),
              last_update_time=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                  f.last_update_time
              ),
          )
      )

    return result

  @utils.Synchronized
  def ReadHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads hunt output plugin log entries."""

    all_entries = []
    for flow_obj in self._GetHuntFlows(hunt_id):
      # ReadFlowOutputPluginLogEntries is implemented in the db.Database class.
      # pytype: disable=attribute-error
      for entry in self.ReadFlowOutputPluginLogEntries(
          flow_obj.client_id,
          flow_obj.flow_id,
          output_plugin_id,
          0,
          sys.maxsize,
          with_type=with_type,
      ):
        # pytype: enable=attribute-error
        all_entries.append(
            flows_pb2.FlowOutputPluginLogEntry(
                hunt_id=hunt_id,
                client_id=flow_obj.client_id,
                flow_id=flow_obj.flow_id,
                output_plugin_id=output_plugin_id,
                log_entry_type=entry.log_entry_type,
                timestamp=entry.timestamp,
                message=entry.message,
            )
        )
    all_entries.sort(key=lambda x: x.timestamp)
    return all_entries[offset : offset + count]

  @utils.Synchronized
  def CountHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> int:
    """Counts hunt output plugin log entries."""

    return len(
        self.ReadHuntOutputPluginLogEntries(
            hunt_id, output_plugin_id, 0, sys.maxsize, with_type=with_type
        )
    )
