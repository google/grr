#!/usr/bin/env python
"""API handlers for accessing and searching clients and managing labels."""
import ipaddress
import re
import shlex
from typing import Optional

from urllib import parse as urlparse

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import search as rdf_search
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import precondition
from grr_response_proto.api import client_pb2
from grr_response_server import action_registry
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import flow
from grr_response_server import ip_resolver
from grr_response_server import timeseries
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui.api_plugins import stats as api_stats
from grr_response_server.rdfvalues import objects as rdf_objects
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2


def UpdateClientsFromFleetspeak(clients):
  """Updates ApiClient records to include info from Fleetspeak."""
  if not fleetspeak_connector.CONN or not fleetspeak_connector.CONN.outgoing:
    # FS not configured, or an outgoing connection is otherwise unavailable.
    return
  id_map = {}
  for client in clients:
    if client.fleetspeak_enabled:
      id_map[fleetspeak_utils.GRRIDToFleetspeakID(client.client_id)] = client
  if not id_map:
    return
  res = fleetspeak_connector.CONN.outgoing.ListClients(
      admin_pb2.ListClientsRequest(client_ids=list(id_map.keys())))
  for read in res.clients:
    api_client = id_map[read.client_id]
    api_client.last_seen_at = fleetspeak_utils.TSToRDFDatetime(
        read.last_contact_time)
    api_client.last_clock = fleetspeak_utils.TSToRDFDatetime(read.last_clock)


class InterrogateOperationNotFoundError(
    api_call_handler_base.ResourceNotFoundError):
  """Raised when an interrogate operation could not be found."""


class ApiClientId(rdfvalue.RDFString):
  """Class encapsulating client ids."""

  CLIENT_ID_RE = re.compile(r"^C\.[0-9a-fA-F]{16}$")

  def __init__(self, initializer=None):
    if isinstance(initializer, rdf_client.ClientURN):
      initializer = initializer.Basename()

    super().__init__(initializer=initializer)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      re_match = self.CLIENT_ID_RE.match(self._value)
      if not re_match:
        raise ValueError("Invalid client id: %s" % str(self._value))

  def ToString(self):
    if not self._value:
      raise ValueError("Can't call ToString() on an empty client id.")

    return self._value


class ApiClient(rdf_structs.RDFProtoStruct):
  """API client object."""

  protobuf = client_pb2.ApiClient
  rdf_deps = [
      rdf_objects.ClientLabel,
      ApiClientId,
      rdfvalue.ByteSize,
      rdf_client.ClientInformation,
      rdf_client.ClientURN,
      rdf_cloud.CloudInstance,
      rdf_client.HardwareInfo,
      rdf_client_network.Interface,
      rdf_client.KnowledgeBase,
      rdfvalue.RDFDatetime,
      rdf_client.Uname,
      rdf_client.User,
      rdf_client_fs.Volume,
  ]

  def InitFromClientObject(
      self, client_obj: rdf_objects.ClientSnapshot) -> "ApiClient":

    # TODO(amoser): Deprecate all urns.
    self.urn = client_obj.client_id

    self.client_id = client_obj.client_id

    if client_obj.metadata and client_obj.metadata.source_flow_id:
      self.source_flow_id = client_obj.metadata.source_flow_id

    self.agent_info = client_obj.startup_info.client_info
    self.hardware_info = client_obj.hardware_info

    os_info = rdf_client.Uname()
    if client_obj.os_version:
      os_info.version = client_obj.os_version
    if client_obj.os_release:
      os_info.release = client_obj.os_release
    if client_obj.kernel:
      os_info.kernel = client_obj.kernel
    if client_obj.arch:
      os_info.machine = client_obj.arch
    if client_obj.install_time:
      os_info.install_date = client_obj.install_time

    kb = client_obj.knowledge_base
    if kb:
      self.knowledge_base = kb
      if kb.os:
        os_info.system = kb.os
      if kb.fqdn:
        os_info.fqdn = kb.fqdn

      # TODO(amoser): Deprecate this field in favor of the kb.
      if kb.users:
        self.users = sorted(kb.users, key=lambda user: user.username)

    self.os_info = os_info

    if client_obj.interfaces:
      self.interfaces = client_obj.interfaces
    if client_obj.volumes:
      self.volumes = client_obj.volumes
    if client_obj.cloud_instance:
      self.cloud_instance = client_obj.cloud_instance

    self.age = client_obj.timestamp

    if client_obj.memory_size:
      self.memory_size = client_obj.memory_size
    if client_obj.startup_info.boot_time:
      self.last_booted_at = client_obj.startup_info.boot_time

    return self

  def InitFromClientInfo(
      self,
      client_id: str,
      client_info: rdf_objects.ClientFullInfo,
  ) -> "ApiClient":
    self.client_id = client_id

    if client_info.HasField("last_snapshot"):
      # Just a sanity check to ensure that the object has correct client id.
      if client_info.last_snapshot.client_id != client_id:
        raise ValueError(f"Invalid last snapshot client id: "
                         f"{client_id} expected but "
                         f"{client_info.last_snapshot.client_id} found")

      self.InitFromClientObject(client_info.last_snapshot)
    else:
      # Every returned object should have `age` specified. If we cannot get this
      # information from the snapshot (because there is none), we just use the
      # time of the first observation of the client.
      if not client_info.last_snapshot.timestamp:
        self.age = client_info.metadata.first_seen

    # If we have it, use the boot_time / agent info from the startup
    # info which might be more recent than the interrogation
    # results. At some point we should have a dedicated API for
    # startup information instead of packing it into the API client
    # object.
    if client_info.last_startup_info.boot_time:
      self.last_booted_at = client_info.last_startup_info.boot_time
    if client_info.last_startup_info.client_info:
      self.agent_info = client_info.last_startup_info.client_info

    md = client_info.metadata
    if md:
      if md.first_seen:
        self.first_seen_at = md.first_seen
      if md.ping:
        self.last_seen_at = md.ping
      if md.clock:
        self.last_clock = md.clock
      if md.last_crash_timestamp:
        self.last_crash_at = md.last_crash_timestamp
      self.fleetspeak_enabled = md.fleetspeak_enabled

    self.labels = client_info.labels

    return self

  def ObjectReference(self):
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.CLIENT,
        client=rdf_objects.ClientReference(client_id=str(self.client_id)))


