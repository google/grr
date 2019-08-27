#!/usr/bin/env python
"""Tests for the GRR Foreman."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import data_store
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr.test_lib import test_lib


class ForemanTests(test_lib.GRRBaseTest):
  """Tests the Foreman."""

  clients_started = []

  def StartHuntFlowOnClient(self, client_id, hunt_id):
    # Keep a record of all the clients
    self.clients_started.append((hunt_id, client_id))

  def testOperatingSystemSelection(self):
    """Tests that we can distinguish based on operating system."""
    self.SetupClient(1, system="Windows XP")
    self.SetupClient(2, system="Linux")
    self.SetupClient(3, system="Windows 7")

    with utils.Stubber(hunt, "StartHuntFlowOnClient",
                       self.StartHuntFlowOnClient):
      # Now setup the filters
      now = rdfvalue.RDFDatetime.Now()
      expiration_time = now + rdfvalue.Duration.From(1, rdfvalue.HOURS)

      # Make a new rule
      rule = foreman_rules.ForemanCondition(
          creation_time=now,
          expiration_time=expiration_time,
          description="Test rule",
          hunt_id="111111")

      # Matches Windows boxes
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.OS,
              os=foreman_rules.ForemanOsClientRule(os_windows=True))
      ])

      data_store.REL_DB.WriteForemanRule(rule)

      self.clients_started = []
      foreman_obj = foreman.Foreman()
      foreman_obj.AssignTasksToClient(u"C.1000000000000001")
      foreman_obj.AssignTasksToClient(u"C.1000000000000002")
      foreman_obj.AssignTasksToClient(u"C.1000000000000003")

      # Make sure that only the windows machines ran
      self.assertLen(self.clients_started, 2)
      self.assertEqual(self.clients_started[0][1], u"C.1000000000000001")
      self.assertEqual(self.clients_started[1][1], u"C.1000000000000003")

      self.clients_started = []

      # Run again - This should not fire since it did already
      foreman_obj.AssignTasksToClient(u"C.1000000000000001")
      foreman_obj.AssignTasksToClient(u"C.1000000000000002")
      foreman_obj.AssignTasksToClient(u"C.1000000000000003")

      self.assertEmpty(self.clients_started)

  def testIntegerComparisons(self):
    """Tests that we can use integer matching rules on the foreman."""

    base_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1336480583.077736)
    boot_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1336300000.000000)

    self.SetupClient(0x11, system="Windows XP", install_time=base_time)
    self.SetupClient(0x12, system="Windows 7", install_time=base_time)
    # This one was installed one week earlier.
    one_week_ago = base_time - rdfvalue.Duration.From(1, rdfvalue.WEEKS)
    self.SetupClient(0x13, system="Windows 7", install_time=one_week_ago)
    self.SetupClient(0x14, system="Windows 7", last_boot_time=boot_time)

    with utils.Stubber(hunt, "StartHuntFlowOnClient",
                       self.StartHuntFlowOnClient):
      now = rdfvalue.RDFDatetime.Now()
      expiration_time = now + rdfvalue.Duration.From(1, rdfvalue.HOURS)

      # Make a new rule
      rule = foreman_rules.ForemanCondition(
          creation_time=now,
          expiration_time=expiration_time,
          description="Test rule(old)",
          hunt_id="111111")

      # Matches the old client
      one_hour_ago = base_time - rdfvalue.Duration.From(1, rdfvalue.HOURS)
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
              integer=foreman_rules.ForemanIntegerClientRule(
                  field="INSTALL_TIME",
                  operator=foreman_rules.ForemanIntegerClientRule.Operator
                  .LESS_THAN,
                  value=one_hour_ago.AsSecondsSinceEpoch()))
      ])

      data_store.REL_DB.WriteForemanRule(rule)

      # Make a new rule
      rule = foreman_rules.ForemanCondition(
          creation_time=now,
          expiration_time=expiration_time,
          description="Test rule(new)",
          hunt_id="222222")

      # Matches the newer clients
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
              integer=foreman_rules.ForemanIntegerClientRule(
                  field="INSTALL_TIME",
                  operator=foreman_rules.ForemanIntegerClientRule.Operator
                  .GREATER_THAN,
                  value=one_hour_ago.AsSecondsSinceEpoch()))
      ])

      data_store.REL_DB.WriteForemanRule(rule)

      # Make a new rule
      rule = foreman_rules.ForemanCondition(
          creation_time=now,
          expiration_time=expiration_time,
          description="Test rule(eq)",
          hunt_id="333333")

      # Note that this also tests the handling of nonexistent attributes.
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
              integer=foreman_rules.ForemanIntegerClientRule(
                  field="LAST_BOOT_TIME",
                  operator="EQUAL",
                  value=boot_time.AsSecondsSinceEpoch()))
      ])

      data_store.REL_DB.WriteForemanRule(rule)

      foreman_obj = foreman.Foreman()

      self.clients_started = []
      foreman_obj.AssignTasksToClient(u"C.1000000000000011")
      foreman_obj.AssignTasksToClient(u"C.1000000000000012")
      foreman_obj.AssignTasksToClient(u"C.1000000000000013")
      foreman_obj.AssignTasksToClient(u"C.1000000000000014")

      # Make sure that the clients ran the correct flows.
      self.assertLen(self.clients_started, 4)
      self.assertEqual(self.clients_started[0][1], u"C.1000000000000011")
      self.assertEqual("222222", self.clients_started[0][0])
      self.assertEqual(self.clients_started[1][1], u"C.1000000000000012")
      self.assertEqual("222222", self.clients_started[1][0])
      self.assertEqual(self.clients_started[2][1], u"C.1000000000000013")
      self.assertEqual("111111", self.clients_started[2][0])
      self.assertEqual(self.clients_started[3][1], u"C.1000000000000014")
      self.assertEqual("333333", self.clients_started[3][0])

  def testRuleExpiration(self):
    with test_lib.FakeTime(1000):
      foreman_obj = foreman.Foreman()

      rules = []
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1500),
              description="Test rule1",
              hunt_id="111111"))
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1200),
              description="Test rule2",
              hunt_id="222222"))
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1500),
              description="Test rule3",
              hunt_id="333333"))
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1300),
              description="Test rule4",
              hunt_id="444444"))

      client_id = self.SetupClient(0x21)

      # Clear the rule set and add the new rules to it.
      for rule in rules:
        # Add some regex that does not match the client.
        rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
                regex=foreman_rules.ForemanRegexClientRule(
                    field="SYSTEM", attribute_regex="XXX"))
        ])
        data_store.REL_DB.WriteForemanRule(rule)

    for now, num_rules in [(1000, 4), (1250, 3), (1350, 2), (1600, 0)]:
      with test_lib.FakeTime(now):
        data_store.REL_DB.WriteClientMetadata(
            client_id,
            last_foreman=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))
        foreman_obj.AssignTasksToClient(client_id)
        rules = data_store.REL_DB.ReadAllForemanRules()
        self.assertLen(rules, num_rules)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
