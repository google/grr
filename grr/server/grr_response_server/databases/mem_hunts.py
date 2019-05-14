#!/usr/bin/env python
"""The in memory database methods for hunt handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import compatibility
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects


class InMemoryDBHuntMixin(object):
  """Hunts-related DB methods implementation."""

  def _GetHuntFlows(self, hunt_id):
    top_level_flows = [
        f for f in self.flows.values()
        if f.parent_hunt_id == hunt_id and not f.parent_flow_id
    ]
    return sorted(top_level_flows, key=lambda f: f.client_id)

  @utils.Synchronized
  def WriteHuntObject(self, hunt_obj):
    """Writes a hunt object to the database."""
    if hunt_obj.hunt_id in self.hunts:
      raise db.DuplicatedHuntError(hunt_id=hunt_obj.hunt_id)

    clone = self._DeepCopy(hunt_obj)
    clone.create_time = rdfvalue.RDFDatetime.Now()
    clone.last_update_time = rdfvalue.RDFDatetime.Now()
    self.hunts[(hunt_obj.hunt_id)] = clone

  @utils.Synchronized
  def UpdateHuntObject(self, hunt_id, start_time=None, **kwargs):
    """Updates the hunt object by applying the update function."""
    hunt_obj = self.ReadHuntObject(hunt_id)

    delta_suffix = "_delta"

    for k, v in kwargs.items():
      if v is None:
        continue

      if k.endswith(delta_suffix):
        key = k[:-len(delta_suffix)]
        current_value = getattr(hunt_obj, key)
        setattr(hunt_obj, key, current_value + v)
      else:
        setattr(hunt_obj, k, v)

    if start_time is not None:
      hunt_obj.init_start_time = hunt_obj.init_start_time or start_time
      hunt_obj.last_start_time = start_time

    hunt_obj.last_update_time = rdfvalue.RDFDatetime.Now()
    self.hunts[hunt_obj.hunt_id] = hunt_obj

  @utils.Synchronized
  def ReadHuntOutputPluginsStates(self, hunt_id):
    if hunt_id not in self.hunts:
      raise db.UnknownHuntError(hunt_id)

    serialized_states = self.hunt_output_plugins_states.get(hunt_id, [])
    return [
        rdf_flow_runner.OutputPluginState.FromSerializedString(s)
        for s in serialized_states
    ]

  @utils.Synchronized
  def WriteHuntOutputPluginsStates(self, hunt_id, states):

    if hunt_id not in self.hunts:
      raise db.UnknownHuntError(hunt_id)

    self.hunt_output_plugins_states[hunt_id] = [
        s.SerializeToString() for s in states
    ]

  @utils.Synchronized
  def UpdateHuntOutputPluginState(self, hunt_id, state_index, update_fn):
    """Updates hunt output plugin state for a given output plugin."""

    if hunt_id not in self.hunts:
      raise db.UnknownHuntError(hunt_id)

    try:
      state = rdf_flow_runner.OutputPluginState.FromSerializedString(
          self.hunt_output_plugins_states[hunt_id][state_index])
    except KeyError:
      raise db.UnknownHuntOutputPluginError(hunt_id, state_index)

    state.plugin_state = update_fn(state.plugin_state)

    self.hunt_output_plugins_states[hunt_id][
        state_index] = state.SerializeToString()

    return state.plugin_state

  @utils.Synchronized
  def DeleteHuntObject(self, hunt_id):
    try:
      del self.hunts[hunt_id]
    except KeyError:
      raise db.UnknownHuntError(hunt_id)

  @utils.Synchronized
  def ReadHuntObject(self, hunt_id):
    """Reads a hunt object from the database."""
    try:
      return self._DeepCopy(self.hunts[hunt_id])
    except KeyError:
      raise db.UnknownHuntError(hunt_id)

  @utils.Synchronized
  def ReadHuntObjects(self,
                      offset,
                      count,
                      with_creator=None,
                      created_after=None,
                      with_description_match=None):
    """Reads metadata for hunt objects from the database."""
    filter_fns = []
    if with_creator is not None:
      filter_fns.append(lambda h: h.creator == with_creator)
    if created_after is not None:
      filter_fns.append(lambda h: h.create_time > created_after)
    if with_description_match is not None:
      filter_fns.append(lambda h: with_description_match in h.description)
    filter_fn = lambda h: all(f(h) for f in filter_fns)

    result = [self._DeepCopy(h) for h in self.hunts.values() if filter_fn(h)]
    return sorted(
        result, key=lambda h: h.create_time,
        reverse=True)[offset:offset + (count or db.MAX_COUNT)]

  @utils.Synchronized
  def ListHuntObjects(self,
                      offset,
                      count,
                      with_creator=None,
                      created_after=None,
                      with_description_match=None):
    """Reads all hunt objects from the database."""
    filter_fns = []
    if with_creator is not None:
      filter_fns.append(lambda h: h.creator == with_creator)
    if created_after is not None:
      filter_fns.append(lambda h: h.create_time > created_after)
    if with_description_match is not None:
      filter_fns.append(lambda h: with_description_match in h.description)
    filter_fn = lambda h: all(f(h) for f in filter_fns)

    result = []
    for h in self.hunts.values():
      if not filter_fn(h):
        continue
      result.append(rdf_hunt_objects.HuntMetadata.FromHunt(h))

    return sorted(
        result, key=lambda h: h.create_time,
        reverse=True)[offset:offset + (count or db.MAX_COUNT)]

  @utils.Synchronized
  def ReadHuntLogEntries(self, hunt_id, offset, count, with_substring=None):
    """Reads hunt log entries of a given hunt using given query options."""
    all_entries = []
    for flow_obj in self._GetHuntFlows(hunt_id):
      for entry in self.ReadFlowLogEntries(
          flow_obj.client_id,
          flow_obj.flow_id,
          0,
          sys.maxsize,
          with_substring=with_substring):

        all_entries.append(
            rdf_flow_objects.FlowLogEntry(
                hunt_id=hunt_id,
                client_id=flow_obj.client_id,
                flow_id=flow_obj.flow_id,
                timestamp=entry.timestamp,
                message=entry.message))

    return sorted(all_entries, key=lambda x: x.timestamp)[offset:offset + count]

  @utils.Synchronized
  def CountHuntLogEntries(self, hunt_id):
    """Returns number of hunt log entries of a given hunt."""
    return len(self.ReadHuntLogEntries(hunt_id, 0, sys.maxsize))

  @utils.Synchronized
  def ReadHuntResults(self,
                      hunt_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None,
                      with_timestamp=None):
    """Reads hunt results of a given hunt using given query options."""
    all_results = []
    for flow_obj in self._GetHuntFlows(hunt_id):
      for entry in self.ReadFlowResults(
          flow_obj.client_id,
          flow_obj.flow_id,
          0,
          sys.maxsize,
          with_tag=with_tag,
          with_type=with_type,
          with_substring=with_substring):
        all_results.append(
            rdf_flow_objects.FlowResult(
                hunt_id=hunt_id,
                client_id=flow_obj.client_id,
                flow_id=flow_obj.flow_id,
                timestamp=entry.timestamp,
                tag=entry.tag,
                payload=entry.payload))

    if with_timestamp:
      all_results = [r for r in all_results if r.timestamp == with_timestamp]

    return sorted(all_results, key=lambda x: x.timestamp)[offset:offset + count]

  @utils.Synchronized
  def CountHuntResults(self, hunt_id, with_tag=None, with_type=None):
    """Counts hunt results of a given hunt using given query options."""
    return len(
        self.ReadHuntResults(
            hunt_id, 0, sys.maxsize, with_tag=with_tag, with_type=with_type))

  @utils.Synchronized
  def CountHuntResultsByType(self, hunt_id):
    result = {}
    for hr in self.ReadHuntResults(hunt_id, 0, sys.maxsize):
      key = compatibility.GetName(hr.payload.__class__)
      result[key] = result.setdefault(key, 0) + 1

    return result

  @utils.Synchronized
  def ReadHuntFlows(self,
                    hunt_id,
                    offset,
                    count,
                    filter_condition=db.HuntFlowsCondition.UNSET):
    """Reads hunt flows matching given conditins."""
    if filter_condition == db.HuntFlowsCondition.UNSET:
      filter_fn = lambda _: True
    elif filter_condition == db.HuntFlowsCondition.FAILED_FLOWS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.ERROR
    elif filter_condition == db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.FINISHED
    elif filter_condition == db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY:
      filter_fn = (
          lambda f: f.flow_state in [f.FlowState.ERROR, f.FlowState.FINISHED])
    elif filter_condition == db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.RUNNING
    elif filter_condition == db.HuntFlowsCondition.CRASHED_FLOWS_ONLY:
      filter_fn = lambda f: f.flow_state == f.FlowState.CRASHED
    else:
      raise ValueError("Invalid filter condition: %d" % filter_condition)

    results = [
        flow_obj for flow_obj in self._GetHuntFlows(hunt_id)
        if filter_fn(flow_obj)
    ]
    results.sort(key=lambda f: f.last_update_time)
    return results[offset:offset + count]

  @utils.Synchronized
  def CountHuntFlows(self,
                     hunt_id,
                     filter_condition=db.HuntFlowsCondition.UNSET):
    """Counts hunt flows matching given conditions."""

    return len(
        self.ReadHuntFlows(
            hunt_id, 0, sys.maxsize, filter_condition=filter_condition))

  @utils.Synchronized
  def ReadHuntCounters(self, hunt_id):
    """Reads hunt counters."""
    num_clients = self.CountHuntFlows(hunt_id)
    num_successful_clients = self.CountHuntFlows(
        hunt_id, filter_condition=db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY)
    num_failed_clients = self.CountHuntFlows(
        hunt_id, filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY)
    num_clients_with_results = len(
        set(r[0].client_id
            for r in self.flow_results.values()
            if r and r[0].hunt_id == hunt_id))
    num_crashed_clients = self.CountHuntFlows(
        hunt_id, filter_condition=db.HuntFlowsCondition.CRASHED_FLOWS_ONLY)
    num_results = self.CountHuntResults(hunt_id)

    total_cpu_seconds = 0
    total_network_bytes_sent = 0
    for f in self.ReadHuntFlows(hunt_id, 0, sys.maxsize):
      total_cpu_seconds += (
          f.cpu_time_used.user_cpu_time + f.cpu_time_used.system_cpu_time)
      total_network_bytes_sent += f.network_bytes_sent

    return db.HuntCounters(
        num_clients=num_clients,
        num_successful_clients=num_successful_clients,
        num_failed_clients=num_failed_clients,
        num_clients_with_results=num_clients_with_results,
        num_crashed_clients=num_crashed_clients,
        num_results=num_results,
        total_cpu_seconds=total_cpu_seconds,
        total_network_bytes_sent=total_network_bytes_sent)

  @utils.Synchronized
  def ReadHuntClientResourcesStats(self, hunt_id):
    """Read/calculate hunt client resources stats."""

    result = rdf_stats.ClientResourcesStats()
    for f in self._GetHuntFlows(hunt_id):
      cr = rdf_client_stats.ClientResources(
          session_id="%s/%s" % (f.client_id, f.flow_id),
          client_id=f.client_id,
          cpu_usage=f.cpu_time_used,
          network_bytes_sent=f.network_bytes_sent)
      result.RegisterResources(cr)

    # TODO(user): remove this hack when compatibility with AFF4 is not
    # important.
    return rdf_stats.ClientResourcesStats.FromSerializedString(
        result.SerializeToString())

  @utils.Synchronized
  def ReadHuntFlowsStatesAndTimestamps(self, hunt_id):
    """Reads hunt flows states and timestamps."""

    result = []
    for f in self._GetHuntFlows(hunt_id):
      result.append(
          db.FlowStateAndTimestamps(
              flow_state=f.flow_state,
              create_time=f.create_time,
              last_update_time=f.last_update_time))

    return result

  @utils.Synchronized
  def ReadHuntOutputPluginLogEntries(self,
                                     hunt_id,
                                     output_plugin_id,
                                     offset,
                                     count,
                                     with_type=None):
    """Reads hunt output plugin log entries."""

    all_entries = []
    for flow_obj in self._GetHuntFlows(hunt_id):
      for entry in self.ReadFlowOutputPluginLogEntries(
          flow_obj.client_id,
          flow_obj.flow_id,
          output_plugin_id,
          0,
          sys.maxsize,
          with_type=with_type):
        all_entries.append(
            rdf_flow_objects.FlowOutputPluginLogEntry(
                hunt_id=hunt_id,
                client_id=flow_obj.client_id,
                flow_id=flow_obj.flow_id,
                output_plugin_id=output_plugin_id,
                log_entry_type=entry.log_entry_type,
                timestamp=entry.timestamp,
                message=entry.message))

    return sorted(all_entries, key=lambda x: x.timestamp)[offset:offset + count]

  @utils.Synchronized
  def CountHuntOutputPluginLogEntries(self,
                                      hunt_id,
                                      output_plugin_id,
                                      with_type=None):
    """Counts hunt output plugin log entries."""

    return len(
        self.ReadHuntOutputPluginLogEntries(
            hunt_id, output_plugin_id, 0, sys.maxsize, with_type=with_type))
