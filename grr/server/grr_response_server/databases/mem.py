#!/usr/bin/env python
"""An in memory database implementation used for testing."""

import collections
from collections.abc import Callable
import sys
import threading
from typing import Any

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db
from grr_response_server.databases import mem_artifacts
from grr_response_server.databases import mem_blob_keys
from grr_response_server.databases import mem_blobs
from grr_response_server.databases import mem_clients
from grr_response_server.databases import mem_cronjobs
from grr_response_server.databases import mem_events
from grr_response_server.databases import mem_flows
from grr_response_server.databases import mem_foreman_rules
from grr_response_server.databases import mem_hunts
from grr_response_server.databases import mem_paths
from grr_response_server.databases import mem_signed_binaries
from grr_response_server.databases import mem_signed_commands
from grr_response_server.databases import mem_users
from grr_response_server.databases import mem_yara
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class InMemoryDB(
    mem_artifacts.InMemoryDBArtifactsMixin,
    mem_blob_keys.InMemoryDBBlobKeysMixin,
    mem_blobs.InMemoryDBBlobsMixin,
    mem_clients.InMemoryDBClientMixin,
    mem_cronjobs.InMemoryDBCronJobMixin,
    mem_events.InMemoryDBEventMixin,
    mem_flows.InMemoryDBFlowMixin,
    mem_foreman_rules.InMemoryDBForemanRulesMixin,
    mem_hunts.InMemoryDBHuntMixin,
    mem_paths.InMemoryDBPathMixin,
    mem_signed_binaries.InMemoryDBSignedBinariesMixin,
    mem_signed_commands.InMemoryDBSignedCommandsMixin,
    mem_users.InMemoryDBUsersMixin,
    mem_yara.InMemoryDBYaraMixin,
    db.Database,
):
  """An in memory database implementation used for testing."""

  rrg_startups: dict[str, list[rrg_startup_pb2.Startup]]

  def __init__(self):
    super().__init__()
    self._Init()
    self.lock = threading.RLock()

  def _Init(self):
    self.artifacts = {}
    self.approvals_by_username: dict[
        str, dict[str, objects_pb2.ApprovalRequest]
    ] = {}
    self.blob_keys: dict[models_blobs.BlobID, str] = {}
    # Serialized `objects_pb2.ClientSnapshot`.
    self.clients: dict[str, dict[rdfvalue.RDFDatetime, bytes]] = {}
    # Serialized `jobs_pb2.ClientCrash`.
    self.crash_history: dict[str, dict[rdfvalue.RDFDatetime, bytes]] = {}
    self.foreman_rules: list[jobs_pb2.ForemanCondition] = []
    self.keywords: dict[str, dict[str, rdfvalue.RDFDatetime]] = {}
    self.labels: dict[str, dict[str, set[str]]] = {}
    # Maps handler_id to dict[request_id, lease expiration time in us].
    self.message_handler_leases: dict[str, dict[str, int]] = {}
    # Maps handler_id to dict[request_id, MessageHandlerRequest].
    self.message_handler_requests: dict[
        str, dict[str, objects_pb2.MessageHandlerRequest]
    ] = {}
    # Maps client_id to client metadata.
    self.metadatas: dict[str, Any] = {}
    self.notifications_by_username: dict[str, objects_pb2.UserNotification] = {}
    # Serialized `jobs_pb2.StartupInfo`.
    self.startup_history: dict[str, dict[rdfvalue.RDFDatetime, bytes]] = {}
    self.rrg_startups: dict[str, list[rrg_startup_pb2.Startup]] = (
        collections.defaultdict(list)
    )
    # Maps `(client_id, flow_id)` to a mapping of `(request_id, response_id)` to
    # a log entry.
    self.rrg_logs: dict[tuple[str, str], dict[tuple[int, int], rrg_pb2.Log]] = (
        {}
    )
    # TODO(hanuszczak): Consider changing this to nested dicts for improved
    # debugging experience.
    # Maps (client_id, path_type, components) to a path record.
    self.path_records: dict[
        tuple[str, "objects_pb2.PathInfo.PathType", tuple[str, ...]], Any
    ] = {}
    # Maps cron_job_id to cron_job
    self.cronjobs: dict[str, flows_pb2.CronJob] = {}
    self.cronjob_leases: dict[str, tuple[int, str]] = {}
    # Maps (cron_job_id, run_id) to cron_job_run
    self.cronjob_runs: dict[tuple[str, str], flows_pb2.CronJobRun] = {}
    self.blobs: dict[models_blobs.BlobID, bytes] = {}
    self.blob_refs_by_hashes: dict[
        rdf_objects.SHA256HashID, list[objects_pb2.BlobReference]
    ] = {}
    self.users: dict[str, objects_pb2.GRRUser] = {}
    self.handler_thread: threading.Thread = None
    self.handler_stop = True
    # Maps (client_id, flow_id) to flow objects.
    self.flows: dict[tuple[str, str], flows_pb2.Flow] = {}
    # Maps (client_id, flow_id) to flow request id to the request.
    self.flow_requests: dict[
        tuple[str, str], dict[str, flows_pb2.FlowRequest]
    ] = {}
    # Maps (client_id, flow_id) to flow request id to a list of responses.
    self.flow_responses: dict[tuple[str, str], list[flows_pb2.FlowResponse]] = (
        {}
    )
    # Maps (client_id, flow_id, request_id) to FlowProcessingRequest rdfvalues.
    self.flow_processing_requests: dict[
        tuple[str, str, str], flows_pb2.FlowProcessingRequest
    ] = {}
    # Maps (client_id, flow_id) to [FlowResult].
    self.flow_results: dict[tuple[str, str], list[flows_pb2.FlowResult]] = {}
    # Maps (client_id, flow_id) to [FlowError].
    self.flow_errors: dict[tuple[str, str], list[flows_pb2.FlowError]] = {}
    # Maps (client_id, flow_id) to [FlowLogEntry].
    self.flow_log_entries: dict[
        tuple[str, str], list[flows_pb2.FlowLogEntry]
    ] = {}
    self.flow_output_plugin_log_entries: dict[
        tuple[str, str], list[flows_pb2.FlowOutputPluginLogEntry]
    ] = {}
    self.flow_handler_target: Callable[
        [flows_pb2.FlowProcessingRequest], None
    ] = None
    self.flow_handler_thread: threading.Thread = None
    self.flow_handler_stop = True
    self.flow_handler_num_being_processed = 0
    self.api_audit_entries: list[objects_pb2.APIAuditEntry] = []
    self.hunts: dict[str, hunts_pb2.Hunt] = {}
    # Maps hunt_id to a list of serialized output_plugin_pb2.OutputPluginState.
    self.hunt_output_plugins_states: dict[str, list[bytes]] = {}
    # Maps (binary-type, binary-path) to (objects_pb2.BlobReferences, timestamp)
    self.signed_binary_references: dict[
        tuple[int, str], tuple[objects_pb2.BlobReferences, rdfvalue.RDFDatetime]
    ] = {}
    # Maps (client_id, creator, scheduled_flow_id) to ScheduledFlow.
    self.scheduled_flows: dict[
        tuple[str, str, str], flows_pb2.ScheduledFlow
    ] = {}
    # Maps (command_name, operating_system) to SignedCommand.
    self.signed_commands: dict[
        tuple[str, signed_commands_pb2.SignedCommand.OS],
        signed_commands_pb2.SignedCommand,
    ] = {}

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

  def _DeepCopy(self, obj):
    """Creates an object copy by serializing/deserializing it.

    RDFStruct.Copy() doesn't deep-copy repeated fields which may lead to
    hard to catch bugs.

    Args:
      obj: RDFValue to be copied.

    Returns:
      A deep copy of the passed RDFValue.
    """
    precondition.AssertType(obj, rdfvalue.RDFValue)

    return obj.__class__.FromSerializedBytes(obj.SerializeToBytes())

  def Now(self) -> rdfvalue.RDFDatetime:
    del self  # Unused.
    return rdfvalue.RDFDatetime.Now()

  def MinTimestamp(self) -> rdfvalue.RDFDatetime:
    return rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)
