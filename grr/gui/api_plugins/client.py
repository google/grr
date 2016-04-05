#!/usr/bin/env python
"""API handlers for accessing and searching clients and managing labels."""

import shlex
import sys

from grr.gui import api_call_handler_base

from grr.lib import aff4
from grr.lib import client_index
from grr.lib import flow
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard

from grr.lib.flows.general import audit

from grr.lib.rdfvalues import aff4_rdfvalues
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "Clients"


class ApiClient(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClient

  def InitFromAff4Object(self, client_obj):
    self.urn = client_obj.urn

    self.agent_info = client_obj.Get(client_obj.Schema.CLIENT_INFO)
    self.hardware_info = client_obj.Get(client_obj.Schema.HARDWARE_INFO)
    self.os_info = rdf_client.Uname(
        system=client_obj.Get(client_obj.Schema.SYSTEM),
        node=client_obj.Get(client_obj.Schema.HOSTNAME),
        release=client_obj.Get(client_obj.Schema.OS_RELEASE),
        # TODO(user): Check if ProtoString.Validate should be fixed
        # to do an isinstance() check on a value. Is simple type
        # equality check used there for performance reasons?
        version=utils.SmartStr(
            client_obj.Get(client_obj.Schema.OS_VERSION, "")),
        kernel=client_obj.Get(client_obj.Schema.KERNEL),
        machine=client_obj.Get(client_obj.Schema.ARCH),
        fqdn=client_obj.Get(client_obj.Schema.FQDN),
        install_date=client_obj.Get(client_obj.Schema.INSTALL_DATE)
        )

    self.first_seen_at = client_obj.Get(client_obj.Schema.FIRST_SEEN)
    self.last_seen_at = client_obj.Get(client_obj.Schema.PING)
    self.last_booted_at = client_obj.Get(client_obj.Schema.LAST_BOOT_TIME)
    self.last_clock = client_obj.Get(client_obj.Schema.CLOCK)
    last_crash = client_obj.Get(client_obj.Schema.LAST_CRASH)
    if last_crash is not None:
      self.last_crash_at = last_crash.timestamp

    self.labels = client_obj.GetLabels()
    self.interfaces = client_obj.Get(client_obj.Schema.LAST_INTERFACES)
    kb = client_obj.Get(client_obj.Schema.KNOWLEDGE_BASE)
    self.users = kb and kb.users or []
    self.volumes = client_obj.Get(client_obj.Schema.VOLUMES)

    return self


class ApiSearchClientsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiSearchClientsArgs


class ApiSearchClientsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiSearchClientsResult


class ApiSearchClientsHandler(api_call_handler_base.ApiCallHandler):
  """Renders results of a client search."""

  category = CATEGORY

  args_type = ApiSearchClientsArgs
  result_type = ApiSearchClientsResult

  def Handle(self, args, token=None):
    end = args.count or sys.maxint

    keywords = shlex.split(args.query)

    index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                                aff4_type="ClientIndex",
                                mode="rw",
                                token=token)
    result_urns = sorted(index.LookupClients(keywords),
                         key=str)[args.offset:args.offset + end]
    result_set = aff4.FACTORY.MultiOpen(result_urns, token=token)

    api_clients = []
    for child in result_set:
      api_clients.append(ApiClient().InitFromAff4Object(child))

    return ApiSearchClientsResult(items=api_clients)


class ApiGetClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetClientArgs


class ApiGetClientResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetClientResult


class ApiGetClientHandler(api_call_handler_base.ApiCallHandler):
  """Renders summary of a given client."""

  category = CATEGORY

  args_type = ApiGetClientArgs
  result_type = ApiGetClientResult

  def Handle(self, args, token=None):
    client = aff4.FACTORY.Open(args.client_id,
                               aff4_type=aff4_grr.VFSGRRClient.__name__,
                               token=token)

    return ApiGetClientResult(
        client=ApiClient().InitFromAff4Object(client))


class ApiAddClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiAddClientsLabelsArgs


class ApiAddClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Adds labels to a given client."""

  category = CATEGORY
  args_type = ApiAddClientsLabelsArgs
  privileged = True

  def Handle(self, args, token=None):
    audit_description = ",".join(
        [token.username + u"." + utils.SmartUnicode(name)
         for name in args.labels])
    audit_events = []

    try:
      index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                                  aff4_type="ClientIndex",
                                  mode="rw",
                                  token=token)
      client_objs = aff4.FACTORY.MultiOpen(
          args.client_ids, aff4_type=aff4_grr.VFSGRRClient.__name__,
          mode="rw", token=token)
      for client_obj in client_objs:
        client_obj.AddLabels(*args.labels)
        index.AddClient(client_obj)
        client_obj.Close()

        audit_events.append(
            flow.AuditEvent(
                user=token.username, action="CLIENT_ADD_LABEL",
                flow_name="handler.ApiAddClientsLabelsHandler",
                client=client_obj.urn, description=audit_description))
    finally:
      flow.Events.PublishMultipleEvents({audit.AUDIT_EVENT: audit_events},
                                        token=token)


class ApiRemoveClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiRemoveClientsLabelsArgs


class ApiRemoveClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Remove labels from a given client."""

  category = CATEGORY
  args_type = ApiRemoveClientsLabelsArgs
  privileged = True

  def RemoveClientLabels(self, client, labels_names):
    """Removes labels with given names from a given client object."""

    affected_owners = set()
    for label in client.GetLabels():
      if label.name in labels_names and label.owner != "GRR":
        affected_owners.add(label.owner)

    for owner in affected_owners:
      client.RemoveLabels(*labels_names, owner=owner)

  def Handle(self, args, token=None):
    audit_description = ",".join(
        [token.username + u"." + utils.SmartUnicode(name)
         for name in args.labels])
    audit_events = []

    try:
      index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                                  aff4_type="ClientIndex",
                                  mode="rw",
                                  token=token)
      client_objs = aff4.FACTORY.MultiOpen(
          args.client_ids, aff4_type=aff4_grr.VFSGRRClient.__name__,
          mode="rw", token=token)
      for client_obj in client_objs:
        index.RemoveClientLabels(client_obj)
        self.RemoveClientLabels(client_obj, args.labels)
        index.AddClient(client_obj)
        client_obj.Close()

        audit_events.append(
            flow.AuditEvent(
                user=token.username, action="CLIENT_REMOVE_LABEL",
                flow_name="handler.ApiRemoveClientsLabelsHandler",
                client=client_obj.urn, description=audit_description))
    finally:
      flow.Events.PublishMultipleEvents({audit.AUDIT_EVENT: audit_events},
                                        token=token)


class ApiListClientsLabelsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListClientsLabelsResult


class ApiListClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients labels."""

  category = CATEGORY
  result_type = ApiListClientsLabelsResult

  def Handle(self, args, token=None):
    labels_index = aff4.FACTORY.Create(standard.LabelSet.CLIENT_LABELS_URN,
                                       "LabelSet",
                                       mode="r",
                                       token=token)
    label_objects = []
    for label in labels_index.ListLabels():
      label_objects.append(aff4_rdfvalues.AFF4ObjectLabel(name=label))

    return ApiListClientsLabelsResult(items=label_objects)


class ApiListKbFieldsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListKbFieldsResult


class ApiListKbFieldsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients knowledge base fields."""

  category = CATEGORY
  result_type = ApiListKbFieldsResult

  def Handle(self, args, token=None):
    fields = rdf_client.KnowledgeBase().GetKbFieldNames()
    return ApiListKbFieldsResult(items=sorted(fields))

