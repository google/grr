#!/usr/bin/env python
"""This implements the auditing system.

How does it work?

Noteworthy events within the GRR system (such as approval granting, flow
execution etc) generate events to notify listeners about the event.

The audit system consists of a group of event listeners which receive these
events and act upon them.
"""

from grr.lib import queues
from grr.lib import rdfvalue
from grr.server import aff4
from grr.server import data_store
from grr.server import events
from grr.server import flow
from grr.server import sequential_collection

AUDIT_EVENT = "Audit"


class AuditEventCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = events.AuditEvent


def AllAuditLogs(token=None):
  # TODO(amoser): This is not great, we should store this differently.
  for log in aff4.FACTORY.Open("aff4:/audit/logs", token=token).ListChildren():
    yield AuditEventCollection(log)


def AuditLogsForTimespan(start_time, end_time, token=None):
  # TODO(amoser): This is not great, we should store this differently.
  for log in aff4.FACTORY.Open(
      "aff4:/audit/logs", token=token).ListChildren(age=(start_time, end_time)):
    yield AuditEventCollection(log)


class AuditEventListener(flow.EventListener):
  """Receive the audit events."""
  well_known_session_id = rdfvalue.SessionID(
      base="aff4:/audit", queue=queues.FLOWS, flow_name="listener")
  EVENTS = [AUDIT_EVENT]

  created_logs = set()

  def EnsureLogIsIndexed(self, log_urn):
    if log_urn not in self.created_logs:
      # Just write any type to the aff4 space so we can determine
      # which audit logs exist easily.
      aff4.FACTORY.Create(
          log_urn, aff4.AFF4Volume, mode="w", token=self.token).Close()
      self.created_logs.add(log_urn)
    return log_urn

  @flow.EventHandler(auth_required=False)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    log_urn = aff4.CurrentAuditLog()
    self.EnsureLogIsIndexed(log_urn)
    with data_store.DB.GetMutationPool() as pool:
      AuditEventCollection.StaticAdd(log_urn, event, mutation_pool=pool)
