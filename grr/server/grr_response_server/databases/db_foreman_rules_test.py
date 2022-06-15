#!/usr/bin/env python
"""Mixin tests for storing Foreman rules in the relational db."""

from grr_response_core.lib import rdfvalue
from grr_response_server import foreman_rules
from grr_response_server.databases import db_test_utils


class DatabaseTestForemanRulesMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of foreman rules.
  """

  def _GetTestRule(self, hunt_id="123456", expires=None):
    now = rdfvalue.RDFDatetime.Now()
    expiration_time = expires or now + rdfvalue.Duration.From(2, rdfvalue.WEEKS)
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
    hunt_id = db_test_utils.InitializeHunt(self.db)
    rule = self._GetTestRule(hunt_id)
    self.db.WriteForemanRule(rule)

    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 1)
    self.assertEqual(read[0], rule)

  def testForemanRuleRemove(self):
    db_test_utils.InitializeHunt(self.db, "H:123456")
    rule1 = self._GetTestRule("H:123456")
    self.db.WriteForemanRule(rule1)

    db_test_utils.InitializeHunt(self.db, "H:654321")
    rule2 = self._GetTestRule("H:654321")
    self.db.WriteForemanRule(rule2)

    db_test_utils.InitializeHunt(self.db, "H:ABCDEF")
    rule3 = self._GetTestRule("H:ABCDEF")
    self.db.WriteForemanRule(rule3)

    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 3)

    self.db.RemoveForemanRule("H:654321")
    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 2)
    self.assertCountEqual(read, [rule1, rule3])

    self.db.RemoveForemanRule("H:123456")
    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 1)
    self.assertEqual(read[0], rule3)

  def testForemanRuleExpire(self):
    for i in range(3):
      db_test_utils.InitializeHunt(self.db, f"00000{i}")

      expires = self.db.Now() - rdfvalue.Duration("1s")
      rule = self._GetTestRule(f"00000{i}", expires=expires)
      self.db.WriteForemanRule(rule)

    for i in range(3, 5):
      db_test_utils.InitializeHunt(self.db, f"00000{i}")

      expires = self.db.Now() + rdfvalue.Duration("100s")
      rule = self._GetTestRule(f"00000{i}", expires=expires)
      self.db.WriteForemanRule(rule)

    self.assertLen(self.db.ReadAllForemanRules(), 5)

    # This should remove first 3 rules.
    self.db.RemoveExpiredForemanRules()

    self.assertLen(self.db.ReadAllForemanRules(), 2)


# This file is a test library and thus does not require a __main__ block.
