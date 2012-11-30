#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for the hunt."""



import time


from grr.client import conf
import logging

from grr.lib import aff4
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.flows.general import hunts
from grr.proto import jobs_pb2


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
      self.MarkClientBad(client_id)

    self.MarkClientDone(client_id)


class HuntTest(test_lib.FlowTestsBaseclass):
  """Tests the Hunt."""

  def testRuleAdding(self):

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    rules = foreman.Get(foreman.Schema.RULES)
    # Make sure there are no rules yet.
    self.assertEqual(rules, None)

    hunt = hunts.SampleHunt(token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="HUNT")
    int_rule = jobs_pb2.ForemanAttributeInteger(
        attribute_name="Clock",
        operator=jobs_pb2.ForemanAttributeInteger.GREATER_THAN,
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
                     jobs_pb2.ForemanAttributeInteger.GREATER_THAN)
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
    self.assertEqual(rules, None)
    now = int(time.time() * 1e6)
    expires = now + 3600
    # Add some rules.
    rules = [jobs_pb2.ForemanRule(created=now, expires=expires,
                                  description="Test rule1"),
             jobs_pb2.ForemanRule(created=now, expires=expires,
                                  description="Test rule2")]
    self.AddForemanRules(rules)

    hunt = hunts.SampleHunt(token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="HUNT")
    int_rule = jobs_pb2.ForemanAttributeInteger(
        attribute_name="Clock",
        operator=jobs_pb2.ForemanAttributeInteger.GREATER_THAN,
        value=1336650631137737)
    # Fire on either of the rules.
    hunt.AddRule([int_rule])
    hunt.AddRule([regex_rule])
    # Push the rules to the foreman.
    hunt.Run()

    # Add some more rules.
    rules = [jobs_pb2.ForemanRule(created=now, expires=expires,
                                  description="Test rule3"),
             jobs_pb2.ForemanRule(created=now, expires=expires,
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

    hunt = hunts.SampleHunt(token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="no such attribute",
        attribute_regex="HUNT")
    self.assertRaises(RuntimeError, hunt.AddRule, [regex_rule])

  def Callback(self, hunt_id, client_id, client_limit):
    self.called.append((hunt_id, client_id, client_limit))

  def testCallback(self, client_limit=None):
    """Checks that the foreman uses the callback specified in the action."""

    hunt = hunts.SampleHunt(client_limit=client_limit, token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)

    # Create a client that matches our regex.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    info = client.Schema.CLIENT_INFO()
    info.data.client_name = "GRR Monitor"
    client.Set(client.Schema.CLIENT_INFO, info)
    client.Close()

    old_start_client = hunts.SampleHunt.StartClient
    try:
      hunts.SampleHunt.StartClient = self.Callback
      self.called = []

      foreman.AssignTasksToClient(client.client_id)

      self.assertEqual(len(self.called), 1)
      self.assertEqual(self.called[0][1], client.client_id)

      # Clean up.
      foreman.Set(foreman.Schema.RULES())
      foreman.Close()
    finally:
      hunts.SampleHunt.StartClient = staticmethod(old_start_client)

  def testStartClient(self):
    hunt = hunts.SampleHunt(token=self.token)
    hunt.Run()

    client = aff4.FACTORY.Open("aff4:/%s" % self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    flows = client.GetValuesForAttribute(client.Schema.FLOW)

    self.assertEqual(flows, [])

    flow.GRRHunt.StartClient(hunt.session_id, self.client_id)

    test_lib.TestHuntHelper(None, [self.client_id], False, self.token)

    client = aff4.FACTORY.Open("aff4:/%s" % self.client_id, token=self.token,
                               age=aff4.ALL_TIMES)

    flows = client.GetValuesForAttribute(client.Schema.FLOW)

    # One flow should have been started.
    self.assertEqual(len(flows), 1)

  def testCallbackWithLimit(self):

    self.assertRaises(RuntimeError, self.testCallback, 2000)

    self.testCallback(100)

  class SampleHuntMock(object):

    def __init__(self):
      self.responses = 0
      self.data = "Hello World!"

    def StatFile(self, args):
      return self._StatFile(args)

    def _StatFile(self, args):
      req = jobs_pb2.ListDirRequest()
      req.ParseFromString(args)
      response = jobs_pb2.StatResponse(
          pathspec=req.pathspec,
          st_mode=33184,
          st_ino=1063090,
          st_dev=64512L,
          st_nlink=1,
          st_uid=139592,
          st_gid=5000,
          st_size=len(self.data),
          st_atime=1336469177,
          st_mtime=1336129892,
          st_ctime=1336129892)

      self.responses += 1

      # Every second client does not have this file.
      if self.responses % 2:
        return []

      return [response]

    def TransferBuffer(self, args):

      response = jobs_pb2.BufferReadMessage()
      response.ParseFromString(args)

      response.data = self.data
      response.length = len(self.data)
      return [response]

  class RaisingSampleHuntMock(SampleHuntMock):

    def StatFile(self, args):
      if self.responses == 3:
        self.responses += 1
        raise RuntimeError("This client fails.")

      return self._StatFile(args)

  def testProcessing(self):
    """This tests running the hunt on some clients."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.SampleHunt(token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = self.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    badness = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.BADNESS)

    self.assertEqual(len(set(started)), 10)
    self.assertEqual(len(set(finished)), 10)
    self.assertEqual(len(set(badness)), 5)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testHangingClients(self):
    """This tests if the hunt completes when some clients hang or raise."""
    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.SampleHunt(token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    client_mock = self.SampleHuntMock()
    # Just pass 8 clients to run, the other two went offline.
    test_lib.TestHuntHelper(client_mock, client_ids[1:9], False, self.token)

    hunt_obj = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    badness = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.BADNESS)

    # We started the hunt on 10 clients.
    self.assertEqual(len(set(started)), 10)
    # But only 8 should have finished.
    self.assertEqual(len(set(finished)), 8)
    # The client that raised should not show up here.
    self.assertEqual(len(set(badness)), 4)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testClientLimit(self):
    """This tests that we can limit hunts to a number of clients."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = hunts.SampleHunt(token=self.token, client_limit=5)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = self.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    badness = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.BADNESS)

    # We limited here to 5 clients.
    self.assertEqual(len(set(started)), 5)
    self.assertEqual(len(set(finished)), 5)
    self.assertEqual(len(set(badness)), 2)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testBrokenHunt(self):
    """This tests the behavior when a hunt raises an exception."""

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = BrokenSampleHunt(token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = self.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt.session_id, mode="rw",
                                 age=aff4.ALL_TIMES, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    badness = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.BADNESS)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 10)
    # There should be errors for the five clients where the hunt raised.
    self.assertEqual(len(set(errors)), 5)
    # All of the clients that have the file should still finish eventually.
    self.assertEqual(len(set(finished)), 5)
    self.assertEqual(len(set(badness)), 5)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def testHuntNotifications(self):
    """This tests the Hunt notification event."""

    received_events = []

    class Listener1(flow.EventListener):  # pylint:disable=W0612
      well_known_session_id = "W:TestHuntDone"
      EVENTS = ["TestHuntDone"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None):
        # Store the results for later inspection.
        received_events.append(message)

    # Set up 10 clients.
    client_ids = self.SetupClients(10)

    hunt = BrokenSampleHunt(notification_event="TestHuntDone",
                            token=self.token)
    regex_rule = jobs_pb2.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = self.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    self.assertEqual(len(received_events), 5)

    # Clean up.
    foreman.Set(foreman.Schema.RULES())
    foreman.Close()

    self.DeleteClients(10)

  def CheckTuple(self, tuple1, tuple2):
    (a, b) = tuple1
    (c, d) = tuple2

    self.assertAlmostEqual(a, c)
    self.assertAlmostEqual(b, d)

  def testResourceUsageStats(self):

    hunt = hunts.SampleHunt(token=self.token)
    hunt_obj = hunt.GetAFF4Object(mode="w", token=self.token)

    usages = [("client1", "flow1", 0.5, 0.5),
              ("client1", "flow2", 0.1, 0.5),
              ("client1", "flow3", 0.2, 0.5),
              ("client2", "flow4", 0.6, 0.5),
              ("client2", "flow5", 0.7, 0.5),
              ("client2", "flow6", 0.6, 0.5),
              ("client3", "flow7", 0.1, 0.5),
              ("client3", "flow8", 0.1, 0.5),
             ]

    # Add some client stats.
    for (client_id, session_id, user, sys) in usages:
      resource = hunt_obj.Schema.RESOURCES()
      resource.data.client_id = client_id
      resource.data.session_id = session_id
      resource.data.cpu_usage.user_cpu_time = user
      resource.data.cpu_usage.system_cpu_time = sys
      hunt_obj.AddAttribute(resource)

    hunt_obj.Close()

    hunt_obj = hunt.GetAFF4Object(mode="r", token=self.token)

    # Just for one client.
    res = hunt_obj.GetResourceUsage(client_id="client1", group_by_client=False)

    self.assertEqual(sorted(res.keys()), ["client1"])
    self.assertEqual(sorted(res["client1"].keys()),
                     ["flow1", "flow2", "flow3"])
    self.CheckTuple(res["client1"]["flow1"], (0.5, 0.5))
    self.CheckTuple(res["client1"]["flow2"], (0.1, 0.5))

    # Group by client_id.
    res = hunt_obj.GetResourceUsage(client_id="client1", group_by_client=True)

    self.assertEqual(sorted(res.keys()), ["client1"])
    self.CheckTuple(res["client1"], (0.8, 1.5))

    # Now for all clients.
    res = hunt_obj.GetResourceUsage(group_by_client=False)

    self.assertEqual(sorted(res.keys()), ["client1", "client2", "client3"])
    self.assertEqual(sorted(res["client1"].keys()),
                     ["flow1", "flow2", "flow3"])
    self.CheckTuple(res["client1"]["flow1"], (0.5, 0.5))
    self.CheckTuple(res["client1"]["flow2"], (0.1, 0.5))

    self.assertEqual(sorted(res["client2"].keys()),
                     ["flow4", "flow5", "flow6"])
    self.CheckTuple(res["client2"]["flow4"], (0.6, 0.5))
    self.CheckTuple(res["client2"]["flow5"], (0.7, 0.5))

    # Group by client_id.
    res = hunt_obj.GetResourceUsage(group_by_client=True)

    self.assertEqual(sorted(res.keys()), ["client1", "client2", "client3"])
    self.CheckTuple(res["client1"], (0.8, 1.5))
    self.CheckTuple(res["client2"], (1.9, 1.5))
    self.CheckTuple(res["client3"], (0.2, 1.0))


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  conf.StartMain(main)
