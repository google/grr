#!/usr/bin/env python
"""UI report handling helper utils."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server.flows.general import audit


def GetAuditLogEntries(offset, now, token):
  """Return all audit log entries between now-offset and now.

  Args:
    offset: rdfvalue.Duration how far back to look in time
    now: rdfvalue.RDFDatetime for current time
    token: GRR access token
  Yields:
    AuditEvents created during the time range
  """
  start_time = now - offset - audit.AUDIT_ROLLOVER_TIME

  for fd in audit.LegacyAuditLogsForTimespan(start_time, now, token):
    for event in fd.GenerateItems():
      if now - offset < event.timestamp < now:
        yield event
