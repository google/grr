#!/usr/bin/env python
"""Tests for the message handler database api."""

import queue

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import objects_pb2
from grr_response_server.databases import db_test_utils


class DatabaseTestHandlerMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of message handler requests.
  """

  def testMessageHandlerRequests(self):

    requests = []
    for i in range(5):
      emb = mig_protodict.ToProtoEmbeddedRDFValue(
          rdf_protodict.EmbeddedRDFValue(rdfvalue.RDFInteger(i))
      )
      requests.append(
          objects_pb2.MessageHandlerRequest(
              client_id="C.1000000000000000",
              handler_name="Testhandler",
              request_id=i * 100,
              request=emb,
          )
      )

    self.db.WriteMessageHandlerRequests(requests)

    read = self.db.ReadMessageHandlerRequests()
    for r in read:
      self.assertTrue(r.timestamp)
      r.ClearField("timestamp")

    self.assertCountEqual(read, requests)

    self.db.DeleteMessageHandlerRequests(requests[:2])
    self.db.DeleteMessageHandlerRequests(requests[4:5])

    read = self.db.ReadMessageHandlerRequests()
    self.assertLen(read, 2)
    for r in read:
      r.ClearField("timestamp")

    self.assertCountEqual(requests[2:4], read)
    self.db.DeleteMessageHandlerRequests(read)

  def testMessageHandlerRequestLeasing(self):

    requests = []
    for i in range(10):
      emb = mig_protodict.ToProtoEmbeddedRDFValue(
          rdf_protodict.EmbeddedRDFValue(rdfvalue.RDFInteger(i))
      )
      requests.append(
          objects_pb2.MessageHandlerRequest(
              client_id="C.1000000000000000",
              handler_name="Testhandler",
              request_id=i * 100,
              request=emb,
          )
      )

    lease_time = rdfvalue.Duration.From(5, rdfvalue.MINUTES)

    leased = queue.Queue()
    self.db.RegisterMessageHandler(leased.put, lease_time, limit=5)

    self.db.WriteMessageHandlerRequests(requests)

    got = []
    while len(got) < 10:
      try:
        l = leased.get(True, timeout=6)
      except queue.Empty:
        self.fail(
            "Timed out waiting for messages, expected 10, got %d" % len(got)
        )
      self.assertLessEqual(len(l), 5)
      for m in l:
        self.assertEqual(m.leased_by, utils.ProcessIdString())
        self.assertGreater(m.leased_until, rdfvalue.RDFDatetime.Now())
        self.assertLess(m.timestamp, rdfvalue.RDFDatetime.Now())
        m.ClearField("leased_by")
        m.ClearField("leased_until")
        m.ClearField("timestamp")
      got += l
    self.db.DeleteMessageHandlerRequests(got)

    got.sort(key=lambda req: req.request_id)
    self.assertEqual(requests, got)

  def testLargeRequestId(self):
    client_id = db_test_utils.InitializeClient(self.db)

    request = objects_pb2.MessageHandlerRequest()
    request.client_id = client_id
    request.request_id = 0x133713371337
    request.handler_name = "FooHandler"
    self.db.WriteMessageHandlerRequests([request])

    results = self.db.ReadMessageHandlerRequests()
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id)
    self.assertEqual(results[0].request_id, 0x133713371337)
    self.assertEqual(results[0].handler_name, "FooHandler")


# This file is a test library and thus does not require a __main__ block.
