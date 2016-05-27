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
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collects

AUDIT_EVENT = "Audit"


class AuditEventListener(flow.EventListener):
  """Receive the audit events."""
  well_known_session_id = rdfvalue.SessionID(base="aff4:/audit",
                                             queue=queues.FLOWS,
                                             flow_name="listener")
  EVENTS = [AUDIT_EVENT]

  @flow.EventHandler(auth_required=False)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    with aff4.FACTORY.Create(aff4.CurrentAuditLog(),
                             collects.PackedVersionedCollection,
                             mode="w",
                             token=self.token) as fd:
      fd.Add(event)
