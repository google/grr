#!/usr/bin/env python
"""The in memory database methods for foreman rule handling."""

from collections.abc import Sequence

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import jobs_pb2


class InMemoryDBForemanRulesMixin(object):
  """InMemoryDB mixin for foreman rules related functions."""

  foreman_rules: Sequence[jobs_pb2.ForemanCondition]

  @utils.Synchronized
  def WriteForemanRule(self, rule: jobs_pb2.ForemanCondition) -> None:
    self.RemoveForemanRule(rule.hunt_id)
    self.foreman_rules.append(rule)

  @utils.Synchronized
  def RemoveForemanRule(self, hunt_id: str) -> None:
    self.foreman_rules = [r for r in self.foreman_rules if r.hunt_id != hunt_id]

  @utils.Synchronized
  def ReadAllForemanRules(self) -> Sequence[jobs_pb2.ForemanCondition]:
    return self.foreman_rules

  @utils.Synchronized
  def RemoveExpiredForemanRules(self) -> None:
    now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    self.foreman_rules = [
        r for r in self.foreman_rules if r.expiration_time >= now
    ]
