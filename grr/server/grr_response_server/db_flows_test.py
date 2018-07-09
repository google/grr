#!/usr/bin/env python
"""Tests for the flow database api."""

from grr.core.grr_response_core.lib import rdfvalue
from grr.core.grr_response_core.lib import utils
from grr.core.grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.test_lib import test_lib


class DatabaseTestFlowMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of flows.
  """

  def testClientMessageStorage(self):

    client_id = self.InitializeClient()
    msg = rdf_flows.GrrMessage(queue=client_id, generate_task_id=True)

    self.db.WriteClientMessages([msg])

    read_msgs = self.db.ReadClientMessages(client_id)
    self.assertEqual(len(read_msgs), 1)
    self.assertEqual(msg, read_msgs[0])

    self.db.DeleteClientMessages([msg])
    read_msgs = self.db.ReadClientMessages(client_id)
    self.assertEqual(len(read_msgs), 0)

    # Extra delete should not raise.
    self.db.DeleteClientMessages([msg])

    # Deleting the same message multiple times is an error.
    with self.assertRaises(ValueError):
      self.db.DeleteClientMessages([msg, msg])

  def testClientMessageUpdate(self):
    client_id = self.InitializeClient()
    msg = rdf_flows.GrrMessage(queue=client_id, generate_task_id=True)

    ttl = msg.ttl
    self.assertGreater(ttl, 5)

    for _ in xrange(5):
      msg.ttl -= 1
      self.db.WriteClientMessages([msg])
      read_msgs = self.db.ReadClientMessages(client_id)
      self.assertEqual(len(read_msgs), 1)
      self.assertEqual(msg, read_msgs[0])

  def testClientMessageLeasing(self):

    client_id = self.InitializeClient()
    messages = [
        rdf_flows.GrrMessage(queue=client_id, generate_task_id=True)
        for _ in range(10)
    ]
    lease_time = rdfvalue.Duration("5m")

    self.db.WriteClientMessages(messages)

    t0 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000)
    with test_lib.FakeTime(t0):
      t0_expiry = t0 + lease_time
      leased = self.db.LeaseClientMessages(
          client_id, lease_time=lease_time, limit=5)

      self.assertEqual(len(leased), 5)

      for request in leased:
        self.assertEqual(request.leased_until, t0_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

    t1 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 100)
    with test_lib.FakeTime(t1):
      t1_expiry = t1 + lease_time
      leased = self.db.LeaseClientMessages(
          client_id, lease_time=lease_time, limit=5)

      self.assertEqual(len(leased), 5)

      for request in leased:
        self.assertEqual(request.leased_until, t1_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

      # Nothing left to lease.
      leased = self.db.LeaseClientMessages(
          client_id, lease_time=lease_time, limit=2)

      self.assertEqual(len(leased), 0)

    read = self.db.ReadClientMessages(client_id)

    self.assertEqual(len(read), 10)
    for r in read:
      self.assertEqual(r.leased_by, utils.ProcessIdString())

    self.assertEqual(len([r for r in read if r.leased_until == t0_expiry]), 5)
    self.assertEqual(len([r for r in read if r.leased_until == t1_expiry]), 5)

    # Half the leases expired.
    t2 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 350)
    with test_lib.FakeTime(t2):
      leased = self.db.LeaseClientMessages(client_id, lease_time=lease_time)

      self.assertEqual(len(leased), 5)

    # All of them expired.
    t3 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 10350)
    with test_lib.FakeTime(t3):
      leased = self.db.LeaseClientMessages(client_id, lease_time=lease_time)

      self.assertEqual(len(leased), 10)
