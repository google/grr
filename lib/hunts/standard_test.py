#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for the standard hunts."""



import math
import time


from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.hunts import output_plugins


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
    hunt = hunts.GRRHunt.StartHunt(
        "GenericHunt",
        flow_name="GetFile",
        args=rdfvalue.Dict(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        output_plugins=[],
        token=self.token)

    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
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
    hunt.Stop()
    hunt.Save()

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

  def testEmailPlugin(self):
    try:
      old_send_email = email_alerts.SendEmail

      self.email_messages = []

      def SendEmail(address, sender, title, message, **_):
        self.email_messages.append(dict(address=address, sender=sender,
                                        title=title, message=message))

      email_alerts.SendEmail = SendEmail

      hunt = hunts.GRRHunt.StartHunt(
          "GenericHunt",
          flow_name="GetFile",
          args=rdfvalue.Dict(
              pathspec=rdfvalue.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdfvalue.PathSpec.PathType.OS,
                  )
              ),
          output_plugins=[("CollectionPlugin", {}),
                          ("EmailPlugin", {"email": "notify@grrserver.com"})],
          token=self.token)

      email_plugin = hunt.GetOutputObjects(
          output_cls=output_plugins.EmailPlugin)[0]
      email_plugin.email_limit = 10
      hunt.Run()

      self.client_ids = self.SetupClients(40)
      for client_id in self.client_ids:
        hunt.StartClient(hunt.session_id, client_id)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Stop the hunt now.
      hunt.Stop()
      hunt.Save()

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 40)
      self.assertEqual(len(set(finished)), 40)
      self.assertEqual(len(set(errors)), 20)

      collection = aff4.FACTORY.Open(hunt.urn.Add("Results"),
                                     mode="r", token=self.token)

      self.assertEqual(len(collection), 20)

      # Due to the limit there should only by 10 messages.
      self.assertEqual(len(self.email_messages), 10)

      for msg in self.email_messages:
        self.assertEqual(msg["address"], "notify@grrserver.com")
        self.assertTrue(
            "%s produced a new result" % hunt_obj.session_id in msg["title"])
        self.assertTrue("fs/os/tmp/evil.txt" in msg["message"])

      self.assertTrue("sending of emails will be disabled now"
                      in self.email_messages[-1]["message"])

    finally:
      email_alerts.SendEmail = old_send_email

  def testGenericHunt(self):
    """This tests running the hunt on some clients."""
    hunt = hunts.GRRHunt.StartHunt(
        "GenericHunt",
        flow_name="GetFile",
        args=rdfvalue.Dict(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt", pathtype=rdfvalue.PathSpec.PathType.OS)),
        token=self.token)

    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
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
    hunt.Stop()
    hunt.Save()

    hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                 token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 10)
    self.assertEqual(len(set(finished)), 10)
    self.assertEqual(len(set(errors)), 5)

    collection = aff4.FACTORY.Open(hunt.state.output_objects[0].collection.urn,
                                   mode="r", token=self.token)

    # We should receive stat entries.
    i = 0
    for i, x in enumerate(collection):
      self.assertEqual(x.payload.__class__, rdfvalue.StatEntry)
      self.assertEqual(x.payload.aff4path.Split(2)[-1], "fs/os/tmp/evil.txt")

    self.assertEqual(i, 4)

  def RunVariableGenericHunt(self):
    flows = {
        rdfvalue.ClientURN("C.1%015d" % 1): [
            ("GetFile", dict(
                pathspec=rdfvalue.PathSpec(
                    path="/tmp/evil1.txt",
                    pathtype=rdfvalue.PathSpec.PathType.OS),
                ))],
        rdfvalue.ClientURN("C.1%015d" % 2): [
            ("GetFile", dict(
                pathspec=rdfvalue.PathSpec(
                    path="/tmp/evil2.txt",
                    pathtype=rdfvalue.PathSpec.PathType.OS),
                )),
            ("GetFile", dict(
                pathspec=rdfvalue.PathSpec(
                    path="/tmp/evil3.txt",
                    pathtype=rdfvalue.PathSpec.PathType.OS),
                ))],
        }

    hunt = hunts.GRRHunt.StartHunt("VariableGenericHunt", flows=flows,
                                   token=self.token)
    hunt.Run()
    hunt.ManuallyScheduleClients()

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock(failrate=100)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Stop the hunt now.
    hunt.Stop()
    hunt.Save()
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

  def testCollectionPlugin(self):
    """Tests the output collection."""
    hunt = self.RunVariableGenericHunt()

    collection = aff4.FACTORY.Open(
        hunt.state.output_objects[0].collection.urn,
        mode="r", token=self.token, age=aff4.ALL_TIMES)

    # We should receive stat entries.
    self.assertEqual(len(collection), 3)

    collection = sorted([x for x in collection],
                        key=lambda x: x.payload.aff4path)
    stats = [x.payload for x in collection]
    self.assertEqual(stats[0].__class__, rdfvalue.StatEntry)

    self.assertEqual(stats[0].aff4path.Split(2)[-1], "fs/os/tmp/evil1.txt")
    self.assertEqual(collection[0].source, "aff4:/C.1%015d" % 1)
    self.assertEqual(stats[1].__class__, rdfvalue.StatEntry)
    self.assertEqual(stats[1].aff4path.Split(2)[-1], "fs/os/tmp/evil2.txt")
    self.assertEqual(collection[1].source, "aff4:/C.1%015d" % 2)
    self.assertEqual(stats[2].__class__, rdfvalue.StatEntry)
    self.assertEqual(stats[2].aff4path.Split(2)[-1], "fs/os/tmp/evil3.txt")
    self.assertEqual(collection[2].source, "aff4:/C.1%015d" % 2)

  def testHuntTermination(self):
    """This tests that hunts with a client limit terminate correctly."""

    old_time = time.time
    try:
      time.time = lambda: 1000

      args = rdfvalue.Dict(
          pathspec=rdfvalue.PathSpec(
              path="/tmp/evil.txt",
              pathtype=rdfvalue.PathSpec.PathType.OS)
          )

      hunt = hunts.GRRHunt.StartHunt(
          "GenericHunt", flow_name="GetFile", args=args,
          client_limit=5,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token)

      regex_rule = rdfvalue.ForemanAttributeRegex(
          attribute_name="GRR client",
          attribute_regex="GRR")
      hunt.AddRule([regex_rule])
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

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 5)
      self.assertEqual(len(set(finished)), 5)
      self.assertEqual(len(set(errors)), 2)

      # Now advance the time such that the hunt expires.
      time.time = lambda: 5000

      # Erase the last foreman check time for one client.
      client = aff4.FACTORY.Open(self.client_ids[0], mode="rw",
                                 token=self.token)
      client.Set(client.Schema.LAST_FOREMAN_TIME(0))
      client.Close()

      # Let one client check in, this expires the rules and terminates the hunt.
      foreman.AssignTasksToClient(self.client_ids[0])

      # Now emulate a worker.
      worker = test_lib.MockWorker(token=self.token)
      while worker.Next():
        pass
      worker.pool.Join()

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)
      self.assertEqual(hunt_obj.state.context.state,
                       rdfvalue.Flow.State.TERMINATED)

    finally:
      time.time = old_time

  def testHuntModificationWorksCorrectly(self):
    """This tests running the hunt on some clients."""
    hunt = hunts.GRRHunt.StartHunt(
        "GenericHunt", flow_name="GetFile",
        args=rdfvalue.Dict(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS),
            ),
        client_limit=1,
        token=self.token)

    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    # Forget about hunt object, we'll use AFF4 for everything.
    hunt_session_id = hunt.session_id
    hunt = None

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # client..
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in self.client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt_session_id, age=aff4.ALL_TIMES,
                                 token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    # There should be only one client, due to the limit
    self.assertEqual(len(set(started)), 1)

    hunt_obj = aff4.FACTORY.Open(hunt_session_id, mode="rw", token=self.token)
    hunt_obj.state.context.client_limit = 10
    hunt_obj.Close()

    # Read the hunt we've just written.
    hunt = aff4.FACTORY.Open(hunt_session_id, mode="rw", token=self.token)
    hunt.Pause()
    hunt.Run()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # client..
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in self.client_ids:
      foreman.AssignTasksToClient(client_id)

    hunt_obj = aff4.FACTORY.Open(hunt_session_id, age=aff4.ALL_TIMES,
                                 token=self.token)
    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    # There should be only one client, due to the limit
    self.assertEqual(len(set(started)), 10)

  def testResourceUsageStats(self):
    client_ids = self.SetupClients(10)

    hunt = hunts.GRRHunt.StartHunt(
        "GenericHunt",
        flow_name="GetFile",
        args=rdfvalue.Dict(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        output_plugins=[],
        token=self.token)

    regex_rule = rdfvalue.ForemanAttributeRegex(
        attribute_name="GRR client",
        attribute_regex="GRR")
    hunt.AddRule([regex_rule])
    hunt.Run()

    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
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
    hunt = hunts.GRRHunt.StartHunt(
        "MBRHunt", length=3333,
        client_limit=1,
        token=self.token)
    hunt.Run()
    hunt.StartClient(hunt.session_id, self.client_id)

    # Run the hunt.
    client_mock = self.MBRHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    mbr = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add("mbr"),
                            token=self.token)
    data = mbr.read(100000)
    self.assertEqual(len(data), 3333)

  def testCollectFilesHunt(self):
    fbc = [(c, [rdfvalue.PathSpec(path="/dir/file%d" % i, pathtype=0)])
           for i, c in enumerate(self.client_ids[:5])]
    hunt = hunts.GRRHunt.StartHunt(
        "CollectFilesHunt",
        files_by_client=dict(fbc),
        token=self.token)
    hunt.Run()
    hunt.ManuallyScheduleClients()

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock(failrate=len(self.client_ids))
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    for i, c in enumerate(self.client_ids[:5]):
      fd = aff4.FACTORY.Open(rdfvalue.RDFURN(c).Add("fs/os/dir/file%d" % i),
                             token=self.token)
      self.assertTrue(isinstance(fd, aff4.HashImage))
