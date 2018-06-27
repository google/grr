#!/usr/bin/env python
"""The in memory database methods for event handling."""

from grr.lib import rdfvalue
from grr.lib import utils


class InMemoryDBEventMixin(object):
  """InMemoryDB mixin for event handling."""

  @utils.Synchronized
  def ReadAllAuditEvents(self):
    return sorted(self.events, key=lambda event: event.timestamp)

  @utils.Synchronized
  def WriteAuditEvent(self, event):
    event = event.Copy()
    event.timestamp = rdfvalue.RDFDatetime.Now()
    self.events.append(event)
