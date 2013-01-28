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


"""Tests for the standard hunts."""



import time


from grr.lib import aff4
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class SampleHuntMock(object):

  def __init__(self):
    self.responses = 0
    self.data = "Hello World!"

  def StatFile(self, args):
    return self._StatFile(args)

  def _StatFile(self, args):
    req = rdfvalue.ListDirRequest()
    req.ParseFromString(args)
    response = rdfvalue.StatEntry(
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
      raise IOError("File does not exist")

    return [response]

  def TransferBuffer(self, args):

    response = rdfvalue.BufferReference()
    response.ParseFromString(args)

    response.data = self.data
    response.length = len(self.data)
    return [response]


class StandardHuntTest(test_lib.FlowTestsBaseclass):
  """Tests the Hunt."""

  def setUp(self):
    super(StandardHuntTest, self).setUp()
    # Set up 10 clients.
    self.client_ids = self.SetupClients(10)

  def tearDown(self):
    super(StandardHuntTest, self).tearDown()
    self.DeleteClients(10)

  def testGenericHuntWithSendRepliesSetToFalse(self):
    """This tests running the hunt on some clients."""

    hunt = hunts.GenericHunt(
        flow_name="GetFile",
        args=rdfvalue.RDFProtoDict(
            pathspec=rdfvalue.RDFPathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.RDFPathSpec.Enum("OS"),
                )
            ),
        collect_replies=False,
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
    client_mock = SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids,
                            check_flow_errors=False, token=self.token)

    # Stop the hunt now.
    hunt.Stop()

    hunt_obj = hunt.GetAFF4Object(token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 10)
    self.assertEqual(len(set(finished)), 10)
    self.assertEqual(len(set(errors)), 5)

    # We shouldn't receive any entries as send_replies is set to False.
    collection = aff4.FACTORY.Open(hunt.collection.urn, mode="r",
                                   token=self.token)
    self.assertEqual(len(list(collection)), 0)

  def testGenericHunt(self):
    """This tests running the hunt on some clients."""

    hunt = hunts.GenericHunt(flow_name="GetFile",
                             args=rdfvalue.RDFProtoDict(
                                 pathspec=rdfvalue.RDFPathSpec(
                                     path="/tmp/evil.txt",
                                     pathtype=rdfvalue.RDFPathSpec.Enum("OS")),
                                 ),
                             collect_replies=True,
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
    client_mock = SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Stop the hunt now.
    hunt.Stop()

    hunt_obj = hunt.GetAFF4Object(token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 10)
    self.assertEqual(len(set(finished)), 10)
    self.assertEqual(len(set(errors)), 5)

    collection = aff4.FACTORY.Open(hunt.collection.urn, mode="r",
                                   token=self.token)

    # We should receive stat entries.
    i = 0
    for i, x in enumerate(collection):
      self.assertEqual(x.payload.__class__, rdfvalue.StatEntry)
      self.assertTrue(x.payload.aff4path.endswith("/fs/os/tmp/evil.txt"))

    self.assertEqual(i, 4)

  def testHuntTermination(self):
    """This tests that hunts with a client limit terminate correctly."""

    old_time = time.time
    try:
      time.time = lambda: 1000

      args = rdfvalue.RDFProtoDict(
          pathspec=rdfvalue.RDFPathSpec(
              path="/tmp/evil.txt",
              pathtype=rdfvalue.RDFPathSpec.Enum("OS"))
          )

      hunt = hunts.GenericHunt(flow_name="GetFile", args=args,
                               collect_replies=False, client_limit=5,
                               expiry_time=1000, token=self.token)

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
      client_mock = SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids,
                              check_flow_errors=False, token=self.token)

      hunt_obj = hunt.GetAFF4Object(token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 5)
      self.assertEqual(len(set(finished)), 5)
      self.assertEqual(len(set(errors)), 3)

      # Now advance the time such that the hunt expires.
      time.time = lambda: 5000

      # Erase the last foreman check time for one client.
      client = aff4.FACTORY.Open("aff4:/%s" % self.client_ids[0], mode="rw",
                                 token=self.token)
      client.Set(client.Schema.LAST_FOREMAN_TIME(0))
      client.Close()

      # Let one client check in, this expires the rules and terminates the hunt.
      foreman.AssignTasksToClient(self.client_ids[0])

      # Now emulate a worker.
      worker = test_lib.MockWorker(queue_name="W", token=self.token)
      while worker.Next():
        pass
      worker.pool.Join()

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, token=self.token)
      flow_obj = hunt_obj.GetFlowObj()
      self.assertEqual(flow_obj.flow_pb.state, rdfvalue.Flow.Enum("TERMINATED"))

    finally:
      time.time = old_time
