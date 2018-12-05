#!/usr/bin/env python
"""An in memory database implementation used for testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys
import threading


from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import db
from grr_response_server.databases import mem_artifacts
from grr_response_server.databases import mem_blobs
from grr_response_server.databases import mem_clients
from grr_response_server.databases import mem_cronjobs
from grr_response_server.databases import mem_events
from grr_response_server.databases import mem_flows
from grr_response_server.databases import mem_foreman_rules
from grr_response_server.databases import mem_hunts
from grr_response_server.databases import mem_paths
from grr_response_server.databases import mem_signed_binaries
from grr_response_server.databases import mem_stats
from grr_response_server.databases import mem_users
from grr_response_server.rdfvalues import objects as rdf_objects


# pyformat: disable
class InMemoryDB(mem_artifacts.InMemoryDBArtifactsMixin,
                 mem_blobs.InMemoryDBBlobsMixin,
                 mem_clients.InMemoryDBClientMixin,
                 mem_cronjobs.InMemoryDBCronJobMixin,
                 mem_events.InMemoryDBEventMixin,
                 mem_flows.InMemoryDBFlowMixin,
                 mem_foreman_rules.InMemoryDBForemanRulesMixin,
                 mem_hunts.InMemoryDBHuntMixin,
                 mem_paths.InMemoryDBPathMixin,
                 mem_signed_binaries.InMemoryDBSignedBinariesMixin,
                 mem_stats.InMemoryDBStatsMixin,
                 mem_users.InMemoryDBUsersMixin,
                 db.Database):
  """An in memory database implementation used for testing."""
  # pyformat: enable

  def __init__(self):
    super(InMemoryDB, self).__init__()
    self._Init()
    self.lock = threading.RLock()

  def _Init(self):
    self.artifacts = {}
    self.approvals_by_username = {}
    self.clients = {}
    self.client_messages = {}
    self.client_message_leases = {}
    self.crash_history = {}
    self.cronjob_leases = {}
    self.cronjobs = {}
    self.foreman_rules = []
    self.keywords = {}
    self.labels = {}
    self.message_handler_leases = {}
    self.message_handler_requests = {}
    self.metadatas = {}
    self.notifications_by_username = {}
    self.startup_history = {}
    # TODO(hanuszczak): Consider chaning this to nested dicts for improved
    # debugging experience.
    # Maps (client_id, path_type, components) to a path record.
    self.path_records = {}
    # Maps (client_id, path_type, path_id) to a blob record.
    self.blob_records = {}
    self.message_handler_requests = {}
    self.message_handler_leases = {}
    self.cronjobs = {}
    self.cronjob_leases = {}
    self.cronjob_runs = {}
    self.foreman_rules = []
    self.blobs = {}
    self.blob_refs_by_hashes = {}
    self.users = {}
    self.handler_thread = None
    self.handler_stop = True
    # Maps (client_id, flow_id) to flow objects.
    self.flows = {}
    # Maps (client_id, flow_id) to flow request id to the request.
    self.flow_requests = {}
    # Maps (client_id, flow_id) to flow request id to a list of responses.
    self.flow_responses = {}
    # Maps (client_id, flow_id, request_id) to FlowProcessingRequest rdfvalues.
    self.flow_processing_requests = {}
    # Maps (client_id, flow_id) to [FlowResult].
    self.flow_results = {}
    # Maps (client_id, flow_id) to [FlowLogEntry].
    self.flow_log_entries = {}
    self.flow_handler_target = None
    self.flow_handler_thread = None
    self.flow_handler_stop = True
    self.stats_store_entries = {}
    self.api_audit_entries = []
    self.hunts = {}
    self.signed_binary_references = {}

  @utils.Synchronized
  def ClearTestDB(self):
    self.UnregisterMessageHandler()
    self._Init()

  def _AllPathIDs(self):
    result = set()

    for client_id, path_type, components in self.path_records:
      path_id = rdf_objects.PathID.FromComponents(components)
      result.add((client_id, path_type, path_id))

    return result

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
