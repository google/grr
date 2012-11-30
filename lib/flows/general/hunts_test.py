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




from grr.lib import aff4
from grr.lib import test_lib
from grr.lib.flows.general import hunts
from grr.proto import jobs_pb2


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
      raise IOError("File does not exist")

    return [response]

  def TransferBuffer(self, args):

    response = jobs_pb2.BufferReadMessage()
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

    hunt = hunts.GenericHunt(flow_name="GetFile", args=dict(
        path="/tmp/evil.txt",
        pathspec=jobs_pb2.Path.OS,
        ), collect_replies=False, token=self.token)

    regex_rule = jobs_pb2.ForemanAttributeRegex(
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

    # We shouldn't receive any entries as send_replies is set to False.
    collection = aff4.FACTORY.Open(hunt.collection.urn, mode="r",
                                   token=self.token)
    self.assertEqual(len(list(collection)), 0)

  def testGenericHunt(self):
    """This tests running the hunt on some clients."""

    hunt = hunts.GenericHunt(flow_name="GetFile", args=dict(
        path="/tmp/evil.txt",
        pathspec=jobs_pb2.Path.OS,
        ), collect_replies=True, token=self.token)

    regex_rule = jobs_pb2.ForemanAttributeRegex(
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
      self.assertEqual(x.value.__class__, aff4.FACTORY.RDFValue("StatEntry"))
      self.assertTrue(x.value.data.aff4path.endswith("/fs/os/tmp/evil.txt"))

    self.assertEqual(i, 4)
