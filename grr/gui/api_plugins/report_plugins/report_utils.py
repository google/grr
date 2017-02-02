#!/usr/bin/env python
"""UI report handling helper utils."""
import itertools

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collects
from grr.lib.flows.general import audit


def GetAuditLogFiles(offset, now, token):
  """Get fds for audit log files created between now-offset and now.

  Args:
    offset: rdfvalue.Duration how far back to look in time
    now: rdfvalue.RDFDatetime for current time
    token: GRR access token
  Returns:
    Open handles to all audit logs collections that match the time range
  Raises:
    ValueError: if no matching logs were found
  """
  # Go back offset seconds, and another rollover period to make sure we get
  # all the events
  oldest_time = now - offset - rdfvalue.Duration(config_lib.CONFIG[
      "Logging.aff4_audit_log_rollover"])
  parentdir = aff4.FACTORY.Open("aff4:/audit/logs", token=token)
  logs = list(
      parentdir.ListChildren(age=(oldest_time.AsMicroSecondsFromEpoch(),
                                  now.AsMicroSecondsFromEpoch())))
  if not logs:
    raise ValueError("Couldn't find any logs in aff4:/audit/logs "
                     "between %s and %s" % (oldest_time, now))

  # TODO(user): Switch to AuditEventCollection fully.
  legacy_logs = aff4.FACTORY.MultiOpen(
      logs, aff4_type=collects.RDFValueCollection, token=token)
  audit_logs = aff4.FACTORY.MultiOpen(
      logs, aff4_type=audit.AuditEventCollection, token=token)
  return itertools.chain(legacy_logs, audit_logs)


def GetAuditLogEntries(offset, now, token):
  """Return all audit log entries between now-offset and now.

  Args:
    offset: rdfvalue.Duration how far back to look in time
    now: rdfvalue.RDFDatetime for current time
    token: GRR access token
  Yields:
    AuditEvents created during the time range
  """
  for fd in GetAuditLogFiles(offset, now, token):
    for event in fd.GenerateItems():
      if now - offset < event.timestamp < now:
        yield event
