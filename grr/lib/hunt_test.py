#!/usr/bin/env python
"""Tests for the hunt."""




import logging

from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow

# These imports populate the GRRHunt registry.
from grr.lib import hunts
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.server import foreman as rdf_foreman


class TestHuntListener(flow.EventListener):
  well_known_session_id = rdfvalue.SessionID(flow_name="TestHuntDone")
  EVENTS = ["TestHuntDone"]

  received_events = []

  @flow.EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    _ = event
    # Store the results for later inspection.
    self.__class__.received_events.append(message)


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


class DummyHunt(hunts.GRRHunt):
  """Dummy hunt that stores client ids in a class variable."""

  client_ids = []

  @flow.StateHandler()
  def RunClient(self, responses):
    for client_id in responses:
      DummyHunt.client_ids.append(client_id)
      self.MarkClientDone(client_id)


class HuntTest(test_lib.FlowTestsBaseclass):
  """Tests the Hunt."""

  def setUp(self):
    super(HuntTest, self).setUp()

    with test_lib.FakeTime(0):
      # Clean up the foreman to remove any rules.
      with aff4.FACTORY.Open("aff4:/foreman",
                             mode="rw",
                             token=self.token) as foreman:
        foreman.Set(foreman.Schema.RULES())

    DummyHunt.client_ids = []

  def testRuleAdding(self):
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)
    # Make sure there are no rules yet in the foreman.
    self.assertEqual(len(rules), 0)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="HUNT")), rdf_foreman.ForemanClientRule(
                    rule_type=rdf_foreman.ForemanClientRule.Type.INTEGER,
                    integer=rdf_foreman.ForemanIntegerClientRule(
                        attribute_name="Clock",
                        operator=rdf_foreman.ForemanIntegerClientRule.Operator.
                        GREATER_THAN,
                        value=1336650631137737))
    ])

    hunt = hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                   client_rule_set=client_rule_set,
                                   client_rate=0,
                                   token=self.token)

    # Push the rules to the foreman.
    with hunt:
      hunt.GetRunner().Start()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)

    # Make sure they were written correctly.
    self.assertEqual(len(rules), 1)
    rule = rules[0]

    self.assertEqual(rule.client_rule_set, client_rule_set)

    self.assertEqual(len(rule.actions), 1)
    self.assertEqual(rule.actions[0].hunt_name, "SampleHunt")

    # Running a second time should not change the rules any more.
    with hunt:
      hunt.GetRunner().Start()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)

    # Still just one rule.
    self.assertEqual(len(rules), 1)

  def AddForemanRules(self, to_add):
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES, default=foreman.Schema.RULES())
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
    now = rdfvalue.RDFDatetime().Now()
    expires = rdfvalue.Duration("1h").Expiry()
    # Add some rules.
    rules = [rdf_foreman.ForemanRule(created=now,
                                     expires=expires,
                                     description="Test rule1"),
             rdf_foreman.ForemanRule(created=now,
                                     expires=expires,
                                     description="Test rule2")]
    self.AddForemanRules(rules)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="HUNT")), rdf_foreman.ForemanClientRule(
                    rule_type=rdf_foreman.ForemanClientRule.Type.INTEGER,
                    integer=rdf_foreman.ForemanIntegerClientRule(
                        attribute_name="Clock",
                        operator=rdf_foreman.ForemanIntegerClientRule.Operator.
                        GREATER_THAN,
                        value=1336650631137737))
    ])

    hunt = hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                   client_rule_set=client_rule_set,
                                   client_rate=0,
                                   token=self.token)

    with hunt:
      runner = hunt.GetRunner()
      runner.Start()

      # Add some more rules.
      rules = [rdf_foreman.ForemanRule(created=now,
                                       expires=expires,
                                       description="Test rule3"),
               rdf_foreman.ForemanRule(created=now,
                                       expires=expires,
                                       description="Test rule4")]
      self.AddForemanRules(rules)

      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      rules = foreman.Get(foreman.Schema.RULES)
      self.assertEqual(len(rules), 5)

      # It should be running.
      self.assertTrue(runner.IsHuntStarted())

      # Now we stop the hunt.
      hunt.Stop()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)
    # The rule for this hunt should be deleted but the rest should be there.
    self.assertEqual(len(rules), 4)

    # And the hunt should report no outstanding requests any more.
    with hunt:
      self.assertFalse(hunt.GetRunner().IsHuntStarted())

  def testInvalidRules(self):
    """Tests the behavior when a wrong attribute name is passed in a rule."""

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="no such attribute",
                attribute_regex="HUNT"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="BrokenSampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 token=self.token) as hunt:

      runner = hunt.GetRunner()
      self.assertRaises(ValueError, runner.Start)

  def Callback(self, hunt_id, client_id):
    self.called.append((hunt_id, client_id))

  def testCallback(self, client_limit=None):
    """Checks that the foreman uses the callback specified in the action."""

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_limit=client_limit,
                                 client_rate=0,
                                 token=self.token) as hunt:

      hunt.GetRunner().Start()

    # Create a client that matches our regex.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    info = client.Schema.CLIENT_INFO()
    info.client_name = "GRR Monitor"
    client.Set(client.Schema.CLIENT_INFO, info)
    client.Close()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    with utils.Stubber(hunts.SampleHunt, "StartClients", self.Callback):
      self.called = []

      foreman.AssignTasksToClient(client.urn)

      self.assertEqual(len(self.called), 1)
      self.assertEqual(self.called[0][1], [client.urn])

  def testStartClients(self):
    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 client_rate=0,
                                 token=self.token) as hunt:

      hunt.GetRunner().Start()

    flows = list(aff4.FACTORY.Open(
        self.client_id.Add("flows"),
        token=self.token).ListChildren())

    self.assertEqual(flows, [])

    hunts.GRRHunt.StartClients(hunt.session_id, [self.client_id])

    test_lib.TestHuntHelper(None, [self.client_id], False, self.token)

    flows = list(aff4.FACTORY.Open(
        self.client_id.Add("flows"),
        token=self.token).ListChildren())

    # One flow should have been started.
    self.assertEqual(len(flows), 1)
    self.assertIn(hunt.session_id.Basename(), str(flows[0]))

  def testCallbackWithLimit(self):

    self.assertRaises(RuntimeError, self.testCallback, 2000)

    self.testCallback(100)

  def testProcessing(self):
    """This tests running the hunt on some clients."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 token=self.token) as hunt:

      hunt.GetRunner().Start()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                 mode="r",
                                 age=aff4.ALL_TIMES,
                                 aff4_type=hunts.SampleHunt,
                                 token=self.token)

    started, finished, _ = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 10)
    self.assertEqual(finished, 10)

  def testHangingClients(self):
    """This tests if the hunt completes when some clients hang or raise."""
    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 token=self.token) as hunt:

      hunt.GetRunner().Start()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    client_mock = test_lib.SampleHuntMock()
    # Just pass 8 clients to run, the other two went offline.
    test_lib.TestHuntHelper(client_mock, client_ids[1:9], False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                 mode="rw",
                                 age=aff4.ALL_TIMES,
                                 token=self.token)

    started, finished, _ = hunt_obj.GetClientsCounts()
    # We started the hunt on 10 clients.
    self.assertEqual(started, 10)
    # But only 8 should have finished.
    self.assertEqual(finished, 8)

  def testPausingAndRestartingDoesNotStartHuntTwiceOnTheSameClient(self):
    """This tests if the hunt completes when some clients hang or raise."""
    client_ids = self.SetupClients(10)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 token=self.token) as hunt:

      hunt.GetRunner().Start()

      hunt_id = hunt.urn

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      num_tasks = foreman.AssignTasksToClient(client_id)
      self.assertEqual(num_tasks, 1)

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    # Pausing and running hunt: this leads to the fresh rules being written
    # to Foreman.RULES.
    with aff4.FACTORY.Open(hunt_id, mode="rw", token=self.token) as hunt:
      runner = hunt.GetRunner()
      runner.Pause()
      runner.Start()

    # Recreating the foreman so that it updates list of rules.
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      num_tasks = foreman.AssignTasksToClient(client_id)
      # No tasks should be assigned as this hunt ran on all the clients
      # before.
      self.assertEqual(num_tasks, 0)

  def testClientLimit(self):
    """This tests that we can limit hunts to a number of clients."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="SampleHunt",
                                 client_limit=5,
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 token=self.token) as hunt:
      hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt.urn,
                                 mode="rw",
                                 age=aff4.ALL_TIMES,
                                 token=self.token)

    started, finished, _ = hunt_obj.GetClientsCounts()
    # We limited here to 5 clients.
    self.assertEqual(started, 5)
    self.assertEqual(finished, 5)

  def testBrokenHunt(self):
    """This tests the behavior when a hunt raises an exception."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="BrokenSampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 token=self.token) as hunt:

      hunt.GetRunner().Start()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                 mode="rw",
                                 age=aff4.ALL_TIMES,
                                 token=self.token)

    started, finished, errors = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 10)
    # There should be errors for the five clients where the hunt raised.
    self.assertEqual(errors, 5)
    # All of the clients that have the file should still finish eventually.
    self.assertEqual(finished, 5)

  def testHuntNotifications(self):
    """This tests the Hunt notification event."""
    TestHuntListener.received_events = []

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="BrokenSampleHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=0,
                                 notification_event="TestHuntDone",
                                 token=self.token) as hunt:

      hunt.GetRunner().Start()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock,
                            client_ids,
                            check_flow_errors=False,
                            token=self.token)

    self.assertEqual(len(TestHuntListener.received_events), 5)

  def _RunRateLimitedHunt(self, client_ids, start_time):
    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="DummyHunt",
                                 client_rule_set=client_rule_set,
                                 client_rate=1,
                                 token=self.token) as hunt:
      hunt.Run()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    self.assertEqual(len(DummyHunt.client_ids), 0)

    # Run the hunt.
    worker_mock = test_lib.MockWorker(check_flow_errors=True,
                                      queues=queues.HUNTS,
                                      token=self.token)

    # One client is scheduled in the first minute.
    with test_lib.FakeTime(start_time + 2):
      worker_mock.Simulate()
    self.assertEqual(len(DummyHunt.client_ids), 1)

    # No further clients will be scheduled until the end of the first minute.
    with test_lib.FakeTime(start_time + 59):
      worker_mock.Simulate()
    self.assertEqual(len(DummyHunt.client_ids), 1)

    return worker_mock, hunt.urn

  def testHuntClientRate(self):
    """Check that clients are scheduled slowly by the hunt."""
    start_time = 10

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    with test_lib.FakeTime(start_time):
      worker_mock, _ = self._RunRateLimitedHunt(client_ids, start_time)
      # One client will be processed every minute.
      for i in range(len(client_ids)):
        with test_lib.FakeTime(start_time + 1 + 60 * i):
          worker_mock.Simulate()
          self.assertEqual(len(DummyHunt.client_ids), i + 1)

  def testHuntClientRateWithPause(self):
    """Check that clients are scheduled only if the hunt is running."""
    start_time = 10

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    with test_lib.FakeTime(start_time):
      worker_mock, hunt_urn = self._RunRateLimitedHunt(client_ids, start_time)

      # Now pause the hunt
      with aff4.FACTORY.Open(hunt_urn,
                             age=aff4.ALL_TIMES,
                             mode="rw",
                             token=self.token) as hunt_obj:
        hunt_obj.Stop()

      # No more clients should be processed.
      for i in range(len(client_ids)):
        with test_lib.FakeTime(start_time + 1 + 60 * i):
          worker_mock.Simulate()
      self.assertEqual(len(DummyHunt.client_ids), 1)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
