#!/usr/bin/env python
"""This implements the auditing system.

How does it work?

Noteworthy events within the GRR system (such as approval granting, flow
execution etc) generate events to notify listeners about the event.

The audit system consists of a group of event listeners which receive these
events and act upon them. The current implementation simply maintains the
aff4:/statistics/ area of the AFF4 namespace, where statistics of user
activities are maintained.
"""


from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import jobs_pb2


class AuditEvent(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.AuditEvent

  def __init__(self, initializer=None, age=None, **kwargs):

    super(AuditEvent, self).__init__(initializer=initializer, age=age,
                                     **kwargs)
    if not self.id:
      self.id = utils.PRNG.GetULong()
    if not self.timestamp:
      self.timestamp = rdfvalue.RDFDatetime().Now()


class AuditEventListener(flow.EventListener):
  """Receive the audit events."""
  well_known_session_id = rdfvalue.SessionID("aff4:/audit/W:listener")
  EVENTS = ["Audit"]

  @flow.EventHandler(auth_required=False)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    with aff4.FACTORY.Create("aff4:/audit/log", "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(event)
