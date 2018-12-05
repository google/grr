#!/usr/bin/env python
"""Mixin tests for storing Foreman rules in the relational db."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_server import foreman_rules
from grr.test_lib import test_lib


class DatabaseTestForemanRulesMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of foreman rules.
  """

  def _GetTestRule(self, hunt_id="H:123456", expires=None):
    now = rdfvalue.RDFDatetime.Now()
    expiration_time = expires or now + rdfvalue.Duration("2w")
    rule = foreman_rules.ForemanCondition(
        creation_time=now,
        expiration_time=expiration_time,
        description="Test rule",
        hunt_id=hunt_id)
    rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
            integer=foreman_rules.ForemanIntegerClientRule(
                field="INSTALL_TIME",
                operator=foreman_rules.ForemanIntegerClientRule.Operator
                .LESS_THAN,
                value=now))
    ])
    return rule

  def testForemanRuleWrite(self):
    rule = self._GetTestRule()
    self.db.WriteForemanRule(rule)

    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 1)
    self.assertEqual(read[0], rule)

  def testForemanRuleRemove(self):
    rule1 = self._GetTestRule("H:123456")
    self.db.WriteForemanRule(rule1)
    rule2 = self._GetTestRule("H:654321")
    self.db.WriteForemanRule(rule2)
    rule3 = self._GetTestRule("H:ABCDEF")
    self.db.WriteForemanRule(rule3)

    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 3)

    self.db.RemoveForemanRule("H:654321")
    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 2)
    self.assertEqual(
        sorted(read, key=lambda rule: rule.hunt_id), [rule1, rule3])

    self.db.RemoveForemanRule("H:123456")
    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 1)
    self.assertEqual(read[0], rule3)

  def testForemanRuleExpire(self):

    for i, ex in enumerate([100, 200, 300, 400, 500, 600]):
      expires = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(ex)
      rule = self._GetTestRule("H:00000%d" % i, expires=expires)
      self.db.WriteForemanRule(rule)

    self.assertLen(self.db.ReadAllForemanRules(), 6)

    with test_lib.FakeTime(110):
      self.db.RemoveExpiredForemanRules()
      self.assertLen(self.db.ReadAllForemanRules(), 5)

    with test_lib.FakeTime(350):
      self.db.RemoveExpiredForemanRules()
      self.assertLen(self.db.ReadAllForemanRules(), 3)

    with test_lib.FakeTime(590):
      self.db.RemoveExpiredForemanRules()
      self.assertLen(self.db.ReadAllForemanRules(), 1)
