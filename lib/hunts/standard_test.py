#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the standard hunts."""



import math
import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class StandardHuntTest(test_lib.FlowTestsBaseclass):
  """Tests the Hunt."""

  def setUp(self):
    super(StandardHuntTest, self).setUp()
    # Set up 10 clients.
    self.client_ids = self.SetupClients(10)

  def tearDown(self):
    super(StandardHuntTest, self).tearDown()
    self.DeleteClients(10)

  def testGenericHuntWithoutOutputPlugins(self):
    """This tests running the hunt on some clients."""
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=[],
        token=self.token) as hunt:
      hunt.Run()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # client..
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in self.client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids,
                            check_flow_errors=False, token=self.token)

    # Stop the hunt now.
    with aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES, mode="rw",
                           token=self.token) as hunt_obj:
      hunt_obj.Stop()

    hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                 token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 10)
    self.assertEqual(len(set(finished)), 10)
    self.assertEqual(len(set(errors)), 5)

    # We shouldn't receive any entries as no output plugin was specified.
    self.assertRaises(IOError, aff4.FACTORY.Open,
                      hunt.session_id.Add("Results"),
                      "RDFValueCollection", "r", False, self.token)

  def testGenericHunt(self):
    """This tests running the hunt on some clients."""
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(pathspec=rdfvalue.PathSpec(
            path="/tmp/evil.txt", pathtype=rdfvalue.PathSpec.PathType.OS)),
        regex_rules=[
            rdfvalue.ForemanAttributeRegex(attribute_name="GRR client",
                                           attribute_regex="GRR"),
            ],
        token=self.token) as hunt:
      hunt.Run()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in self.client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Stop the hunt now.
    with aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES, mode="rw",
                           token=self.token) as hunt_obj:
      hunt_obj.Stop()

    with aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                           token=self.token) as hunt_obj:
      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 10)
      self.assertEqual(len(set(finished)), 10)
      self.assertEqual(len(set(errors)), 5)

      collection = aff4.FACTORY.Open(
          hunt_obj.state.context.output_plugins[0].collection.urn,
          mode="r", token=self.token)

      # We should receive stat entries.
      i = 0
      for i, x in enumerate(collection):
        self.assertEqual(x.payload.__class__, rdfvalue.StatEntry)
        self.assertEqual(x.payload.aff4path.Split(2)[-1], "fs/os/tmp/evil.txt")

      self.assertEqual(i, 4)

  def _AppendFlowRequest(self, flows, client_id, file_id):
    flows.Append(
        client_ids=["C.1%015d" % client_id],
        runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil%s.txt" % file_id,
                pathtype=rdfvalue.PathSpec.PathType.OS),
            )
        )

  def RunVariableGenericHunt(self):
    args = rdfvalue.VariableGenericHuntArgs()
    self._AppendFlowRequest(args.flows, 1, 1)
    self._AppendFlowRequest(args.flows, 2, 2)
    self._AppendFlowRequest(args.flows, 2, 3)

    with hunts.GRRHunt.StartHunt(hunt_name="VariableGenericHunt",
                                 args=args, token=self.token) as hunt:
      hunt.Run()
      hunt.ManuallyScheduleClients()

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock(failrate=100)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Stop the hunt now.
    with aff4.FACTORY.Open(hunt.session_id, mode="rw",
                           token=self.token) as hunt:
      hunt.Stop()

    return hunt

  def testVariableGenericHunt(self):
    """This tests running the hunt on some clients."""
    hunt = self.RunVariableGenericHunt()

    hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                 token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 2)
    self.assertEqual(len(set(finished)), 2)
    self.assertEqual(len(set(errors)), 0)

  def testHuntTermination(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.Stubber(time, "time", lambda: 1000):
      with hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=rdfvalue.GetFileArgs(
              pathspec=rdfvalue.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdfvalue.PathSpec.PathType.OS)
              ),
          regex_rules=[rdfvalue.ForemanAttributeRegex(
              attribute_name="GRR client",
              attribute_regex="GRR")],
          client_limit=5,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids,
                              check_flow_errors=False, token=self.token)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 5)
      self.assertEqual(len(set(finished)), 5)
      self.assertEqual(len(set(errors)), 2)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      # Hunts are automatically paused when they reach the client limit.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

  def testHuntExpiration(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.Stubber(time, "time", lambda: 1000):
      with hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=rdfvalue.GetFileArgs(
              pathspec=rdfvalue.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdfvalue.PathSpec.PathType.OS)
              ),
          regex_rules=[rdfvalue.ForemanAttributeRegex(
              attribute_name="GRR client",
              attribute_regex="GRR")],
          client_limit=5,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STARTED")

      # Now advance the time such that the hunt expires.
      time.time = lambda: 5000

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids,
                              check_flow_errors=False, token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      # No client should be processed since the hunt is expired.
      self.assertEqual(len(set(started)), 0)
      self.assertEqual(len(set(finished)), 0)
      self.assertEqual(len(set(errors)), 0)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      # Hunts are automatically stopped when they expire.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STOPPED")

  def testHuntModificationWorksCorrectly(self):
    """This tests running the hunt on some clients."""
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS),
            ),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        client_limit=1,
        token=self.token) as hunt:
      hunt.Run()

    # Forget about hunt object, we'll use AFF4 for everything.
    hunt_session_id = hunt.session_id
    hunt = None

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # client..
    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token) as foreman:
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Re-open the hunt to get fresh data.
    hunt_obj = aff4.FACTORY.Open(hunt_session_id, age=aff4.ALL_TIMES,
                                 ignore_cache=True, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)

    # There should be only one client, due to the limit
    self.assertEqual(len(set(started)), 1)

    # Check the hunt is paused.
    self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

    with aff4.FACTORY.Open(
        hunt_session_id, mode="rw", token=self.token) as hunt_obj:
      with hunt_obj.GetRunner() as runner:
        runner.args.client_limit = 10
        runner.Start()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients.
    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token) as foreman:
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt_session_id, age=aff4.ALL_TIMES,
                                 token=self.token)
    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    # There should be only one client, due to the limit
    self.assertEqual(len(set(started)), 10)

  def testResourceUsageStats(self):
    client_ids = self.SetupClients(10)

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(
            flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=[],
        token=self.token) as hunt:
      hunt.Run()

    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token) as foreman:
      for client_id in client_ids:
        foreman.AssignTasksToClient(client_id)

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt = aff4.FACTORY.Open(hunt.urn, aff4_type="GenericHunt",
                             token=self.token)

    # This is called once for each state method. Each flow above runs the
    # Start and the StoreResults methods.
    usage_stats = hunt.state.context.usage_stats
    self.assertEqual(usage_stats.user_cpu_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.user_cpu_stats.mean -
                              5.5) < 1e-7)
    self.assertTrue(math.fabs(usage_stats.user_cpu_stats.std -
                              2.8722813) < 1e-7)

    self.assertEqual(usage_stats.system_cpu_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.system_cpu_stats.mean -
                              11) < 1e-7)
    self.assertTrue(math.fabs(usage_stats.system_cpu_stats.std -
                              5.7445626) < 1e-7)

    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.network_bytes_sent_stats.mean -
                              16.5) < 1e-7)
    self.assertTrue(math.fabs(usage_stats.network_bytes_sent_stats.std -
                              8.61684396) < 1e-7)

    # NOTE: Not checking histograms here. RunningStatsTest tests that mean,
    # standard deviation and histograms are calculated correctly. Therefore
    # if mean/stdev values are correct histograms should be ok as well.

    self.assertEqual(len(usage_stats.worst_performers), 10)

    prev = usage_stats.worst_performers[0]
    for p in usage_stats.worst_performers[1:]:
      self.assertTrue(prev.cpu_usage.user_cpu_time +
                      prev.cpu_usage.system_cpu_time >
                      p.cpu_usage.user_cpu_time +
                      p.cpu_usage.system_cpu_time)
      prev = p

  class MBRHuntMock(object):

    def ReadBuffer(self, args):

      response = rdfvalue.BufferReference(args)
      response.data = "\x01" * response.length

      return [response]

  def testMBRHunt(self):
    with hunts.GRRHunt.StartHunt(hunt_name="MBRHunt", length=3333,
                                 client_limit=1,
                                 token=self.token) as hunt:
      hunt.Run()
      hunt.StartClient(hunt.session_id, self.client_id)

    # Run the hunt.
    client_mock = self.MBRHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    mbr = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("mbr"),
                            token=self.token)
    data = mbr.read(100000)
    self.assertEqual(len(data), 3333)


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
