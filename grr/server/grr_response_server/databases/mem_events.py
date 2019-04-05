#!/usr/bin/env python
"""The in memory database methods for event handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils


class InMemoryDBEventMixin(object):
  """InMemoryDB mixin for event handling."""

  @utils.Synchronized
  def ReadAPIAuditEntries(self,
                          username=None,
                          router_method_names=None,
                          min_timestamp=None,
                          max_timestamp=None):
    """Returns audit entries stored in the database."""
    results = []

    for entry in self.api_audit_entries:
      if username is not None and entry.username != username:
        continue

      if (router_method_names and
          entry.router_method_name not in router_method_names):
        continue

      if min_timestamp is not None and entry.timestamp < min_timestamp:
        continue

      if max_timestamp is not None and entry.timestamp > max_timestamp:
        continue

      results.append(entry)

    return sorted(results, key=lambda entry: entry.timestamp)

  @utils.Synchronized
  def CountAPIAuditEntriesByUserAndDay(self,
                                       min_timestamp=None,
                                       max_timestamp=None):
    """Returns audit entry counts grouped by user and calendar day."""
    results = collections.Counter()
    for entry in self.api_audit_entries:
      if min_timestamp is not None and entry.timestamp < min_timestamp:
        continue

      if max_timestamp is not None and entry.timestamp > max_timestamp:
        continue

      # Truncate DateTime by removing the time-part to allow grouping by date.
      day = rdfvalue.RDFDatetime.FromDate(entry.timestamp.AsDatetime().date())
      results[(entry.username, day)] += 1

    return dict(results)

  @utils.Synchronized
  def WriteAPIAuditEntry(self, entry):
    """Writes an audit entry to the database."""
    copy = entry.Copy()
    copy.timestamp = rdfvalue.RDFDatetime.Now()
    self.api_audit_entries.append(copy)
