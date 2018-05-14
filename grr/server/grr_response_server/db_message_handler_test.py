#!/usr/bin/env python
"""Tests for the message handler database api."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class DatabaseTestHandlerMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of client data.
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
    self.db.DeleteMessageHandlerRequests(requests[4])

    read = self.db.ReadMessageHandlerRequests()
    self.assertEqual(len(read), 2)
    read = sorted(read, key=lambda req: req.request_id)
    for r in read:
      r.timestamp = None

    self.assertEqual(requests[2:4], read)

  def testMessageHandlerRequestSorting(self):

    for i, ts in enumerate(
        [10000, 11000, 12000, 13000, 14000, 19000, 18000, 17000, 16000, 15000]):
      with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(ts)):
        request = rdf_objects.MessageHandlerRequest(
            client_id="C.1000000000000000",
            handler_name="Testhandler",
            request_id=i * 100,
            request=rdfvalue.RDFInteger(i))
        self.db.WriteMessageHandlerRequests([request])

    read = self.db.ReadMessageHandlerRequests()

    for i in range(1, len(read)):
      self.assertGreater(read[i - 1].timestamp, read[i].timestamp)

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

    t0 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000)
    with test_lib.FakeTime(t0):
      t0_expiry = t0 + lease_time
      leased = self.db.LeaseMessageHandlerRequests(
          lease_time=lease_time, limit=5)

      self.assertEqual(len(leased), 5)

      for request in leased:
        self.assertEqual(request.leased_until, t0_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

    t1 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 100)
    with test_lib.FakeTime(t1):
      t1_expiry = t1 + lease_time
      leased = self.db.LeaseMessageHandlerRequests(
          lease_time=lease_time, limit=5)

      self.assertEqual(len(leased), 5)

      for request in leased:
        self.assertEqual(request.leased_until, t1_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

      # Nothing left to lease.
      leased = self.db.LeaseMessageHandlerRequests(
          lease_time=lease_time, limit=2)

      self.assertEqual(len(leased), 0)

    read = self.db.ReadMessageHandlerRequests()

    self.assertEqual(len(read), 10)
    for r in read:
      self.assertEqual(r.leased_by, utils.ProcessIdString())

    self.assertEqual(len([r for r in read if r.leased_until == t0_expiry]), 5)
    self.assertEqual(len([r for r in read if r.leased_until == t1_expiry]), 5)

    # Half the leases expired.
    t2 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 350)
    with test_lib.FakeTime(t2):
      leased = self.db.LeaseMessageHandlerRequests(lease_time=lease_time)

      self.assertEqual(len(leased), 5)

    # All of them expired.
    t3 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 10350)
    with test_lib.FakeTime(t3):
      leased = self.db.LeaseMessageHandlerRequests(lease_time=lease_time)

      self.assertEqual(len(leased), 10)
