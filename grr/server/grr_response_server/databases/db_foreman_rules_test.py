#!/usr/bin/env python
"""Mixin tests for storing Foreman rules in the relational db."""

from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db_test_utils


class DatabaseTestForemanRulesMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of foreman rules.
  """

  def _GetTestRule(
      self,
      hunt_id: str = "123456",
      expires: Optional[rdfvalue.RDFDatetime] = None,
  ) -> jobs_pb2.ForemanCondition:
    now = rdfvalue.RDFDatetime.Now()
    expiration_time = expires or now + rdfvalue.Duration.From(2, rdfvalue.WEEKS)
    condition = jobs_pb2.ForemanCondition(
        creation_time=now.AsMicrosecondsSinceEpoch(),
        expiration_time=expiration_time.AsMicrosecondsSinceEpoch(),
        description="Test rule",
        hunt_id=hunt_id,
    )
    integer_rule = jobs_pb2.ForemanIntegerClientRule(
        field="INSTALL_TIME",
        operator=jobs_pb2.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=now.AsMicrosecondsSinceEpoch(),
    )
    rule = jobs_pb2.ForemanClientRule(
        rule_type=jobs_pb2.ForemanClientRule.Type.INTEGER
    )
    rule.integer.CopyFrom(integer_rule)
    rule_set = jobs_pb2.ForemanClientRuleSet()
    rule_set.rules.add().CopyFrom(rule)
    condition.client_rule_set.CopyFrom(rule_set)

    return condition

  def testForemanRuleWrite(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)
    rule = self._GetTestRule(hunt_id)
    self.db.WriteForemanRule(rule)

    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 1)
    self.assertEqual(read[0], rule)

  def testForemanRuleRemove(self):
    db_test_utils.InitializeHunt(self.db, "123456")
    rule1 = self._GetTestRule("123456")
    self.db.WriteForemanRule(rule1)

    db_test_utils.InitializeHunt(self.db, "654321")
    rule2 = self._GetTestRule("654321")
    self.db.WriteForemanRule(rule2)

    db_test_utils.InitializeHunt(self.db, "ABCDEF")
    rule3 = self._GetTestRule("ABCDEF")
    self.db.WriteForemanRule(rule3)

    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 3)

    self.db.RemoveForemanRule("654321")
    read = self.db.ReadAllForemanRules()
    self.assertLen(read, 2)
    self.assertCountEqual(read, [rule1, rule3])

    self.db.RemoveForemanRule("123456")
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
