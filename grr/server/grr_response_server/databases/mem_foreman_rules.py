#!/usr/bin/env python
"""The in memory database methods for foreman rule handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils


class InMemoryDBForemanRulesMixin(object):
  """InMemoryDB mixin for foreman rules related functions."""

  @utils.Synchronized
  def WriteForemanRule(self, rule):
    self.RemoveForemanRule(rule.hunt_id)
    self.foreman_rules.append(rule)

  @utils.Synchronized
  def RemoveForemanRule(self, hunt_id):
    self.foreman_rules = [r for r in self.foreman_rules if r.hunt_id != hunt_id]

  @utils.Synchronized
  def ReadAllForemanRules(self):
    return self.foreman_rules

  @utils.Synchronized
  def RemoveExpiredForemanRules(self):
    now = rdfvalue.RDFDatetime.Now()
    self.foreman_rules = [
        r for r in self.foreman_rules if r.expiration_time >= now
    ]
