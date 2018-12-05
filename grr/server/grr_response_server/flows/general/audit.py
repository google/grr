#!/usr/bin/env python
"""This implements the auditing system.

How does it work?

Noteworthy events within the GRR system (such as approval granting, flow
execution etc) generate events to notify listeners about the event.

The audit system consists of a group of event listeners which receive these
events and act upon them.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import sequential_collection

AUDIT_EVENT = "Audit"

AUDIT_ROLLOVER_TIME = rdfvalue.Duration("2w")


class AuditEventCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_events.AuditEvent


def _AllLegacyAuditLogs(token=None):
  # TODO(amoser): This is not great, we should store this differently.
  for log in aff4.FACTORY.Open("aff4:/audit/logs", token=token).ListChildren():
    yield AuditEventCollection(log)


def LegacyAuditLogsForTimespan(start_time, end_time, token=None):
  # Bug: Returns logs with a file that fulfills start_time <= age <= end_time
  # This might return logs with age < start_time and skip some logs close to
  # end_time.

  # TODO(amoser): This is not great, we should store this differently.
  for log in aff4.FACTORY.Open(
      "aff4:/audit/logs", token=token).ListChildren(age=(start_time, end_time)):
    yield AuditEventCollection(log)


class AuditEventListener(events.EventListener):
  """Receive the audit events."""

  EVENTS = [AUDIT_EVENT]

  _created_logs = set()

  def _EnsureLogIsIndexedAff4(self, log_urn, token=None):
    if log_urn not in self._created_logs:
      # Just write any type to the aff4 space so we can determine
      # which audit logs exist easily.
      aff4.FACTORY.Create(
          log_urn, aff4.AFF4Volume, mode="w", token=token).Close()
      self._created_logs.add(log_urn)
    return log_urn

  def ProcessMessages(self, msgs=None, token=None):
    if not data_store.AFF4Enabled():
      return

    log_urn = _CurrentAuditLog()
    self._EnsureLogIsIndexedAff4(log_urn, token=token)
    with data_store.DB.GetMutationPool() as pool:
      for msg in msgs:
        AuditEventCollection.StaticAdd(log_urn, msg, mutation_pool=pool)


def _AuditLogBase():
  return aff4.ROOT_URN.Add("audit").Add("logs")


def _CurrentAuditLog():
  """Get the rdfurn of the current audit log."""
  now_sec = rdfvalue.RDFDatetime.Now().AsSecondsSinceEpoch()
  rollover_seconds = AUDIT_ROLLOVER_TIME.seconds
  # This gives us a filename that only changes every
  # AUDIT_ROLLOVER_TIfilME seconds, but is still a valid timestamp.
  current_log = (now_sec // rollover_seconds) * rollover_seconds
  return _AuditLogBase().Add(unicode(current_log))
