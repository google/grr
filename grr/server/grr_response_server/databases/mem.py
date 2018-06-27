#!/usr/bin/env python
"""An in memory database implementation used for testing."""

import sys
import threading

from grr.lib import rdfvalue
from grr.lib import utils
from grr.server.grr_response_server import db
from grr.server.grr_response_server.databases import mem_clients
from grr.server.grr_response_server.databases import mem_cronjobs
from grr.server.grr_response_server.databases import mem_events
from grr.server.grr_response_server.databases import mem_flows
from grr.server.grr_response_server.databases import mem_foreman_rules
from grr.server.grr_response_server.databases import mem_paths
from grr.server.grr_response_server.databases import mem_users


# pyformat: disable
class InMemoryDB(mem_clients.InMemoryDBClientMixin,
                 mem_cronjobs.InMemoryDBCronjobMixin,
                 mem_events.InMemoryDBEventMixin,
                 mem_flows.InMemoryDBFlowMixin,
                 mem_foreman_rules.InMemoryDBForemanRulesMixin,
                 mem_paths.InMemoryDBPathMixin,
                 mem_users.InMemoryDBUsersMixin,
                 db.Database):
  """An in memory database implementation used for testing."""
  # pyformat: enable

  def __init__(self):
    super(InMemoryDB, self).__init__()
    self._Init()
    self.lock = threading.RLock()

  def _Init(self):
    self.metadatas = {}
    self.clients = {}
    self.keywords = {}
    self.labels = {}
    self.users = {}
    self.startup_history = {}
    self.crash_history = {}
    self.approvals_by_username = {}
    self.notifications_by_username = {}
    # Maps (client_id, path_type, path_id) to a path record.
    self.path_records = {}
    self.message_handler_requests = {}
    self.message_handler_leases = {}
    self.events = []
    self.cronjobs = {}
    self.cronjob_leases = {}
    self.foreman_rules = []

  @utils.Synchronized
  def ClearTestDB(self):
    self._Init()

  def _ParseTimeRange(self, timerange):
    """Parses a timerange argument and always returns non-None timerange."""
    if timerange is None:
      timerange = (None, None)

    from_time, to_time = timerange
    if not from_time:
      from_time = rdfvalue.RDFDatetime().FromSecondsSinceEpoch(0)

    if not to_time:
      to_time = rdfvalue.RDFDatetime().FromSecondsSinceEpoch(sys.maxsize)

    return (from_time, to_time)
