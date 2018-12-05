#!/usr/bin/env python
"""API handlers for accessing and searching clients and managing labels."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import shlex
import sys


from future.moves.urllib import parse as urlparse
from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues
import ipaddr

from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import compatibility
from grr_response_proto.api import client_pb2
from grr_response_server import aff4
from grr_response_server import aff4_flows
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import events
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import flow
from grr_response_server import ip_resolver
from grr_response_server import queue_manager
from grr_response_server import timeseries
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import standard
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.flows.general import audit
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

  def __init__(self, initializer=None, age=None):
    if isinstance(initializer, rdf_client.ClientURN):
      initializer = initializer.Basename()

    super(ApiClientId, self).__init__(initializer=initializer, age=age)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      re_match = aff4_grr.VFSGRRClient.CLIENT_ID_RE.match(self._value)
      if not re_match:
        raise ValueError("Invalid client id: %s" % utils.SmartStr(self._value))

  def ToClientURN(self):
    if not self._value:
      raise ValueError("Can't call ToClientURN() on an empty client id.")

    return rdf_client.ClientURN(self._value)


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

  def InitFromAff4Object(self, client_obj, include_metadata=True):
    # TODO(amoser): Deprecate all urns.
    self.urn = client_obj.urn

    self.client_id = client_obj.urn.Basename()

    self.agent_info = client_obj.Get(client_obj.Schema.CLIENT_INFO)
    self.hardware_info = client_obj.Get(client_obj.Schema.HARDWARE_INFO)
    self.os_info = rdf_client.Uname(
        system=client_obj.Get(client_obj.Schema.SYSTEM),
        release=client_obj.Get(client_obj.Schema.OS_RELEASE),
        # TODO(user): Check if ProtoString.Validate should be fixed
        # to do an isinstance() check on a value. Is simple type
        # equality check used there for performance reasons?
        version=utils.SmartStr(
            client_obj.Get(client_obj.Schema.OS_VERSION, "")),
        kernel=client_obj.Get(client_obj.Schema.KERNEL),
        machine=client_obj.Get(client_obj.Schema.ARCH),
        fqdn=(client_obj.Get(client_obj.Schema.FQDN) or
              client_obj.Get(client_obj.Schema.HOSTNAME)),
        install_date=client_obj.Get(client_obj.Schema.INSTALL_DATE))
    self.knowledge_base = client_obj.Get(client_obj.Schema.KNOWLEDGE_BASE)
    self.memory_size = client_obj.Get(client_obj.Schema.MEMORY_SIZE)

    self.first_seen_at = client_obj.Get(client_obj.Schema.FIRST_SEEN)

    if include_metadata:
      ping = client_obj.Get(client_obj.Schema.PING)
      if ping:
        self.last_seen_at = ping

      booted = client_obj.Get(client_obj.Schema.LAST_BOOT_TIME)
      if booted:
        self.last_booted_at = booted

      clock = client_obj.Get(client_obj.Schema.CLOCK)
      if clock:
        self.last_clock = clock

      last_crash = client_obj.Get(client_obj.Schema.LAST_CRASH)
      if last_crash is not None:
        self.last_crash_at = last_crash.timestamp

      self.fleetspeak_enabled = bool(
          client_obj.Get(client_obj.Schema.FLEETSPEAK_ENABLED))

    self.labels = [
        rdf_objects.ClientLabel(name=l.name, owner=l.owner)
        for l in client_obj.GetLabels()
    ]
    self.interfaces = client_obj.Get(client_obj.Schema.INTERFACES)
    kb = client_obj.Get(client_obj.Schema.KNOWLEDGE_BASE)
    if kb and kb.users:
      self.users = sorted(kb.users, key=lambda user: user.username)
    self.volumes = client_obj.Get(client_obj.Schema.VOLUMES)

    type_obj = client_obj.Get(client_obj.Schema.TYPE)
    if type_obj:
      # Without self.Set self.age would reference "age" attribute instead of a
      # protobuf field.
      self.Set("age", type_obj.age)

    self.cloud_instance = client_obj.Get(client_obj.Schema.CLOUD_INSTANCE)
    return self

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

    # TODO(amoser): This should be removed in favor of a timestamp field.
    # Without self.Set self.age would reference "age" attribute instead of a
    # protobuf field.
    self.Set("age", client_obj.timestamp)

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
        client=rdf_objects.ClientReference(
            client_id=utils.SmartStr(self.client_id)))


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
    end = args.count or sys.maxsize

    keywords = shlex.split(args.query)

    api_clients = []

    if data_store.RelationalDBReadEnabled():
      index = client_index.ClientIndex()

      # LookupClients returns a sorted list of client ids.
      clients = index.LookupClients(keywords)[args.offset:args.offset + end]

      client_infos = data_store.REL_DB.MultiReadClientFullInfo(clients)
      for client_info in itervalues(client_infos):
        api_clients.append(ApiClient().InitFromClientInfo(client_info))

    else:
      index = client_index.CreateClientIndex(token=token)

      result_urns = sorted(
          index.LookupClients(keywords))[args.offset:args.offset + end]

      result_set = aff4.FACTORY.MultiOpen(result_urns, token=token)

      for child in sorted(result_set):
        api_clients.append(ApiClient().InitFromAff4Object(child))

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
      end = sys.maxsize
      batch_size = end

    keywords = shlex.split(args.query)
    api_clients = []

    if data_store.RelationalDBReadEnabled():
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

    else:
      index = client_index.CreateClientIndex(token=token)
      all_urns = set()
      for label in self.labels_whitelist:
        label_filter = ["label:" + label] + keywords
        all_urns.update(index.LookupClients(label_filter))

      all_objs = aff4.FACTORY.MultiOpen(
          all_urns, aff4_type=aff4_grr.VFSGRRClient, token=token)

      index = 0
      for client_obj in sorted(all_objs):
        if not self._CheckClientLabels(client_obj):
          continue
        if index >= args.offset and index < end:
          api_clients.append(ApiClient().InitFromAff4Object(client_obj))

        index += 1
        if index >= end:
          break

    UpdateClientsFromFleetspeak(api_clients)
    return ApiSearchClientsResult(items=api_clients)


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
    if not args.timestamp:
      age = rdfvalue.RDFDatetime.Now()
    else:
      age = rdfvalue.RDFDatetime(args.timestamp)
    api_client = None
    if data_store.RelationalDBReadEnabled():
      client_id = unicode(args.client_id)
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
    else:
      client = aff4.FACTORY.Open(
          args.client_id.ToClientURN(),
          aff4_type=aff4_grr.VFSGRRClient,
          age=age,
          token=token)
      api_client = ApiClient().InitFromAff4Object(client)
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
    start_time = args.start or end_time - rdfvalue.Duration("3m")
    diffs_only = args.mode == args.Mode.DIFF

    items = []

    if data_store.RelationalDBReadEnabled():
      client_id = unicode(args.client_id)
      history = data_store.REL_DB.ReadClientSnapshotHistory(
          client_id, timerange=(start_time, end_time))

      for client in history[::-1]:
        items.append(ApiClient().InitFromClientObject(client))
    else:
      all_clients = aff4.FACTORY.OpenDiscreteVersions(
          args.client_id.ToClientURN(),
          mode="r",
          age=(start_time.AsMicrosecondsSinceEpoch(),
               end_time.AsMicrosecondsSinceEpoch()),
          diffs_only=diffs_only,
          token=token)

      for fd in all_clients:
        items.append(ApiClient().InitFromAff4Object(fd, include_metadata=False))

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
    if data_store.RelationalDBReadEnabled():
      # TODO(amoser): Again, this is rather inefficient,if we moved
      # this call to the datastore we could make it much
      # faster. However, there is a chance that this will not be
      # needed anymore once we use the relational db everywhere, let's
      # decide later.
      client_id = unicode(args.client_id)
      history = data_store.REL_DB.ReadClientSnapshotHistory(client_id)
      times = [h.timestamp for h in history]
    else:
      fd = aff4.FACTORY.Open(
          args.client_id.ToClientURN(),
          mode="r",
          age=aff4.ALL_TIMES,
          token=token)

      type_values = list(fd.GetValuesForAttribute(fd.Schema.TYPE))
      times = sorted([t.age for t in type_values], reverse=True)

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
    if data_store.RelationalDBFlowsEnabled():
      flow_id = flow.StartFlow(
          flow_cls=discovery.Interrogate, client_id=unicode(args.client_id))

      # TODO(user): don't encode client_id inside the operation_id, but
      # rather have it as a separate field.
      return ApiInterrogateClientResult(
          operation_id="%s/%s" % (args.client_id, flow_id))
    else:
      flow_urn = flow.StartAFF4Flow(
          client_id=args.client_id.ToClientURN(),
          flow_name=aff4_flows.Interrogate.__name__,
          token=token)

      return ApiInterrogateClientResult(operation_id=str(flow_urn))


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
    if data_store.RelationalDBFlowsEnabled():
      client_id = unicode(args.client_id)
      flow_id = unicode(args.operation_id)
      # TODO(user): test both exception scenarios below.
      try:
        flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      except db.UnknownFlowError:
        raise InterrogateOperationNotFoundError(
            "Operation with id %s not found" % args.operation_id)

      if flow_obj.flow_name != compatibility.GetName(discovery.Interrogate):
        raise InterrogateOperationNotFoundError(
            "Operation with id %s not found" % args.operation_id)

      complete = flow_obj.flow_state != flow_obj.FlowState.RUNNING
    else:
      try:
        flow_obj = aff4.FACTORY.Open(
            args.operation_id, aff4_type=aff4_flows.Interrogate, token=token)

        complete = not flow_obj.GetRunner().IsRunning()
      except aff4.InstantiationError:
        raise InterrogateOperationNotFoundError(
            "Operation with id %s not found" % args.operation_id)

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
  return ip_str, ipaddr.IPAddress(ip_str)


class ApiGetLastClientIPAddressHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the last ip a client used for communication with the server."""

  args_type = ApiGetLastClientIPAddressArgs
  result_type = ApiGetLastClientIPAddressResult

  def Handle(self, args, token=None):
    client_id = unicode(args.client_id)

    if data_store.RelationalDBReadEnabled():
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
    else:
      client = aff4.FACTORY.Open(
          args.client_id.ToClientURN(),
          aff4_type=aff4_grr.VFSGRRClient,
          token=token)
      if client.Get(client.Schema.FLEETSPEAK_ENABLED):
        ip_str, ipaddr_obj = _GetAddrFromFleetspeak(client_id)
      else:
        ip_str = client.Get(client.Schema.CLIENT_IP)
        if ip_str:
          ipaddr_obj = ipaddr.IPAddress(ip_str)
        else:
          ipaddr_obj = None

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
    if data_store.RelationalDBReadEnabled():
      crashes = data_store.REL_DB.ReadClientCrashInfoHistory(
          unicode(args.client_id))
      total_count = len(crashes)
      result = api_call_handler_utils.FilterList(
          crashes, args.offset, count=args.count, filter_value=args.filter)
    else:
      crashes = aff4_grr.VFSGRRClient.CrashCollectionForCID(
          args.client_id.ToClientURN())

      total_count = len(crashes)
      result = api_call_handler_utils.FilterCollection(
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
    audit_description = ",".join([
        token.username + u"." + utils.SmartUnicode(name) for name in args.labels
    ])
    audit_events = []

    try:
      index = client_index.CreateClientIndex(token=token)
      client_objs = aff4.FACTORY.MultiOpen(
          [cid.ToClientURN() for cid in args.client_ids],
          aff4_type=aff4_grr.VFSGRRClient,
          mode="rw",
          token=token)
      for client_obj in client_objs:
        if data_store.RelationalDBWriteEnabled():
          cid = client_obj.urn.Basename()
          try:
            data_store.REL_DB.AddClientLabels(cid, token.username, args.labels)
            idx = client_index.ClientIndex()
            idx.AddClientLabels(cid, args.labels)
          except db.UnknownClientError:
            # TODO(amoser): Remove after data migration.
            pass

        client_obj.AddLabels(args.labels)
        index.AddClient(client_obj)
        client_obj.Close()

        audit_events.append(
            rdf_events.AuditEvent(
                user=token.username,
                action="CLIENT_ADD_LABEL",
                flow_name="handler.ApiAddClientsLabelsHandler",
                client=client_obj.urn,
                description=audit_description))
    finally:
      events.Events.PublishMultipleEvents({audit.AUDIT_EVENT: audit_events},
                                          token=token)


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
    audit_description = ",".join([
        token.username + u"." + utils.SmartUnicode(name) for name in args.labels
    ])
    audit_events = []

    try:
      index = client_index.CreateClientIndex(token=token)
      client_objs = aff4.FACTORY.MultiOpen(
          [cid.ToClientURN() for cid in args.client_ids],
          aff4_type=aff4_grr.VFSGRRClient,
          mode="rw",
          token=token)
      for client_obj in client_objs:
        if data_store.RelationalDBWriteEnabled():
          cid = client_obj.urn.Basename()
          data_store.REL_DB.RemoveClientLabels(cid, token.username, args.labels)
          labels_to_remove = set(args.labels)
          existing_labels = data_store.REL_DB.ReadClientLabels(cid)
          for label in existing_labels:
            labels_to_remove.discard(label.name)
          if labels_to_remove:
            idx = client_index.ClientIndex()
            idx.RemoveClientLabels(cid, labels_to_remove)

        index.RemoveClientLabels(client_obj)
        self.RemoveClientLabels(client_obj, args.labels)
        index.AddClient(client_obj)
        client_obj.Close()

        audit_events.append(
            rdf_events.AuditEvent(
                user=token.username,
                action="CLIENT_REMOVE_LABEL",
                flow_name="handler.ApiRemoveClientsLabelsHandler",
                client=client_obj.urn,
                description=audit_description))
    finally:
      events.Events.PublishMultipleEvents({audit.AUDIT_EVENT: audit_events},
                                          token=token)


class ApiListClientsLabelsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListClientsLabelsResult
  rdf_deps = [
      rdf_objects.ClientLabel,
  ]


class ApiListClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients labels."""

  result_type = ApiListClientsLabelsResult

  def HandleLegacy(self, args, token=None):
    labels_index = aff4.FACTORY.Create(
        standard.LabelSet.CLIENT_LABELS_URN,
        standard.LabelSet,
        mode="r",
        token=token)
    label_objects = []
    for label in labels_index.ListLabels():
      label_objects.append(rdf_objects.ClientLabel(name=label))

    return ApiListClientsLabelsResult(items=label_objects)

  def HandleRelationalDB(self, args, token=None):
    labels = data_store.REL_DB.ReadAllClientLabels()

    label_objects = []
    for name in set(l.name for l in labels):
      label_objects.append(rdf_objects.ClientLabel(name=name))

    return ApiListClientsLabelsResult(
        items=sorted(label_objects, key=lambda l: l.name))

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled():
      return self.HandleRelationalDB(args, token=token)
    else:
      return self.HandleLegacy(args, token=token)


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
    if data_store.RelationalDBFlowsEnabled():
      return self._HandleRelational(args)
    else:
      return self._HandleAFF4(args, token=token)

  def _HandleAFF4(self, args, token=None):
    manager = queue_manager.QueueManager(token=token)

    result = ApiListClientActionRequestsResult()
    # Passing "limit" argument explicitly, as Query returns just 1 request
    # by default.
    for task in manager.Query(
        args.client_id.ToClientURN(), limit=self.__class__.REQUESTS_NUM_LIMIT):
      request = ApiClientActionRequest(
          leased_until=task.leased_until,
          session_id=task.session_id,
          client_action=task.name)

      if args.fetch_responses:
        res = []
        for r in data_store.DB.ReadResponsesForRequestId(
            task.session_id, task.request_id):
          # Clear out some internal fields.
          r.task_id = None
          r.auth_state = None
          r.name = None
          res.append(r)

        request.responses = res

      result.items.append(request)

    return result

  def _HandleRelational(self, args):
    result = ApiListClientActionRequestsResult()

    for task in data_store.REL_DB.ReadClientMessages(unicode(args.client_id)):
      request = ApiClientActionRequest(
          leased_until=task.leased_until,
          session_id=task.session_id,
          client_action=task.name)
      result.items.append(request)

      if args.fetch_responses:
        # TODO(amoser): This is slightly wasteful but this api method is not
        # used too frequently.
        requests_responses = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
            unicode(args.client_id), task.session_id.Basename())

        for req, responses in requests_responses:
          if req.request_id == task.request_id:
            res = []
            for resp_id in sorted(responses):
              m = responses[resp_id].AsLegacyGrrMessage()
              # TODO(amoser): Once AFF4 is gone, leaving this as 0 is ok.
              if m.args_age == 0:
                m.args_age = None
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
      start_time = end_time - rdfvalue.Duration("30m")

    fd = aff4.FACTORY.Create(
        args.client_id.ToClientURN().Add("stats"),
        aff4_type=aff4_stats.ClientStats,
        mode="r",
        token=token,
        age=(start_time, end_time))

    stat_values = list(fd.GetValuesForAttribute(fd.Schema.STATS))
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
        points.append((stat_value.bytes_received, stat_value.age))
      elif args.metric == args.Metric.NETWORK_BYTES_SENT:
        points.append((stat_value.bytes_sent, stat_value.age))
      elif args.metric == args.Metric.MEMORY_PERCENT:
        points.append((stat_value.memory_percent, stat_value.age))
      elif args.metric == args.Metric.MEMORY_RSS_SIZE:
        points.append((stat_value.RSS_size, stat_value.age))
      elif args.metric == args.Metric.MEMORY_VMS_SIZE:
        points.append((stat_value.VMS_size, stat_value.age))
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
      sampling_interval = rdfvalue.Duration.FromSeconds(
          ((end_time - start_time).seconds // self.MAX_SAMPLES) or 1)
      if args.metric in self.GAUGE_METRICS:
        mode = timeseries.NORMALIZE_MODE_GAUGE
      else:
        mode = timeseries.NORMALIZE_MODE_COUNTER

      ts.Normalize(sampling_interval, start_time, end_time, mode=mode)

    result = ApiGetClientLoadStatsResult()
    for value, timestamp in ts.data:
      dp = api_stats.ApiStatsStoreMetricDataPoint(
          timestamp=timestamp, value=value)
      result.data_points.append(dp)

    return result
