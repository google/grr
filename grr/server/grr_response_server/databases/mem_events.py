#!/usr/bin/env python
"""The in memory database methods for event handling."""

import collections
from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import objects_pb2


class InMemoryDBEventMixin(object):
  """InMemoryDB mixin for event handling."""

  api_audit_entries: list[objects_pb2.APIAuditEntry]

  @utils.Synchronized
  def ReadAPIAuditEntries(
      self,
      username: Optional[str] = None,
      router_method_names: Optional[list[str]] = None,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> list[objects_pb2.APIAuditEntry]:
    """Returns audit entries stored in the database."""
    results = []

    for entry in self.api_audit_entries:
      if username and entry.username != username:
        continue

      if (
          router_method_names
          and entry.router_method_name not in router_method_names
      ):
        continue

      if (
          min_timestamp is not None
          and entry.timestamp < min_timestamp.AsMicrosecondsSinceEpoch()
      ):
        continue

      if (
          max_timestamp is not None
          and entry.timestamp > max_timestamp.AsMicrosecondsSinceEpoch()
      ):
        continue

      results.append(entry)

    return sorted(results, key=lambda entry: entry.timestamp)

  @utils.Synchronized
  def CountAPIAuditEntriesByUserAndDay(
      self,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, rdfvalue.RDFDatetime], int]:
    """Returns audit entry counts grouped by user and calendar day."""
    results = collections.Counter()
    for entry in self.api_audit_entries:
      if (
          min_timestamp is not None
          and entry.timestamp < min_timestamp.AsMicrosecondsSinceEpoch()
      ):
        continue

      if (
          max_timestamp is not None
          and entry.timestamp > max_timestamp.AsMicrosecondsSinceEpoch()
      ):
        continue

      # Truncate DateTime by removing the time-part to allow grouping by date.
      rdf_dt = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(entry.timestamp)
      day = rdfvalue.RDFDatetime.FromDate(rdf_dt.AsDatetime().date())
      results[(entry.username, day)] += 1

    return dict(results)

  @utils.Synchronized
  def WriteAPIAuditEntry(self, entry: objects_pb2.APIAuditEntry) -> None:
    """Writes an audit entry to the database."""
    copy = objects_pb2.APIAuditEntry()
    copy.CopyFrom(entry)
    if not copy.HasField("timestamp"):
      copy.timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    self.api_audit_entries.append(copy)
