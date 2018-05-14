#!/usr/bin/env python
"""This implements the auditing system.

How does it work?

Noteworthy events within the GRR system (such as approval granting, flow
execution etc) generate events to notify listeners about the event.

The audit system consists of a group of event listeners which receive these
events and act upon them.
"""

from grr.lib.rdfvalues import events as rdf_events
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import events
from grr.server.grr_response_server import sequential_collection

AUDIT_EVENT = "Audit"


class AuditEventCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_events.AuditEvent


def AllAuditLogs(token=None):
  # TODO(amoser): This is not great, we should store this differently.
  for log in aff4.FACTORY.Open("aff4:/audit/logs", token=token).ListChildren():
    yield AuditEventCollection(log)


def AuditLogsForTimespan(start_time, end_time, token=None):
  # TODO(amoser): This is not great, we should store this differently.
  for log in aff4.FACTORY.Open(
      "aff4:/audit/logs", token=token).ListChildren(age=(start_time, end_time)):
    yield AuditEventCollection(log)


class AuditEventListener(events.EventListener):
  """Receive the audit events."""

  EVENTS = [AUDIT_EVENT]

  created_logs = set()

  def EnsureLogIsIndexed(self, log_urn, token=None):
    if log_urn not in self.created_logs:
      # Just write any type to the aff4 space so we can determine
      # which audit logs exist easily.
      aff4.FACTORY.Create(
          log_urn, aff4.AFF4Volume, mode="w", token=token).Close()
      self.created_logs.add(log_urn)
    return log_urn

  def ProcessMessages(self, msgs=None, token=None):
    log_urn = aff4.CurrentAuditLog()
    self.EnsureLogIsIndexed(log_urn, token=token)
    with data_store.DB.GetMutationPool() as pool:
      for msg in msgs:
        AuditEventCollection.StaticAdd(log_urn, msg, mutation_pool=pool)