class ApiClientActionRequest(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiClientActionRequest
  rdf_deps = [
      rdf_flows.GrrMessage,
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]


class ApiSearchClientsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiSearchClientsArgs


class ApiSearchClientsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiSearchClientsResult
  rdf_deps = [
      ApiClient,
  ]


class ApiSearchClientsHandler(api_call_handler_base.ApiCallHandler):
  """Renders results of a client search."""

  args_type = ApiSearchClientsArgs
  result_type = ApiSearchClientsResult

  def Handle(self, args, context=None):
    end = args.count or db.MAX_COUNT

    keywords = shlex.split(args.query)

    api_clients = []

    index = client_index.ClientIndex()

    # LookupClients returns a sorted list of client ids.
    clients = index.LookupClients(keywords)[args.offset:args.offset + end]

    client_infos = data_store.REL_DB.MultiReadClientFullInfo(clients)
    for client_id, client_info in client_infos.items():
      api_clients.append(ApiClient().InitFromClientInfo(client_id, client_info))

    UpdateClientsFromFleetspeak(api_clients)
    return ApiSearchClientsResult(items=api_clients)


class ApiStructuredSearchClientsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiStructuredSearchClientsArgs
  rdf_deps = [rdf_search.SearchExpression, rdf_search.SortOrder]


class ApiStructuredSearchClientsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiStructuredSearchClientsResult
  rdf_deps = [
      ApiClient,
  ]


class ApiStructuredSearchClientsHandler(api_call_handler_base.ApiCallHandler):
  """Renders results of a client structured search."""

  args_type = ApiStructuredSearchClientsArgs
  result_type = ApiStructuredSearchClientsResult

  def Handle(self, args, context=None):
    # TODO: Implement this method.
    raise NotImplementedError()


class ApiLabelsRestrictedStructuredSearchClientsHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders results of a client structured search."""

  args_type = ApiStructuredSearchClientsArgs
  result_type = ApiStructuredSearchClientsResult

  def Handle(self, args, context=None):
    # TODO: Implement this method.
    raise NotImplementedError()


class ApiLabelsRestrictedSearchClientsHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders results of a client search."""

  args_type = ApiSearchClientsArgs
  result_type = ApiSearchClientsResult

  def __init__(self, allow_labels=None, allow_labels_owners=None):
    super().__init__()

    self.allow_labels = set(allow_labels or [])
    self.allow_labels_owners = set(allow_labels_owners or [])

  def _VerifyLabels(self, labels):
    for label in labels:
      if (label.name in self.allow_labels and
          label.owner in self.allow_labels_owners):
        return True
    return False

  def Handle(self, args, context=None):
    if args.count:
      end = args.offset + args.count
      # Read <count> clients ahead in case some of them fail to open / verify.
      batch_size = end + args.count
    else:
      end = db.MAX_COUNT
      batch_size = end

    keywords = shlex.split(args.query)
    api_clients = []

    index = client_index.ClientIndex()

    # TODO(amoser): We could move the label verification into the
    # database making this method more efficient. Label restrictions
    # should be on small subsets though so this might not be worth
    # it.
    all_client_ids = set()
    for label in self.allow_labels:
      label_filter = ["label:" + label] + keywords
      all_client_ids.update(index.LookupClients(label_filter))

    index = 0
    for cid_batch in collection.Batch(sorted(all_client_ids), batch_size):
      client_infos = data_store.REL_DB.MultiReadClientFullInfo(cid_batch)

      for client_id, client_info in sorted(client_infos.items()):
        if not self._VerifyLabels(client_info.labels):
          continue
        if index >= args.offset and index < end:
          api_clients.append(ApiClient().InitFromClientInfo(
              client_id, client_info))
        index += 1
        if index >= end:
          UpdateClientsFromFleetspeak(api_clients)
          return ApiSearchClientsResult(items=api_clients)

    UpdateClientsFromFleetspeak(api_clients)
    return ApiSearchClientsResult(items=api_clients)


class ApiVerifyAccessArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiVerifyAccessArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiVerifyAccessResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiVerifyAccessResult
  rdf_deps = []


class ApiVerifyAccessHandler(api_call_handler_base.ApiCallHandler):
  """Dummy handler that renders empty message."""

  args_type = ApiVerifyAccessArgs
  result_type = ApiVerifyAccessResult

  def Handle(self, args, context=None):
    return ApiVerifyAccessResult()


class ApiGetClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetClientArgs
  rdf_deps = [
      ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetClientHandler(api_call_handler_base.ApiCallHandler):
  """Renders summary of a given client."""

  args_type = ApiGetClientArgs
  result_type = ApiClient

  def Handle(self, args, context=None):
    client_id = str(args.client_id)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    if info is None:
      raise api_call_handler_base.ResourceNotFoundError()

    if args.timestamp:
      # Assume that a snapshot for this particular timestamp exists.
      snapshots = data_store.REL_DB.ReadClientSnapshotHistory(
          client_id, timerange=(args.timestamp, args.timestamp))

      if snapshots:
        info.last_snapshot = snapshots[0]
        info.last_startup_info = snapshots[0].startup_info

    api_client = ApiClient().InitFromClientInfo(client_id, info)
    UpdateClientsFromFleetspeak([api_client])
    return api_client


class ApiGetClientVersionsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetClientVersionsArgs
  rdf_deps = [
      ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetClientVersionsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetClientVersionsResult
  rdf_deps = [
      ApiClient,
  ]


class ApiGetClientVersionsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves a multiple versions of a given client."""

  args_type = ApiGetClientVersionsArgs
  result_type = ApiGetClientVersionsResult

  def Handle(self, args, context=None):
    end_time = args.end or rdfvalue.RDFDatetime.Now()
    start_time = max(
        args.start or end_time - rdfvalue.Duration.From(3, rdfvalue.MINUTES),
        data_store.REL_DB.MinTimestamp(),
    )
    items = []

    client_id = str(args.client_id)
    history = data_store.REL_DB.ReadClientSnapshotHistory(
        client_id, timerange=(start_time, end_time))
    labels = data_store.REL_DB.ReadClientLabels(client_id)

    for client in history[::-1]:
      c = ApiClient().InitFromClientObject(client)
      c.labels = labels
      items.append(c)

    return ApiGetClientVersionsResult(items=items)


class ApiGetClientVersionTimesArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetClientVersionTimesArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiGetClientVersionTimesResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetClientVersionTimesResult
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiGetClientVersionTimesHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves a list of versions for the given client."""

  args_type = ApiGetClientVersionTimesArgs
  result_type = ApiGetClientVersionTimesResult

  def Handle(self, args, context=None):
    # TODO(amoser): Again, this is rather inefficient,if we moved
    # this call to the datastore we could make it much
    # faster. However, there is a chance that this will not be
    # needed anymore once we use the relational db everywhere, let's
    # decide later.
    client_id = str(args.client_id)
    history = data_store.REL_DB.ReadClientSnapshotHistory(client_id)
    times = [h.timestamp for h in history]

    return ApiGetClientVersionTimesResult(times=times)


class ApiInterrogateClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiInterrogateClientArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiInterrogateClientResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiInterrogateClientResult


class ApiInterrogateClientHandler(api_call_handler_base.ApiCallHandler):
  """Interrogates the given client."""

  args_type = ApiInterrogateClientArgs
  result_type = ApiInterrogateClientResult

  def Handle(self, args, context=None):
    flow_id = flow.StartFlow(
        flow_cls=discovery.Interrogate,
        client_id=str(args.client_id),
        creator=context.username)

    # TODO(user): don't encode client_id inside the operation_id, but
    # rather have it as a separate field.
    return ApiInterrogateClientResult(operation_id=flow_id)


class ApiGetInterrogateOperationStateArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetInterrogateOperationStateArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiGetInterrogateOperationStateResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetInterrogateOperationStateResult


class ApiGetInterrogateOperationStateHandler(
    api_call_handler_base.ApiCallHandler):
  """Retrieves the state of the interrogate operation."""

  args_type = ApiGetInterrogateOperationStateArgs
  result_type = ApiGetInterrogateOperationStateResult

  def Handle(self, args, context=None):
    client_id = str(args.client_id)
    flow_id = str(args.operation_id)

    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    # TODO(user): test both exception scenarios below.
    try:
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    except db.UnknownFlowError:
      raise InterrogateOperationNotFoundError("Operation with id %s not found" %
                                              args.operation_id)

    expected_flow_name = discovery.Interrogate.__name__
    if flow_obj.flow_class_name != expected_flow_name:
      raise InterrogateOperationNotFoundError("Operation with id %s not found" %
                                              args.operation_id)

    complete = flow_obj.flow_state != flow_obj.FlowState.RUNNING

    result = ApiGetInterrogateOperationStateResult()
    if complete:
      result.state = ApiGetInterrogateOperationStateResult.State.FINISHED
    else:
      result.state = ApiGetInterrogateOperationStateResult.State.RUNNING

    return result


class ApiGetLastClientIPAddressArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetLastClientIPAddressArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiGetLastClientIPAddressResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetLastClientIPAddressResult


def _GetAddrFromFleetspeak(client_id):
  res = fleetspeak_connector.CONN.outgoing.ListClients(
      admin_pb2.ListClientsRequest(
          client_ids=[fleetspeak_utils.GRRIDToFleetspeakID(client_id)]))
  if not res.clients or not res.clients[0].last_contact_address:
    return "", None
  # last_contact_address typically includes a port
  parsed = urlparse.urlparse("//{}".format(res.clients[0].last_contact_address))
  ip_str = parsed.hostname
  return ip_str, ipaddress.ip_address(ip_str)


class ApiGetLastClientIPAddressHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the last ip a client used for communication with the server."""

  args_type = ApiGetLastClientIPAddressArgs
  result_type = ApiGetLastClientIPAddressResult

  def Handle(self, args, context=None):
    client_id = str(args.client_id)

    md = data_store.REL_DB.ReadClientMetadata(client_id)
    if md.fleetspeak_enabled:
      ip_str, ipaddr_obj = _GetAddrFromFleetspeak(client_id)
    else:
      try:
        ipaddr_obj = md.ip.AsIPAddr()
        ip_str = str(ipaddr_obj)
      except ValueError:
        ipaddr_obj = None
        ip_str = ""

    status, info = ip_resolver.IP_RESOLVER.RetrieveIPInfo(ipaddr_obj)

    return ApiGetLastClientIPAddressResult(ip=ip_str, info=info, status=status)


class ApiListClientCrashesArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListClientCrashesArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiListClientCrashesResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListClientCrashesResult
  rdf_deps = [
      rdf_client.ClientCrash,
  ]


class ApiListClientCrashesHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of crashes for the given client."""

  args_type = ApiListClientCrashesArgs
  result_type = ApiListClientCrashesResult

  def Handle(self, args, context=None):
    crashes = data_store.REL_DB.ReadClientCrashInfoHistory(str(args.client_id))
    total_count = len(crashes)
    result = api_call_handler_utils.FilterList(
        crashes, args.offset, count=args.count, filter_value=args.filter)

    return ApiListClientCrashesResult(items=result, total_count=total_count)


class ApiAddClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiAddClientsLabelsArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiAddClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Adds labels to a given client."""

  args_type = ApiAddClientsLabelsArgs

  def Handle(self, args, context=None):
    client_ids = list(map(str, args.client_ids))
    labels = args.labels

    data_store.REL_DB.MultiAddClientLabels(client_ids, context.username, labels)

    idx = client_index.ClientIndex()
    idx.MultiAddClientLabels(client_ids, args.labels)


class ApiRemoveClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiRemoveClientsLabelsArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiRemoveClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Remove labels from a given client."""

  args_type = ApiRemoveClientsLabelsArgs

  def Handle(self, args, context=None):
    for client_id in args.client_ids:
      cid = str(client_id)
      data_store.REL_DB.RemoveClientLabels(cid, context.username, args.labels)
      labels_to_remove = set(args.labels)
      existing_labels = data_store.REL_DB.ReadClientLabels(cid)
      for label in existing_labels:
        labels_to_remove.discard(label.name)
      if labels_to_remove:
        idx = client_index.ClientIndex()
        idx.RemoveClientLabels(cid, labels_to_remove)


class ApiListClientsLabelsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListClientsLabelsResult
  rdf_deps = [
      rdf_objects.ClientLabel,
  ]


class ApiListClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients labels."""

  result_type = ApiListClientsLabelsResult

  def Handle(self, args, context=None):
    labels = data_store.REL_DB.ReadAllClientLabels()

    label_objects = []
    for name in labels:
      label_objects.append(rdf_objects.ClientLabel(name=name))

    return ApiListClientsLabelsResult(
        items=sorted(label_objects, key=lambda l: l.name))


class ApiListKbFieldsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListKbFieldsResult


class ApiListKbFieldsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients knowledge base fields."""

  result_type = ApiListKbFieldsResult

  def Handle(self, args, context=None):
    fields = rdf_client.KnowledgeBase().GetKbFieldNames()
    return ApiListKbFieldsResult(items=sorted(fields))


class ApiListClientActionRequestsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListClientActionRequestsArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiListClientActionRequestsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListClientActionRequestsResult
  rdf_deps = [
      ApiClientActionRequest,
  ]


class ApiListClientActionRequestsHandler(api_call_handler_base.ApiCallHandler):
  """Lists pending client action requests."""

  args_type = ApiListClientActionRequestsArgs
  result_type = ApiListClientActionRequestsResult

  REQUESTS_NUM_LIMIT = 1000

  def Handle(self, args, context=None):
    result = ApiListClientActionRequestsResult()

    request_cache = {}

    for r in data_store.REL_DB.ReadAllClientActionRequests(str(args.client_id)):
      stub = action_registry.ACTION_STUB_BY_ID[r.action_identifier]
      client_action = stub.__name__

      request = ApiClientActionRequest(
          leased_until=r.leased_until,
          session_id="%s/%s" % (r.client_id, r.flow_id),
          client_action=client_action)
      result.items.append(request)

      if not args.fetch_responses:
        continue

      if r.flow_id not in request_cache:
        req_res = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
            str(args.client_id), r.flow_id)
        request_cache[r.flow_id] = req_res

      for req, responses in request_cache[r.flow_id]:
        if req.request_id == r.request_id:
          res = []
          for resp_id in sorted(responses):
            m = responses[resp_id].AsLegacyGrrMessage()
            res.append(m)

          request.responses = res

    return result


class ApiGetClientLoadStatsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetClientLoadStatsArgs
  rdf_deps = [
      ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetClientLoadStatsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetClientLoadStatsResult
  rdf_deps = [
      api_stats.ApiStatsStoreMetricDataPoint,
  ]


class ApiGetClientLoadStatsHandler(api_call_handler_base.ApiCallHandler):
  """Returns client load stats data."""

  args_type = ApiGetClientLoadStatsArgs
  result_type = ApiGetClientLoadStatsResult

  # pyformat: disable
  GAUGE_METRICS = [
      ApiGetClientLoadStatsArgs.Metric.CPU_PERCENT,
      ApiGetClientLoadStatsArgs.Metric.MEMORY_PERCENT,
      ApiGetClientLoadStatsArgs.Metric.MEMORY_RSS_SIZE,
      ApiGetClientLoadStatsArgs.Metric.MEMORY_VMS_SIZE
  ]
  # pyformat: enable
  MAX_SAMPLES = 100

  def Handle(self, args, context=None):
    start_time = args.start
    end_time = args.end

    if not end_time:
      end_time = rdfvalue.RDFDatetime.Now()

    if not start_time:
      start_time = end_time - rdfvalue.Duration.From(30, rdfvalue.MINUTES)

    stat_values = data_store.REL_DB.ReadClientStats(
        client_id=str(args.client_id),
        min_timestamp=start_time,
        max_timestamp=end_time)
    points = []
    for stat_value in reversed(stat_values):
      if args.metric == args.Metric.CPU_PERCENT:
        points.extend(
            (s.cpu_percent, s.timestamp) for s in stat_value.cpu_samples)
      elif args.metric == args.Metric.CPU_SYSTEM:
        points.extend(
            (s.system_cpu_time, s.timestamp) for s in stat_value.cpu_samples)
      elif args.metric == args.Metric.CPU_USER:
        points.extend(
            (s.user_cpu_time, s.timestamp) for s in stat_value.cpu_samples)
      elif args.metric == args.Metric.IO_READ_BYTES:
        points.extend(
            (s.read_bytes, s.timestamp) for s in stat_value.io_samples)
      elif args.metric == args.Metric.IO_WRITE_BYTES:
        points.extend(
            (s.write_bytes, s.timestamp) for s in stat_value.io_samples)
      elif args.metric == args.Metric.IO_READ_OPS:
        points.extend(
            (s.read_count, s.timestamp) for s in stat_value.io_samples)
      elif args.metric == args.Metric.IO_WRITE_OPS:
        points.extend(
            (s.write_count, s.timestamp) for s in stat_value.io_samples)
      elif args.metric == args.Metric.NETWORK_BYTES_RECEIVED:
        points.append((stat_value.bytes_received, stat_value.timestamp))
      elif args.metric == args.Metric.NETWORK_BYTES_SENT:
        points.append((stat_value.bytes_sent, stat_value.timestamp))
      elif args.metric == args.Metric.MEMORY_PERCENT:
        points.append((stat_value.memory_percent, stat_value.timestamp))
      elif args.metric == args.Metric.MEMORY_RSS_SIZE:
        points.append((stat_value.RSS_size, stat_value.timestamp))
      elif args.metric == args.Metric.MEMORY_VMS_SIZE:
        points.append((stat_value.VMS_size, stat_value.timestamp))
      else:
        raise ValueError("Unknown metric.")

    # Points collected from "cpu_samples" and "io_samples" may not be correctly
    # sorted in some cases (as overlaps between different stat_values are
    # possible).
    points.sort(key=lambda x: x[1])

    ts = timeseries.Timeseries()
    ts.MultiAppend(points)

    if args.metric not in self.GAUGE_METRICS:
      ts.MakeIncreasing()

    if len(stat_values) > self.MAX_SAMPLES:
      sampling_interval = rdfvalue.Duration.From(
          ((end_time - start_time).ToInt(rdfvalue.SECONDS) // self.MAX_SAMPLES)
          or 1, rdfvalue.SECONDS)
      if args.metric in self.GAUGE_METRICS:
        mode = timeseries.NORMALIZE_MODE_GAUGE
      else:
        mode = timeseries.NORMALIZE_MODE_COUNTER

      ts.Normalize(sampling_interval, start_time, end_time, mode=mode)

    result = ApiGetClientLoadStatsResult()
    for value, timestamp in ts.data:
      dp = api_stats.ApiStatsStoreMetricDataPoint(
          timestamp=timestamp, value=float(value))
      result.data_points.append(dp)

    return result


def _CheckFleetspeakConnection() -> None:
  if fleetspeak_connector.CONN is None:
    raise Exception("Fleetspeak connection is not available.")


class ApiKillFleetspeakArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiKillFleetspeakArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiKillFleetspeakHandler(api_call_handler_base.ApiCallHandler):
  """Kills fleetspeak on the given client."""

  args_type = ApiKillFleetspeakArgs

  def Handle(self,
             args: ApiKillFleetspeakArgs,
             context: Optional[api_call_context.ApiCallContext] = None) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.KillFleetspeak(str(args.client_id), args.force)


class ApiRestartFleetspeakGrrServiceArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiRestartFleetspeakGrrServiceArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiRestartFleetspeakGrrServiceHandler(api_call_handler_base.ApiCallHandler
                                           ):
  """Restarts the GRR fleetspeak service on the given client."""

  args_type = ApiRestartFleetspeakGrrServiceArgs

  def Handle(self,
             args: ApiRestartFleetspeakGrrServiceArgs,
             context: Optional[api_call_context.ApiCallContext] = None) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.RestartFleetspeakGrrService(str(args.client_id))


class ApiDeleteFleetspeakPendingMessagesArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiDeleteFleetspeakPendingMessagesArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiDeleteFleetspeakPendingMessagesHandler(
    api_call_handler_base.ApiCallHandler):
  """Deletes pending fleetspeak messages for the given client."""

  args_type = ApiDeleteFleetspeakPendingMessagesArgs

  def Handle(self,
             args: ApiDeleteFleetspeakPendingMessagesArgs,
             context: Optional[api_call_context.ApiCallContext] = None) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.DeleteFleetspeakPendingMessages(str(args.client_id))


class ApiGetFleetspeakPendingMessageCountArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetFleetspeakPendingMessageCountArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiGetFleetspeakPendingMessageCountResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetFleetspeakPendingMessageCountResult


class ApiGetFleetspeakPendingMessageCountHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the number of fleetspeak messages pending for the given client."""
  args_type = ApiGetFleetspeakPendingMessageCountArgs
  result_type = ApiGetFleetspeakPendingMessageCountResult

  def Handle(
      self,
      args: ApiGetFleetspeakPendingMessageCountArgs,
      context: Optional[api_call_context.ApiCallContext] = None
  ) -> ApiGetFleetspeakPendingMessageCountResult:
    _CheckFleetspeakConnection()
    return ApiGetFleetspeakPendingMessageCountResult(
        count=fleetspeak_utils.GetFleetspeakPendingMessageCount(
            str(args.client_id)))


class ApiFleetspeakAddress(rdf_structs.RDFProtoStruct):
  """Mirrors the fleetspeak proto `common_pb2.Address`."""
  protobuf = client_pb2.ApiFleetspeakAddress
  rdf_deps = [
      ApiClientId,
  ]

  @classmethod
  def FromFleetspeakProto(cls,
                          proto: common_pb2.Address) -> "ApiFleetspeakAddress":
    if proto.client_id:
      client_id = fleetspeak_utils.FleetspeakIDToGRRID(proto.client_id)
    else:
      client_id = None
    return ApiFleetspeakAddress(
        client_id=client_id,
        service_name=proto.service_name,
    )


class ApiFleetspeakAnnotations(rdf_structs.RDFProtoStruct):
  """Mirrors the proto `fleetspeak.Annotations`."""

  class Entry(rdf_structs.RDFProtoStruct):
    protobuf = client_pb2.ApiFleetspeakAnnotations.Entry

    @classmethod
    def FromFleetspeakProto(
        cls, proto: common_pb2.Annotations.Entry
    ) -> "ApiFleetspeakAnnotations.Entry":
      return ApiFleetspeakAnnotations.Entry(
          key=proto.key,
          value=proto.value,
      )

  protobuf = client_pb2.ApiFleetspeakAnnotations
  rdf_deps = [
      Entry,
  ]

  @classmethod
  def FromFleetspeakProto(
      cls, proto: common_pb2.Annotations) -> "ApiFleetspeakAnnotations":
    result = ApiFleetspeakAnnotations()
    for entry in proto.entries:
      result.entries.append(cls.Entry.FromFleetspeakProto(entry))
    return result


class ApiFleetspeakValidationInfo(rdf_structs.RDFProtoStruct):
  """Mirrors the proto `fleetspeak.ValidationInfo`."""

  class Tag(rdf_structs.RDFProtoStruct):
    protobuf = client_pb2.ApiFleetspeakValidationInfo.Tag

  protobuf = client_pb2.ApiFleetspeakValidationInfo
  rdf_deps = [
      Tag,
  ]

  @classmethod
  def FromFleetspeakProto(
      cls, proto: common_pb2.ValidationInfo) -> "ApiFleetspeakValidationInfo":
    result = ApiFleetspeakValidationInfo()
    for key, value in proto.tags.items():
      result.tags.append(cls.Tag(key=key, value=value))
    return result


class ApiFleetspeakMessageResult(rdf_structs.RDFProtoStruct):
  """Mirrors the proto `fleetspeak.MessageResult`."""
  protobuf = client_pb2.ApiFleetspeakMessageResult
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  @classmethod
  def FromFleetspeakProto(
      cls, proto: common_pb2.MessageResult) -> "ApiFleetspeakMessageResult":
    result = ApiFleetspeakMessageResult(
        failed=proto.failed,
        failed_reason=proto.failed_reason,
    )
    if proto.HasField("processed_time"):
      result.processed_time = rdfvalue.RDFDatetime.FromDatetime(
          proto.processed_time.ToDatetime())
    return result


class ApiFleetspeakMessage(rdf_structs.RDFProtoStruct):
  """Mirrors the proto `fleetspeak.Message`."""
  protobuf = client_pb2.ApiFleetspeakMessage
  rdf_deps = [
      ApiFleetspeakAddress,
      rdfvalue.RDFDatetime,
      ApiFleetspeakValidationInfo,
      ApiFleetspeakMessageResult,
      ApiFleetspeakAnnotations,
  ]

  @classmethod
  def FromFleetspeakProto(cls,
                          proto: common_pb2.Message) -> "ApiFleetspeakMessage":
    result = ApiFleetspeakMessage(
        message_id=proto.message_id,
        source_message_id=proto.source_message_id,
        message_type=proto.message_type,
        priority=cls._PriorityFromFleetspeakProto(proto.priority),
        background=proto.background,
    )
    if proto.HasField("source"):
      result.source = ApiFleetspeakAddress.FromFleetspeakProto(proto.source)
    if proto.HasField("destination"):
      result.destination = ApiFleetspeakAddress.FromFleetspeakProto(
          proto.destination)
    if proto.HasField("creation_time"):
      result.creation_time = rdfvalue.RDFDatetime.FromDatetime(
          proto.creation_time.ToDatetime())
    if proto.HasField("data"):
      result.data = cls._AnyFromFleetspeakProto(proto.data)
    if proto.HasField("validation_info"):
      result.validation_info = ApiFleetspeakValidationInfo.FromFleetspeakProto(
          proto.validation_info)
    if proto.HasField("result"):
      result.result = ApiFleetspeakMessageResult.FromFleetspeakProto(
          proto.result)
    if proto.HasField("annotations"):
      result.annotations = ApiFleetspeakAnnotations.FromFleetspeakProto(
          proto.annotations)
    return result

  _PRIORITY_MAP = {
      common_pb2.Message.Priority.MEDIUM:
          client_pb2.ApiFleetspeakMessage.Priority.MEDIUM,
      common_pb2.Message.Priority.LOW:
          client_pb2.ApiFleetspeakMessage.Priority.LOW,
      common_pb2.Message.Priority.HIGH:
          client_pb2.ApiFleetspeakMessage.Priority.HIGH,
  }

  @classmethod
  def _PriorityFromFleetspeakProto(
      cls, proto: common_pb2.Message.Priority) -> Optional[int]:
    return cls._PRIORITY_MAP.get(proto, None)

  @classmethod
  def _AnyFromFleetspeakProto(cls, proto) -> rdf_structs.AnyValue:
    return rdf_structs.AnyValue(type_url=proto.type_url, value=proto.value)


class ApiGetFleetspeakPendingMessagesArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetFleetspeakPendingMessagesArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiGetFleetspeakPendingMessagesResult(rdf_structs.RDFProtoStruct):
  """Result for ApiGetFleetspeakPendingMessagesHandler."""
  protobuf = client_pb2.ApiGetFleetspeakPendingMessagesResult
  rdf_deps = [
      ApiFleetspeakMessage,
  ]

  @classmethod
  def FromFleetspeakProto(
      cls, proto: admin_pb2.GetPendingMessagesResponse
  ) -> "ApiGetFleetspeakPendingMessagesResult":
    result = ApiGetFleetspeakPendingMessagesResult()
    for message in proto.messages:
      result.messages.append(ApiFleetspeakMessage.FromFleetspeakProto(message))
    return result


class ApiGetFleetspeakPendingMessagesHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the fleetspeak pending messages for the given client."""

  args_type = ApiGetFleetspeakPendingMessagesArgs
  result_type = ApiGetFleetspeakPendingMessagesResult

  def Handle(
      self,
      args: ApiGetFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None
  ) -> ApiGetFleetspeakPendingMessagesResult:
    _CheckFleetspeakConnection()
    return ApiGetFleetspeakPendingMessagesResult.FromFleetspeakProto(
        fleetspeak_utils.GetFleetspeakPendingMessages(
            str(args.client_id),
            offset=args.offset,
            limit=args.limit,
            want_data=args.want_data))
