#!/usr/bin/env python
"""API handlers for accessing and searching clients and managing labels."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from future.builtins import str
from future.moves.urllib import parse as urlparse
from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues

import ipaddress

from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import compatibility
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
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui.api_plugins import stats as api_stats
from grr_response_server.rdfvalues import objects as rdf_objects


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
      admin_pb2.ListClientsRequest(client_ids=list(iterkeys(id_map))))
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

    super(ApiClientId, self).__init__(initializer=initializer)

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

  def InitFromClientObject(self, client_obj):

    # TODO(amoser): Deprecate all urns.
    self.urn = client_obj.client_id

    self.client_id = client_obj.client_id

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

  def InitFromClientInfo(self, client_info):
    self.InitFromClientObject(client_info.last_snapshot)

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

  def Handle(self, args, token=None):
    end = args.count or db.MAX_COUNT

    keywords = compatibility.ShlexSplit(args.query)

    api_clients = []

    index = client_index.ClientIndex()

    # LookupClients returns a sorted list of client ids.
    clients = index.LookupClients(keywords)[args.offset:args.offset + end]

    client_infos = data_store.REL_DB.MultiReadClientFullInfo(clients)
    for client_info in itervalues(client_infos):
      api_clients.append(ApiClient().InitFromClientInfo(client_info))

    UpdateClientsFromFleetspeak(api_clients)
    return ApiSearchClientsResult(items=api_clients)


class ApiLabelsRestrictedSearchClientsHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders results of a client search."""

  args_type = ApiSearchClientsArgs
  result_type = ApiSearchClientsResult

  def __init__(self, labels_whitelist=None, labels_owners_whitelist=None):
    super(ApiLabelsRestrictedSearchClientsHandler, self).__init__()

    self.labels_whitelist = set(labels_whitelist or [])
    self.labels_owners_whitelist = set(labels_owners_whitelist or [])

  def _CheckClientLabels(self, client_obj, token=None):
    for label in client_obj.GetLabels():
      if (label.name in self.labels_whitelist and
          label.owner in self.labels_owners_whitelist):
        return True

    return False

  def _VerifyLabels(self, labels):
    for label in labels:
      if (label.name in self.labels_whitelist and
          label.owner in self.labels_owners_whitelist):
        return True
    return False

  def Handle(self, args, token=None):
    if args.count:
      end = args.offset + args.count
      # Read <count> clients ahead in case some of them fail to open / verify.
      batch_size = end + args.count
    else:
      end = db.MAX_COUNT
      batch_size = end

    keywords = compatibility.ShlexSplit(args.query)
    api_clients = []

    index = client_index.ClientIndex()

    # TODO(amoser): We could move the label verification into the
    # database making this method more efficient. Label restrictions
    # should be on small subsets though so this might not be worth
    # it.
    all_client_ids = set()
    for label in self.labels_whitelist:
      label_filter = ["label:" + label] + keywords
      all_client_ids.update(index.LookupClients(label_filter))

    index = 0
    for cid_batch in collection.Batch(sorted(all_client_ids), batch_size):
      client_infos = data_store.REL_DB.MultiReadClientFullInfo(cid_batch)

      for _, client_info in sorted(iteritems(client_infos)):
        if not self._VerifyLabels(client_info.labels):
          continue
        if index >= args.offset and index < end:
          api_clients.append(ApiClient().InitFromClientInfo(client_info))
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

  def Handle(self, args, token=None):
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

  def Handle(self, args, token=None):
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

    api_client = ApiClient().InitFromClientInfo(info)
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

  def Handle(self, args, token=None):
    end_time = args.end or rdfvalue.RDFDatetime.Now()
    start_time = args.start or end_time - rdfvalue.Duration.From(
        3, rdfvalue.MINUTES)
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

  def Handle(self, args, token=None):
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

  def Handle(self, args, token=None):
    flow_id = flow.StartFlow(
        flow_cls=discovery.Interrogate, client_id=str(args.client_id))

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

  def Handle(self, args, token=None):
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

    expected_flow_name = compatibility.GetName(discovery.Interrogate)
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

  def Handle(self, args, token=None):
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

  def Handle(self, args, token=None):
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

  def Handle(self, args, token=None):
    for api_client_id in args.client_ids:
      cid = str(api_client_id)
      data_store.REL_DB.AddClientLabels(cid, token.username, args.labels)
      idx = client_index.ClientIndex()
      idx.AddClientLabels(cid, args.labels)


class ApiRemoveClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiRemoveClientsLabelsArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiRemoveClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Remove labels from a given client."""

  args_type = ApiRemoveClientsLabelsArgs

  def RemoveClientLabels(self, client, labels_names):
    """Removes labels with given names from a given client object."""

    affected_owners = set()
    for label in client.GetLabels():
      if label.name in labels_names and label.owner != "GRR":
        affected_owners.add(label.owner)

    for owner in affected_owners:
      client.RemoveLabels(labels_names, owner=owner)

  def Handle(self, args, token=None):
    for client_id in args.client_ids:
      cid = str(client_id)
      data_store.REL_DB.RemoveClientLabels(cid, token.username, args.labels)
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

  def Handle(self, args, token=None):
    labels = data_store.REL_DB.ReadAllClientLabels()

    label_objects = []
    for name in set(l.name for l in labels):
      label_objects.append(rdf_objects.ClientLabel(name=name))

    return ApiListClientsLabelsResult(
        items=sorted(label_objects, key=lambda l: l.name))


class ApiListKbFieldsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListKbFieldsResult


class ApiListKbFieldsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients knowledge base fields."""

  result_type = ApiListKbFieldsResult

  def Handle(self, args, token=None):
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

  def Handle(self, args, token=None):
    result = ApiListClientActionRequestsResult()

    request_cache = {}

    for r in data_store.REL_DB.ReadAllClientActionRequests(str(args.client_id)):
      stub = action_registry.ACTION_STUB_BY_ID[r.action_identifier]
      client_action = compatibility.GetName(stub)

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

  def Handle(self, args, token=None):
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
