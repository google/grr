#!/usr/bin/env python
"""The in memory database methods for event handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils


class InMemoryDBEventMixin(object):
  """InMemoryDB mixin for event handling."""

  @utils.Synchronized
  def ReadAPIAuditEntries(self,
                          username=None,
                          router_method_name=None,
                          min_timestamp=None,
                          max_timestamp=None):
    """Returns audit entries stored in the database."""
    results = []

    for entry in self.api_audit_entries:
      if username is not None and entry.username != username:
        continue

      if (router_method_name is not None and
          entry.router_method_name != router_method_name):
        continue

      if min_timestamp is not None and entry.timestamp < min_timestamp:
        continue

      if max_timestamp is not None and entry.timestamp > max_timestamp:
        continue

      results.append(entry)

    return sorted(results, key=lambda entry: entry.timestamp)

  @utils.Synchronized
  def WriteAPIAuditEntry(self, entry):
    """Writes an audit entry to the database."""
    copy = entry.Copy()
    copy.timestamp = rdfvalue.RDFDatetime.Now()
    self.api_audit_entries.append(copy)
