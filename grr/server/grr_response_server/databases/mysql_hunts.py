#!/usr/bin/env python
"""The MySQL database methods for flow handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server import db


class MySQLDBHuntMixin(object):
  """MySQLDB mixin for flow handling."""

  def WriteHuntObject(self, hunt_obj):
    raise NotImplementedError()

  def UpdateHuntObject(self, hunt_id, update_fn):
    raise NotImplementedError()

  def DeleteHuntObject(self, hunt_id):
    raise NotImplementedError()

  def ReadHuntObject(self, hunt_id):
    raise NotImplementedError()

  def ReadAllHuntObjects(self):
    raise NotImplementedError()

  def ReadHuntOutputPluginsStates(self, hunt_id):
    raise NotImplementedError()

  def WriteHuntOutputPluginsStates(self, hunt_id, states):
    raise NotImplementedError()

  def UpdateHuntOutputPluginState(self, hunt_id, state_index, update_fn):
    raise NotImplementedError()

  def ReadHuntLogEntries(self, hunt_id, offset, count, with_substring=None):
    raise NotImplementedError()

  def CountHuntLogEntries(self, hunt_id):
    raise NotImplementedError()

  def ReadHuntResults(self,
                      hunt_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    raise NotImplementedError()

  def CountHuntResults(self, hunt_id, with_tag=None, with_type=None):
    raise NotImplementedError()

  def CountHuntResultsByType(self, hunt_id):
    raise NotImplementedError()

  def ReadHuntFlows(self,
                    hunt_id,
                    offset,
                    count,
                    filter_condition=db.HuntFlowsCondition.UNSET):
    raise NotImplementedError()

  def CountHuntFlows(self,
                     hunt_id,
                     filter_condition=db.HuntFlowsCondition.UNSET):
    raise NotImplementedError()

  def ReadHuntCounters(self, hunt_id):
    raise NotImplementedError()

  def ReadHuntClientResourcesStats(self, hunt_id):
    raise NotImplementedError()

  def ReadHuntFlowsStatesAndTimestamps(self, hunt_id):
    raise NotImplementedError()

  def ReadHuntOutputPluginLogEntries(self,
                                     hunt_id,
                                     output_plugin_id,
                                     offset,
                                     count,
                                     with_type=None):
    """Reads hunt output plugin log entries."""
    raise NotImplementedError()

  def CountHuntOutputPluginLogEntries(self,
                                      hunt_id,
                                      output_plugin_id,
                                      with_type=None):
    """Counts hunt output plugin log entries."""
    raise NotImplementedError()
