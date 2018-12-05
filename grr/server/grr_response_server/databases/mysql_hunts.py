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

  def ReadHuntObject(self, hunt_id):
    raise NotImplementedError()

  def ReadAllHuntObjects(self):
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
