#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the hunt."""



import time


import logging

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow

# These imports populate the GRRHunt registry.
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class BrokenSampleHunt(hunts.SampleHunt):

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""
    client_id = responses.request.client_id

    if not responses.success:
      logging.info("Client %s has no file /tmp/evil.txt", client_id)
      # Raise on one of the code paths.
      raise RuntimeError("Error")
    else:
      logging.info("Client %s has a file /tmp/evil.txt", client_id)

    self.MarkClientDone(client_id)


class HuntTest(test_lib.FlowTestsBaseclass):
  """Tests the Hunt."""

  def testRuleAdding(self):

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)
    # Make sure there are no rules yet.
    self.assertEqual(len(rules), 0)

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="HUNT")

    int_rule = rdfvalue.ForemanAttributeInteger(
        attribute_name="Clock",
        operator=rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN,
        value=1336650631137737)

    hunt.AddRule([int_rule, regex_rule])
    # Push the rules to the foreman.
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)

    # Make sure they were written correctly.
    self.assertEqual(len(rules), 1)
    rule = rules[0]

    self.assertEqual(len(rule.regex_rules), 1)
    self.assertEqual(rule.regex_rules[0].attribute_name, "GRR client")
    self.assertEqual(rule.regex_rules[0].attribute_regex, "HUNT")

    self.assertEqual(len(rule.integer_rules), 1)
    self.assertEqual(rule.integer_rules[0].attribute_name, "Clock")
    self.assertEqual(rule.integer_rules[0].operator,
                     rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN)
    self.assertEqual(rule.integer_rules[0].value, 1336650631137737)

    self.assertEqual(len(rule.actions), 1)
    self.assertEqual(rule.actions[0].hunt_name, "SampleHunt")

    # Running a second time should not change the rules any more.
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)

    # Still just one rule.
    self.assertEqual(len(rules), 1)

  def AddForemanRules(self, to_add):
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES) or foreman.Schema.RULES()
    for rule in to_add:
      rules.Append(rule)
    foreman.Set(foreman.Schema.RULES, rules)
    foreman.Close()

  def testStopping(self):
    """Tests if we can stop a hunt."""

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)
    # Make sure there are no rules yet.
    self.assertEqual(len(rules), 0)
    now = int(time.time() * 1e6)
    expires = now + 3600
    # Add some rules.
    rules = [rdfvalue.ForemanRule(created=now, expires=expires,
                                  description="Test rule1"),
             rdfvalue.ForemanRule(created=now, expires=expires,
                                  description="Test rule2")]
    self.AddForemanRules(rules)

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="HUNT")
    int_rule = rdfvalue.ForemanAttributeInteger(
        attribute_name="Clock",
        operator=rdfvalue.ForemanAttributeInteger.Operator.GREATER_THAN,
        value=1336650631137737)
    # Fire on either of the rules.
    hunt.AddRule([int_rule])
    hunt.AddRule([regex_rule])
    # Push the rules to the foreman.
    hunt.Run()

    # Add some more rules.
    rules = [rdfvalue.ForemanRule(created=now, expires=expires,
                                  description="Test rule3"),
             rdfvalue.ForemanRule(created=now, expires=expires,
                                  description="Test rule4")]
    self.AddForemanRules(rules)

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)
    self.assertEqual(len(rules), 6)
    self.assertNotEqual(hunt.OutstandingRequests(), 0)

    # Now we stop the hunt.
    hunt.Stop()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)
    # The rule for this hunt should be deleted but the rest should be there.
    self.assertEqual(len(rules), 4)
    # And the hunt should report no outstanding requests any more.
    self.assertEqual(hunt.OutstandingRequests(), 0)

  def testInvalidRules(self):
    """Tests the behavior when a wrong attribute name is passed in a rule."""

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="no such attribute",
        attribute_regex="HUNT")
    self.assertRaises(RuntimeError, hunt.AddRule, [regex_rule])

  def Callback(self, hunt_id, client_id, client_limit):
    self.called.append((hunt_id, client_id, client_limit))

  def testCallback(self, client_limit=None):
    """Checks that the foreman uses the callback specified in the action."""

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", client_limit=client_limit,
                                   token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

    # Create a client that matches our regex.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    info = client.Schema.CLIENT_INFO()
    info.client_name = "GRR Monitor"
    client.Set(client.Schema.CLIENT_INFO, info)
    client.Close()

    old_start_client = hunts.SampleHunt.StartClient
    try:
      hunts.SampleHunt.StartClient = self.Callback
      self.called = []

      foreman.AssignTasksToClient(client.urn)

      self.assertEqual(len(self.called), 1)
      self.assertEqual(self.called[0][1], client.urn)

      # Clean up.
      foreman.Set(foreman.Schema.RULES())
      foreman.Close()
    finally:
      hunts.SampleHunt.StartClient = staticmethod(old_start_client)

  def testStartClient(self):
    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    hunt.Run()

    client = aff4.FACTORY.Open(self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    flows = list(client.GetValuesForAttribute(client.Schema.FLOW))

    self.assertEqual(flows, [])

    hunts.GRRHunt.StartClient(hunt.session_id, self.client_id)

    test_lib.TestHuntHelper(None, [self.client_id], False, self.token)

    client = aff4.FACTORY.Open(self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    flows = list(client.GetValuesForAttribute(client.Schema.FLOW))

    # One flow should have been started.
    self.assertEqual(len(flows), 1)

  def testCallbackWithLimit(self):

    self.assertRaises(RuntimeError, self.testCallback, 2000)

    self.testCallback(100)

  def testProcessing(self):
    """This tests running the hunt on some clients."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(
        hunt.session_id, mode="r", age=aff4.ALL_TIMES,
        aff4_type="SampleHunt", token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)

    self.assertEqual(len(set(started)), 10)
    self.assertEqual(len(set(finished)), 10)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testHangingClients(self):
    """This tests if the hunt completes when some clients hang or raise."""
    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    client_mock = test_lib.SampleHuntMock()
    # Just pass 8 clients to run, the other two went offline.
    test_lib.TestHuntHelper(client_mock, client_ids[1:9], False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)

    # We started the hunt on 10 clients.
    self.assertEqual(len(set(started)), 10)
    # But only 8 should have finished.
    self.assertEqual(len(set(finished)), 8)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testPausingAndRestartingDoesNotStartHuntTwiceOnTheSameClient(self):
    """This tests if the hunt completes when some clients hang or raise."""
    client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      num_tasks = foreman.AssignTasksToClient(client_id)
      self.assertEqual(num_tasks, 1)

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    # Pausing and running hunt: this leads to the fresh rules being written
    # to Foreman.RULES.
    hunt.Pause()
    hunt.Run()
    # Recreating the foreman so that it updates list of rules.
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      num_tasks = foreman.AssignTasksToClient(client_id)
      # No tasks should be assigned as this hunt ran of all the clients before.
      self.assertEqual(num_tasks, 0)

    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testClientLimit(self):
    """This tests that we can limit hunts to a number of clients."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt("SampleHunt", token=self.token,
                                   client_limit=5)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)

    # We limited here to 5 clients.
    self.assertEqual(len(set(started)), 5)
    self.assertEqual(len(set(finished)), 5)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testBrokenHunt(self):
    """This tests the behavior when a hunt raises an exception."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt("BrokenSampleHunt", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 10)
    # There should be errors for the five clients where the hunt raised.
    self.assertEqual(len(set(errors)), 5)
    # All of the clients that have the file should still finish eventually.
    self.assertEqual(len(set(finished)), 5)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testHuntNotifications(self):
    """This tests the Hunt notification event."""

    received_events = []

    class Listener1(flow.EventListener):  # pylint: disable=unused-variable
      well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:TestHuntDone")
      EVENTS = ["TestHuntDone"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None, event=None):
        _ = event
        # Store the results for later inspection.
        received_events.append(message)

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt(
        "BrokenSampleHunt", notification_event="TestHuntDone", token=self.token)
    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, check_flow_errors=False,
                            token=self.token)

    self.assertEqual(len(received_events), 5)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
