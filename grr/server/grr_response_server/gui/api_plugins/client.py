#!/usr/bin/env python
"""API handlers for accessing and searching clients and managing labels."""

import ipaddress
import re
import shlex
from typing import Optional, Sequence
from urllib import parse as urlparse

from google.protobuf import message as proto2_message
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import precondition
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import client_pb2
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import flow
from grr_response_server import ip_resolver
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.models import clients as models_clients
from grr_response_server.rdfvalues import objects as rdf_objects
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2


def UpdateClientsFromFleetspeak(
    clients: Sequence[client_pb2.ApiClient],
) -> None:
  """Updates ApiClient records to include info from Fleetspeak."""
  if not fleetspeak_connector.CONN or not fleetspeak_connector.CONN.outgoing:
    # FS not configured, or an outgoing connection is otherwise unavailable.
    return
  id_map = {}
  for client in clients:
    id_map[fleetspeak_utils.GRRIDToFleetspeakID(client.client_id)] = client
  if not id_map:
    return
  res = fleetspeak_connector.CONN.outgoing.ListClients(
      admin_pb2.ListClientsRequest(client_ids=list(id_map.keys()))
  )
  for read in res.clients:
    api_client = id_map[read.client_id]
    api_client.last_seen_at = fleetspeak_utils.TSToRDFDatetime(
        read.last_contact_time
    ).AsMicrosecondsSinceEpoch()
    api_client.last_clock = fleetspeak_utils.TSToRDFDatetime(
        read.last_clock
    ).AsMicrosecondsSinceEpoch()


