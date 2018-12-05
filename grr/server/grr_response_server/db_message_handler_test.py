#!/usr/bin/env python
"""Tests for the message handler database api."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin
import queue

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils

from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class DatabaseTestHandlerMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of message handler requests.
  """

  def testMessageHandlerRequests(self):

    requests = [
        rdf_objects.MessageHandlerRequest(
            client_id="C.1000000000000000",
            handler_name="Testhandler",
            request_id=i * 100,
            request=rdfvalue.RDFInteger(i)) for i in range(5)
    ]

    self.db.WriteMessageHandlerRequests(requests)

    read = self.db.ReadMessageHandlerRequests()
    for r in read:
      self.assertTrue(r.timestamp)
      r.timestamp = None

    self.assertEqual(sorted(read, key=lambda req: req.request_id), requests)

    self.db.DeleteMessageHandlerRequests(requests[:2])
    self.db.DeleteMessageHandlerRequests(requests[4:5])

    read = self.db.ReadMessageHandlerRequests()
    self.assertLen(read, 2)
    read = sorted(read, key=lambda req: req.request_id)
    for r in read:
      r.timestamp = None

    self.assertEqual(requests[2:4], read)
    self.db.DeleteMessageHandlerRequests(read)

  def testMessageHandlerRequestLeasing(self):

    requests = [
        rdf_objects.MessageHandlerRequest(
            client_id="C.1000000000000000",
            handler_name="Testhandler",
            request_id=i * 100,
            request=rdfvalue.RDFInteger(i)) for i in range(10)
    ]
    lease_time = rdfvalue.Duration("5m")

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10000)):
      self.db.WriteMessageHandlerRequests(requests)

    leased = queue.Queue()
    self.db.RegisterMessageHandler(leased.put, lease_time, limit=5)

    got = []
    while len(got) < 10:
      try:
        l = leased.get(True, timeout=6)
      except queue.Empty:
        self.fail(
            "Timed out waiting for messages, expected 10, got %d" % len(got))
      self.assertLessEqual(len(l), 5)
      for m in l:
        self.assertEqual(m.leased_by, utils.ProcessIdString())
        self.assertGreater(m.leased_until, rdfvalue.RDFDatetime.Now())
        self.assertLess(m.timestamp, rdfvalue.RDFDatetime.Now())
        m.leased_by = None
        m.leased_until = None
        m.timestamp = None
      got += l
    self.db.DeleteMessageHandlerRequests(got)

    got.sort(key=lambda req: req.request_id)
    self.assertEqual(requests, got)
