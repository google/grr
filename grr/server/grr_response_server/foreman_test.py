#!/usr/bin/env python
"""Tests for the GRR Foreman."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import queue_manager
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


class ForemanTests(test_lib.GRRBaseTest):
  """Tests the Foreman."""

  clients_launched = []

  def setUp(self):
    super(ForemanTests, self).setUp()
    aff4_grr.GRRAFF4Init().Run()

  def StartFlow(self, client_id, flow_name, token=None, **kw):
    # Make sure the foreman is launching these
    self.assertEqual(token.username, "Foreman")

    # Make sure we pass the argv along
    self.assertEqual(kw["foo"], "bar")

    # Keep a record of all the clients
    self.clients_launched.append((client_id, flow_name))

  def testOperatingSystemSelection(self):
    """Tests that we can distinguish based on operating system."""
    self.SetupClient(1, system="Windows XP")
    self.SetupClient(2, system="Linux")
    self.SetupClient(3, system="Windows 7")

    with utils.Stubber(flow, "StartAFF4Flow", self.StartFlow):
      # Now setup the filters
      now = rdfvalue.RDFDatetime.Now()
      expires = now + rdfvalue.Duration("1h")
      foreman_obj = foreman.GetForeman(token=self.token)

      # Make a new rule
      rule = foreman_rules.ForemanRule(
          created=now, expires=expires, description="Test rule")

      # Matches Windows boxes
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.OS,
              os=foreman_rules.ForemanOsClientRule(os_windows=True))
      ])

      # Will run Test Flow
      rule.actions.Append(
          flow_name="Test Flow", argv=rdf_protodict.Dict(foo="bar"))

      # Clear the rule set and add the new rule to it.
      rule_set = foreman_obj.Schema.RULES()
      rule_set.Append(rule)

      # Assign it to the foreman
      foreman_obj.Set(foreman_obj.Schema.RULES, rule_set)
      foreman_obj.Close()

      self.clients_launched = []
      foreman_obj.AssignTasksToClient(u"C.1000000000000001")
      foreman_obj.AssignTasksToClient(u"C.1000000000000002")
      foreman_obj.AssignTasksToClient(u"C.1000000000000003")

      # Make sure that only the windows machines ran
      self.assertLen(self.clients_launched, 2)
      self.assertEqual(self.clients_launched[0][0],
                       rdf_client.ClientURN(u"C.1000000000000001"))
      self.assertEqual(self.clients_launched[1][0],
                       rdf_client.ClientURN(u"C.1000000000000003"))

      self.clients_launched = []

      # Run again - This should not fire since it did already
      foreman_obj.AssignTasksToClient(u"C.1000000000000001")
      foreman_obj.AssignTasksToClient(u"C.1000000000000002")
      foreman_obj.AssignTasksToClient(u"C.1000000000000003")

      self.assertEmpty(self.clients_launched)

  def testIntegerComparisons(self):
    """Tests that we can use integer matching rules on the foreman."""

    base_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1336480583.077736)
    boot_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1336300000.000000)

    self.SetupClient(0x11, system="Windows XP", install_time=base_time)
    self.SetupClient(0x12, system="Windows 7", install_time=base_time)
    # This one was installed one week earlier.
    one_week_ago = base_time - rdfvalue.Duration("1w")
    self.SetupClient(0x13, system="Windows 7", install_time=one_week_ago)
    self.SetupClient(0x14, system="Windows 7", last_boot_time=boot_time)

    with utils.Stubber(flow, "StartAFF4Flow", self.StartFlow):
      # Now setup the filters
      now = rdfvalue.RDFDatetime.Now()
      expires = now + rdfvalue.Duration("1h")
      foreman_obj = foreman.GetForeman(token=self.token)

      # Make a new rule
      rule = foreman_rules.ForemanRule(
          created=now, expires=expires, description="Test rule(old)")

      # Matches the old client
      one_hour_ago = base_time - rdfvalue.Duration("1h")
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
              integer=foreman_rules.ForemanIntegerClientRule(
                  field="INSTALL_TIME",
                  operator=foreman_rules.ForemanIntegerClientRule.Operator
                  .LESS_THAN,
                  value=one_hour_ago.AsSecondsSinceEpoch()))
      ])

      old_flow = "Test flow for old clients"
      # Will run Test Flow
      rule.actions.Append(
          flow_name=old_flow, argv=rdf_protodict.Dict(dict(foo="bar")))

      # Clear the rule set and add the new rule to it.
      rule_set = foreman_obj.Schema.RULES()
      rule_set.Append(rule)

      # Make a new rule
      rule = foreman_rules.ForemanRule(
          created=now, expires=expires, description="Test rule(new)")

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

      new_flow = "Test flow for newer clients"

      # Will run Test Flow
      rule.actions.Append(
          flow_name=new_flow, argv=rdf_protodict.Dict(dict(foo="bar")))

      rule_set.Append(rule)

      # Make a new rule
      rule = foreman_rules.ForemanRule(
          created=now, expires=expires, description="Test rule(eq)")

      # Note that this also tests the handling of nonexistent attributes.
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
              integer=foreman_rules.ForemanIntegerClientRule(
                  field="LAST_BOOT_TIME",
                  operator="EQUAL",
                  value=boot_time.AsSecondsSinceEpoch()))
      ])

      eq_flow = "Test flow for LAST_BOOT_TIME"

      rule.actions.Append(
          flow_name=eq_flow, argv=rdf_protodict.Dict(dict(foo="bar")))

      rule_set.Append(rule)

      # Assign it to the foreman
      foreman_obj.Set(foreman_obj.Schema.RULES, rule_set)
      foreman_obj.Close()

      self.clients_launched = []
      foreman_obj.AssignTasksToClient(u"C.1000000000000011")
      foreman_obj.AssignTasksToClient(u"C.1000000000000012")
      foreman_obj.AssignTasksToClient(u"C.1000000000000013")
      foreman_obj.AssignTasksToClient(u"C.1000000000000014")

      # Make sure that the clients ran the correct flows.
      self.assertLen(self.clients_launched, 4)
      self.assertEqual(self.clients_launched[0][0],
                       rdf_client.ClientURN(u"C.1000000000000011"))
      self.assertEqual(self.clients_launched[0][1], new_flow)
      self.assertEqual(self.clients_launched[1][0],
                       rdf_client.ClientURN(u"C.1000000000000012"))
      self.assertEqual(self.clients_launched[1][1], new_flow)
      self.assertEqual(self.clients_launched[2][0],
                       rdf_client.ClientURN(u"C.1000000000000013"))
      self.assertEqual(self.clients_launched[2][1], old_flow)
      self.assertEqual(self.clients_launched[3][0],
                       rdf_client.ClientURN(u"C.1000000000000014"))
      self.assertEqual(self.clients_launched[3][1], eq_flow)

  def testRuleExpiration(self):
    with test_lib.FakeTime(1000):
      foreman_obj = foreman.GetForeman(token=self.token)
      hunt_id = rdfvalue.SessionID("aff4:/hunts/foremantest")

      rules = []
      rules.append(
          foreman_rules.ForemanRule(
              created=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expires=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1500),
              description="Test rule1"))
      rules.append(
          foreman_rules.ForemanRule(
              created=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expires=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1200),
              description="Test rule2"))
      rules.append(
          foreman_rules.ForemanRule(
              created=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expires=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1500),
              description="Test rule3"))
      rules.append(
          foreman_rules.ForemanRule(
              created=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expires=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1300),
              description="Test rule4",
              actions=[foreman_rules.ForemanRuleAction(hunt_id=hunt_id)]))

      client_id = u"C.0000000000000021"
      fd = aff4.FACTORY.Create(
          client_id, aff4_grr.VFSGRRClient, token=self.token)
      fd.Close()

      # Clear the rule set and add the new rules to it.
      rule_set = foreman_obj.Schema.RULES()
      for rule in rules:
        # Add some regex that does not match the client.
        rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
                regex=foreman_rules.ForemanRegexClientRule(
                    field="SYSTEM", attribute_regex="XXX"))
        ])
        rule_set.Append(rule)
      foreman_obj.Set(foreman_obj.Schema.RULES, rule_set)
      foreman_obj.Close()

    fd = aff4.FACTORY.Create(client_id, aff4_grr.VFSGRRClient, token=self.token)
    for now, num_rules in [(1000, 4), (1250, 3), (1350, 2), (1600, 0)]:
      with test_lib.FakeTime(now):
        fd.Set(fd.Schema.LAST_FOREMAN_TIME(100))
        fd.Flush()
        foreman_obj = foreman.GetForeman(token=self.token)
        foreman_obj.AssignTasksToClient(client_id)
        rules = foreman_obj.Get(foreman_obj.Schema.RULES)
        self.assertLen(rules, num_rules)

    # Expiring rules that trigger hunts creates a notification for that hunt.
    with queue_manager.QueueManager(token=self.token) as manager:
      notifications = manager.GetNotificationsForAllShards(hunt_id.Queue())
      self.assertLen(notifications, 1)
      self.assertEqual(notifications[0].session_id, hunt_id)


class RelationalForemanTests(db_test_lib.RelationalDBEnabledMixin,
                             test_lib.GRRBaseTest):
  """Tests the Foreman."""

  clients_started = []

  def StartClients(self, hunt_id, clients):
    # Keep a record of all the clients
    for client in clients:
      self.clients_started.append((hunt_id, client))

  def testOperatingSystemSelection(self):
    """Tests that we can distinguish based on operating system."""
    self.SetupTestClientObject(1, system="Windows XP")
    self.SetupTestClientObject(2, system="Linux")
    self.SetupTestClientObject(3, system="Windows 7")

    with utils.Stubber(implementation.GRRHunt, "StartClients",
                       self.StartClients):
      # Now setup the filters
      now = rdfvalue.RDFDatetime.Now()
      expiration_time = now + rdfvalue.Duration("1h")

      # Make a new rule
      rule = foreman_rules.ForemanCondition(
          creation_time=now,
          expiration_time=expiration_time,
          description="Test rule",
          hunt_name=standard.GenericHunt.__name__,
          hunt_id="H:111111")

      # Matches Windows boxes
      rule.client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
          foreman_rules.ForemanClientRule(
              rule_type=foreman_rules.ForemanClientRule.Type.OS,
              os=foreman_rules.ForemanOsClientRule(os_windows=True))
      ])

      data_store.REL_DB.WriteForemanRule(rule)

      self.clients_started = []
      foreman_obj = foreman.GetForeman()
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

    self.SetupTestClientObject(
        0x11, system="Windows XP", install_time=base_time)
    self.SetupTestClientObject(0x12, system="Windows 7", install_time=base_time)
    # This one was installed one week earlier.
    one_week_ago = base_time - rdfvalue.Duration("1w")
    self.SetupTestClientObject(
        0x13, system="Windows 7", install_time=one_week_ago)
    self.SetupTestClientObject(
        0x14, system="Windows 7", last_boot_time=boot_time)

    with utils.Stubber(implementation.GRRHunt, "StartClients",
                       self.StartClients):
      now = rdfvalue.RDFDatetime.Now()
      expiration_time = now + rdfvalue.Duration("1h")

      # Make a new rule
      rule = foreman_rules.ForemanCondition(
          creation_time=now,
          expiration_time=expiration_time,
          description="Test rule(old)",
          hunt_name=standard.GenericHunt.__name__,
          hunt_id="H:111111")

      # Matches the old client
      one_hour_ago = base_time - rdfvalue.Duration("1h")
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
          hunt_name=standard.GenericHunt.__name__,
          hunt_id="H:222222")

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
          hunt_name=standard.GenericHunt.__name__,
          hunt_id="H:333333")

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

      foreman_obj = foreman.GetForeman()

      self.clients_started = []
      foreman_obj.AssignTasksToClient(u"C.1000000000000011")
      foreman_obj.AssignTasksToClient(u"C.1000000000000012")
      foreman_obj.AssignTasksToClient(u"C.1000000000000013")
      foreman_obj.AssignTasksToClient(u"C.1000000000000014")

      # Make sure that the clients ran the correct flows.
      self.assertLen(self.clients_started, 4)
      self.assertEqual(self.clients_started[0][1], u"C.1000000000000011")
      self.assertEqual("H:222222", self.clients_started[0][0].Basename())
      self.assertEqual(self.clients_started[1][1], u"C.1000000000000012")
      self.assertEqual("H:222222", self.clients_started[1][0].Basename())
      self.assertEqual(self.clients_started[2][1], u"C.1000000000000013")
      self.assertEqual("H:111111", self.clients_started[2][0].Basename())
      self.assertEqual(self.clients_started[3][1], u"C.1000000000000014")
      self.assertEqual("H:333333", self.clients_started[3][0].Basename())

  def testRuleExpiration(self):
    with test_lib.FakeTime(1000):
      foreman_obj = foreman.GetForeman()

      rules = []
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1500),
              description="Test rule1",
              hunt_id="H:111111"))
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1200),
              description="Test rule2",
              hunt_id="H:222222"))
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1500),
              description="Test rule3",
              hunt_id="H:333333"))
      rules.append(
          foreman_rules.ForemanCondition(
              creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000),
              expiration_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1300),
              description="Test rule4",
              hunt_id="H:444444"))

      client_id = self.SetupTestClientObject(0x21).client_id

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
  flags.StartMain(main)
