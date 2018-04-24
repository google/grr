#!/usr/bin/env python
"""UI report handling helper utils."""

from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.flows.general import audit


def GetAuditLogEntries(offset, now, token):
  """Return all audit log entries between now-offset and now.

  Args:
    offset: rdfvalue.Duration how far back to look in time
    now: rdfvalue.RDFDatetime for current time
    token: GRR access token
  Raises:
    ValueError: No logs were found.
  Yields:
    AuditEvents created during the time range
  """
  start_time = now - offset - aff4.AUDIT_ROLLOVER_TIME

  logs_found = False
  for fd in audit.AuditLogsForTimespan(start_time, now, token):
    logs_found = True
    for event in fd.GenerateItems():
      if now - offset < event.timestamp < now:
        yield event

  if not logs_found:
    raise ValueError("Couldn't find any logs in aff4:/audit/logs "
                     "between %s and %s" % (start_time, now))