class InterrogateOperationNotFoundError(
    api_call_handler_base.ResourceNotFoundError
):
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
      rdf_client_fs.Volume,
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
  proto_args_type = client_pb2.ApiSearchClientsArgs
  proto_result_type = client_pb2.ApiSearchClientsResult

  def Handle(
      self,
      args: client_pb2.ApiSearchClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiSearchClientsResult:
    end = args.count or db.MAX_COUNT

    keywords = shlex.split(args.query)

    api_clients = []

    index = client_index.ClientIndex()

    # LookupClients returns a sorted list of client ids.
    clients = index.LookupClients(keywords)[args.offset : args.offset + end]

    client_infos = data_store.REL_DB.MultiReadClientFullInfo(clients)
    for client_id, client_info in client_infos.items():
      api_clients.append(
          models_clients.ApiClientFromClientFullInfo(client_id, client_info)
      )

    UpdateClientsFromFleetspeak(api_clients)
    return client_pb2.ApiSearchClientsResult(items=api_clients)


class ApiLabelsRestrictedSearchClientsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Renders results of a client search."""

  args_type = ApiSearchClientsArgs
  result_type = ApiSearchClientsResult
  proto_args_type = client_pb2.ApiSearchClientsArgs
  proto_result_type = client_pb2.ApiSearchClientsResult

  def __init__(self, allow_labels=None, allow_labels_owners=None):
    super().__init__()

    self.allow_labels = set(allow_labels or [])
    self.allow_labels_owners = set(allow_labels_owners or [])

  def _VerifyLabels(self, labels):
    for label in labels:
      if (
          label.name in self.allow_labels
          and label.owner in self.allow_labels_owners
      ):
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
          api_clients.append(
              models_clients.ApiClientFromClientFullInfo(client_id, client_info)
          )
        index += 1
        if index >= end:
          UpdateClientsFromFleetspeak(api_clients)
          return client_pb2.ApiSearchClientsResult(items=api_clients)

    UpdateClientsFromFleetspeak(api_clients)
    return client_pb2.ApiSearchClientsResult(items=api_clients)


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
  proto_args_type = client_pb2.ApiVerifyAccessArgs
  proto_result_type = client_pb2.ApiVerifyAccessResult

  def Handle(self, args, context=None):
    return client_pb2.ApiVerifyAccessResult()


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
  proto_args_type = client_pb2.ApiGetClientArgs
  proto_result_type = client_pb2.ApiClient

  def Handle(
      self,
      args: client_pb2.ApiGetClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiClient:
    client_id = args.client_id
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    if info is None:
      raise api_call_handler_base.ResourceNotFoundError()

    if args.HasField("timestamp"):
      # Assume that a snapshot for this particular timestamp exists.
      timestamp = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.timestamp
      )
      snapshots = data_store.REL_DB.ReadClientSnapshotHistory(
          client_id, timerange=(timestamp, timestamp)
      )

      if snapshots:
        info.last_snapshot.CopyFrom(snapshots[0])
        info.last_startup_info.CopyFrom(info.last_snapshot.startup_info)

    api_client = models_clients.ApiClientFromClientFullInfo(client_id, info)
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
  proto_args_type = client_pb2.ApiGetClientVersionsArgs
  proto_result_type = client_pb2.ApiGetClientVersionsResult

  def Handle(
      self,
      args: client_pb2.ApiGetClientVersionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiGetClientVersionsResult:
    if args.end:
      end_time = rdfvalue.RDFDatetime().FromMicrosecondsSinceEpoch(args.end)
    else:
      end_time = rdfvalue.RDFDatetime.Now()

    if args.start:
      start_time = rdfvalue.RDFDatetime().FromMicrosecondsSinceEpoch(args.start)
    else:
      start_time = end_time - rdfvalue.Duration.From(3, rdfvalue.MINUTES)
    start_time = max(start_time, data_store.REL_DB.MinTimestamp())

    items = []

    history = data_store.REL_DB.ReadClientSnapshotHistory(
        args.client_id, timerange=(start_time, end_time)
    )
    labels = data_store.REL_DB.ReadClientLabels(args.client_id)

    for snapshot in history[::-1]:
      c = models_clients.ApiClientFromClientSnapshot(snapshot)
      # ClientSnapshot does not contain label information, so
      # c.labels should be empty at this point.
      c.labels.extend(labels)
      items.append(c)

    return client_pb2.ApiGetClientVersionsResult(items=items)


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
  proto_args_type = client_pb2.ApiGetClientVersionTimesArgs
  proto_result_type = client_pb2.ApiGetClientVersionTimesResult

  def Handle(
      self,
      args: client_pb2.ApiGetClientVersionTimesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiGetClientVersionTimesResult:
    # TODO(amoser): Again, this is rather inefficient,if we moved
    # this call to the datastore we could make it much
    # faster. However, there is a chance that this will not be
    # needed anymore once we use the relational db everywhere, let's
    # decide later.
    history = data_store.REL_DB.ReadClientSnapshotHistory(args.client_id)
    times = [h.timestamp for h in history]

    return client_pb2.ApiGetClientVersionTimesResult(times=times)


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
  proto_args_type = client_pb2.ApiInterrogateClientArgs
  proto_result_type = client_pb2.ApiInterrogateClientResult

  def Handle(
      self,
      args: client_pb2.ApiInterrogateClientArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiInterrogateClientResult:
    assert context is not None

    flow_id = flow.StartFlow(
        flow_cls=discovery.Interrogate,
        client_id=args.client_id,
        creator=context.username,
    )

    # TODO(user): don't encode client_id inside the operation_id, but
    # rather have it as a separate field.
    return client_pb2.ApiInterrogateClientResult(operation_id=flow_id)


class ApiGetInterrogateOperationStateArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetInterrogateOperationStateArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiGetInterrogateOperationStateResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetInterrogateOperationStateResult


class ApiGetInterrogateOperationStateHandler(
    api_call_handler_base.ApiCallHandler
):
  """Retrieves the state of the interrogate operation."""

  args_type = ApiGetInterrogateOperationStateArgs
  result_type = ApiGetInterrogateOperationStateResult
  proto_args_type = client_pb2.ApiGetInterrogateOperationStateArgs
  proto_result_type = client_pb2.ApiGetInterrogateOperationStateResult

  def Handle(
      self,
      args: client_pb2.ApiGetInterrogateOperationStateArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiGetInterrogateOperationStateResult:
    client_id = str(args.client_id)
    flow_id = str(args.operation_id)

    precondition.ValidateClientId(client_id)
    precondition.ValidateFlowId(flow_id)

    # TODO(user): test both exception scenarios below.
    try:
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    except db.UnknownFlowError as e:
      raise InterrogateOperationNotFoundError(
          "Operation with id %s not found" % args.operation_id
      ) from e

    expected_flow_name = discovery.Interrogate.__name__
    if flow_obj.flow_class_name != expected_flow_name:
      raise InterrogateOperationNotFoundError(
          "Operation with id %s not found" % args.operation_id
      )

    complete = flow_obj.flow_state != flows_pb2.Flow.FlowState.RUNNING

    result = client_pb2.ApiGetInterrogateOperationStateResult()
    if complete:
      result.state = (
          client_pb2.ApiGetInterrogateOperationStateResult.State.FINISHED
      )
    else:
      result.state = (
          client_pb2.ApiGetInterrogateOperationStateResult.State.RUNNING
      )

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
          client_ids=[fleetspeak_utils.GRRIDToFleetspeakID(client_id)]
      )
  )
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
  proto_args_type = client_pb2.ApiGetLastClientIPAddressArgs
  proto_result_type = client_pb2.ApiGetLastClientIPAddressResult

  def Handle(
      self,
      args: client_pb2.ApiGetLastClientIPAddressArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiGetLastClientIPAddressResult:
    ip_str, ipaddr_obj = _GetAddrFromFleetspeak(args.client_id)
    status, info = ip_resolver.IP_RESOLVER.RetrieveIPInfo(ipaddr_obj)

    return client_pb2.ApiGetLastClientIPAddressResult(
        ip=ip_str, info=info, status=status
    )


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
  proto_args_type = client_pb2.ApiListClientCrashesArgs
  proto_result_type = client_pb2.ApiListClientCrashesResult

  def Handle(
      self,
      args: client_pb2.ApiListClientCrashesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiListClientCrashesResult:
    crashes = data_store.REL_DB.ReadClientCrashInfoHistory(args.client_id)
    total_count = len(crashes)
    result = api_call_handler_utils.FilterList(
        crashes, args.offset, count=args.count, filter_value=args.filter
    )

    return client_pb2.ApiListClientCrashesResult(
        items=result,
        total_count=total_count,
    )


class ApiAddClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiAddClientsLabelsArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiAddClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Adds labels to a given client."""

  args_type = ApiAddClientsLabelsArgs
  proto_args_type = client_pb2.ApiAddClientsLabelsArgs

  def Handle(
      self,
      args: client_pb2.ApiAddClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    assert context is not None

    client_ids = args.client_ids
    labels = args.labels

    data_store.REL_DB.MultiAddClientLabels(client_ids, context.username, labels)

    idx = client_index.ClientIndex()
    idx.MultiAddClientLabels(client_ids, args.labels)

    # Reset foreman rules check so active hunts can match against the new data
    data_store.REL_DB.MultiWriteClientMetadata(
        client_ids,
        last_foreman=data_store.REL_DB.MinTimestamp(),
    )


class ApiRemoveClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiRemoveClientsLabelsArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiRemoveClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Remove labels from a given client."""

  args_type = ApiRemoveClientsLabelsArgs
  proto_args_type = client_pb2.ApiRemoveClientsLabelsArgs

  def Handle(
      self,
      args: client_pb2.ApiRemoveClientsLabelsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    assert context is not None

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
  proto_result_type = client_pb2.ApiListClientsLabelsResult

  def Handle(
      self,
      args: Optional[proto2_message.Message] = None,  # Unused
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiListClientsLabelsResult:
    labels = data_store.REL_DB.ReadAllClientLabels()

    label_objects = []
    for name in labels:
      label_objects.append(objects_pb2.ClientLabel(name=name))

    return client_pb2.ApiListClientsLabelsResult(
        items=sorted(label_objects, key=lambda l: l.name)
    )


class ApiListKbFieldsResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiListKbFieldsResult


class ApiListKbFieldsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients knowledge base fields."""

  result_type = ApiListKbFieldsResult
  proto_result_type = client_pb2.ApiListKbFieldsResult

  def Handle(self, args, context=None):
    # TODO: Add a proto function counterpart.
    fields = rdf_client.KnowledgeBase().GetKbFieldNames()
    return client_pb2.ApiListKbFieldsResult(items=sorted(fields))


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
  proto_args_type = client_pb2.ApiKillFleetspeakArgs

  def Handle(
      self,
      args: client_pb2.ApiKillFleetspeakArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.KillFleetspeak(args.client_id, args.force)


class ApiRestartFleetspeakGrrServiceArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiRestartFleetspeakGrrServiceArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiRestartFleetspeakGrrServiceHandler(
    api_call_handler_base.ApiCallHandler
):
  """Restarts the GRR fleetspeak service on the given client."""

  args_type = ApiRestartFleetspeakGrrServiceArgs
  proto_args_type = client_pb2.ApiRestartFleetspeakGrrServiceArgs

  def Handle(
      self,
      args: client_pb2.ApiRestartFleetspeakGrrServiceArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.RestartFleetspeakGrrService(args.client_id)


class ApiDeleteFleetspeakPendingMessagesArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiDeleteFleetspeakPendingMessagesArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiDeleteFleetspeakPendingMessagesHandler(
    api_call_handler_base.ApiCallHandler
):
  """Deletes pending fleetspeak messages for the given client."""

  args_type = ApiDeleteFleetspeakPendingMessagesArgs
  proto_args_type = client_pb2.ApiDeleteFleetspeakPendingMessagesArgs

  def Handle(
      self,
      args: client_pb2.ApiDeleteFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    _CheckFleetspeakConnection()
    fleetspeak_utils.DeleteFleetspeakPendingMessages(args.client_id)


class ApiGetFleetspeakPendingMessageCountArgs(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetFleetspeakPendingMessageCountArgs
  rdf_deps = [
      ApiClientId,
  ]


class ApiGetFleetspeakPendingMessageCountResult(rdf_structs.RDFProtoStruct):
  protobuf = client_pb2.ApiGetFleetspeakPendingMessageCountResult


class ApiGetFleetspeakPendingMessageCountHandler(
    api_call_handler_base.ApiCallHandler
):
  """Returns the number of fleetspeak messages pending for the given client."""

  args_type = ApiGetFleetspeakPendingMessageCountArgs
  result_type = ApiGetFleetspeakPendingMessageCountResult
  proto_args_type = client_pb2.ApiGetFleetspeakPendingMessageCountArgs
  proto_result_type = client_pb2.ApiGetFleetspeakPendingMessageCountResult

  def Handle(
      self,
      args: client_pb2.ApiGetFleetspeakPendingMessageCountArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiGetFleetspeakPendingMessageCountResult:
    _CheckFleetspeakConnection()
    return client_pb2.ApiGetFleetspeakPendingMessageCountResult(
        count=fleetspeak_utils.GetFleetspeakPendingMessageCount(args.client_id)
    )


class ApiFleetspeakAddress(rdf_structs.RDFProtoStruct):
  """Mirrors the fleetspeak proto `common_pb2.Address`."""

  protobuf = client_pb2.ApiFleetspeakAddress
  rdf_deps = [
      ApiClientId,
  ]


class ApiFleetspeakAnnotations(rdf_structs.RDFProtoStruct):
  """Mirrors the proto `fleetspeak.Annotations`."""

  class Entry(rdf_structs.RDFProtoStruct):
    protobuf = client_pb2.ApiFleetspeakAnnotations.Entry

  protobuf = client_pb2.ApiFleetspeakAnnotations
  rdf_deps = [
      Entry,
  ]


class ApiFleetspeakValidationInfo(rdf_structs.RDFProtoStruct):
  """Mirrors the proto `fleetspeak.ValidationInfo`."""

  class Tag(rdf_structs.RDFProtoStruct):
    protobuf = client_pb2.ApiFleetspeakValidationInfo.Tag

  protobuf = client_pb2.ApiFleetspeakValidationInfo
  rdf_deps = [
      Tag,
  ]


class ApiFleetspeakMessageResult(rdf_structs.RDFProtoStruct):
  """Mirrors the proto `fleetspeak.MessageResult`."""

  protobuf = client_pb2.ApiFleetspeakMessageResult
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


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


class ApiGetFleetspeakPendingMessagesHandler(
    api_call_handler_base.ApiCallHandler
):
  """Returns the fleetspeak pending messages for the given client."""

  args_type = ApiGetFleetspeakPendingMessagesArgs
  result_type = ApiGetFleetspeakPendingMessagesResult
  proto_args_type = client_pb2.ApiGetFleetspeakPendingMessagesArgs
  proto_result_type = client_pb2.ApiGetFleetspeakPendingMessagesResult

  def Handle(
      self,
      args: client_pb2.ApiGetFleetspeakPendingMessagesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> client_pb2.ApiGetFleetspeakPendingMessagesResult:
    _CheckFleetspeakConnection()
    return (
        models_clients.ApiGetFleetspeakPendingMessagesResultFromFleetspeakProto(
            fleetspeak_utils.GetFleetspeakPendingMessages(
                str(args.client_id),
                offset=args.offset,
                limit=args.limit,
                want_data=args.want_data,
            )
        )
    )
