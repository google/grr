#!/usr/bin/env python
"""UI report handling helper utils."""

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collects


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

  return aff4.FACTORY.MultiOpen(
      logs, aff4_type=collects.RDFValueCollection, token=token)
