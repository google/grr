#!/usr/bin/env python
"""The in memory database methods for hunt handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


class InMemoryDBHuntMixin(object):
  """Hunts-related DB methods implementation."""

  def _GetHuntFlows(self, hunt_id):
    return [f for f in self.flows.values() if f.parent_hunt_id == hunt_id]

  @utils.Synchronized
  def WriteHuntObject(self, hunt_obj):
    """Writes a hunt object to the database."""
    clone = hunt_obj.Copy()
    clone.last_update_time = rdfvalue.RDFDatetime.Now()
    self.hunts[(hunt_obj.hunt_id)] = clone

  @utils.Synchronized
  def ReadHuntObject(self, hunt_id):
    """Reads a hunt object from the database."""
    try:
      return self.hunts[hunt_id].Copy()
    except KeyError:
      raise db.UnknownHuntError(hunt_id)

  @utils.Synchronized
  def ReadAllHuntObjects(self):
    """Reads all hunt objects from the database."""
    return [h.Copy() for h in self.hunts.values()]

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
                      with_substring=None):
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

    return sorted(all_results, key=lambda x: x.timestamp)[offset:offset + count]

  @utils.Synchronized
  def CountHuntResults(self, hunt_id, with_tag=None, with_type=None):
    """Counts hunt results of a given hunt using given query options."""
    return len(
        self.ReadHuntResults(
            hunt_id, 0, sys.maxsize, with_tag=with_tag, with_type=with_type))

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
      filter_fn = lambda f: f.HasField("client_crash_info")
    elif filter_condition == db.HuntFlowsCondition.FLOWS_WITH_RESULTS_ONLY:
      filter_fn = (
          lambda f: self.ReadFlowResults(f.client_id, f.flow_id, 0, sys.maxsize)
      )
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
