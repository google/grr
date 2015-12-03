#!/usr/bin/env python
"""API handlers for accessing and searching clients and managing labels."""

import shlex
import sys

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import client_index
from grr.lib import flow
from grr.lib import utils

from grr.lib.aff4_objects import standard

from grr.lib.flows.general import filesystem

from grr.lib.rdfvalues import aff4_rdfvalues
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "Clients"


class ApiListClientsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListClientsArgs


class ApiListClientsHandler(api_call_handler_base.ApiCallHandler):
  """Renders results of a client search."""

  category = CATEGORY
  args_type = ApiListClientsArgs

  def Render(self, args, token=None):
    end = args.count or sys.maxint
    rendered_clients = []

    keywords = shlex.split(args.query)

    index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                                aff4_type="ClientIndex",
                                mode="rw",
                                token=token)
    result_urns = sorted(index.LookupClients(keywords),
                         key=str)[args.offset:args.offset + end]
    result_set = aff4.FACTORY.MultiOpen(result_urns, token=token)

    for child in result_set:
      rendered_client = api_aff4_object_renderers.RenderAFF4Object(child)
      rendered_clients.append(rendered_client)

    return dict(query=args.query,
                offset=args.offset,
                count=len(rendered_clients),
                items=rendered_clients)


class ApiGetClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetClientArgs


class ApiGetClientHandler(api_call_handler_base.ApiCallHandler):
  """Renders summary of a given client."""

  category = CATEGORY
  args_type = ApiGetClientArgs

  def Render(self, args, token=None):
    client = aff4.FACTORY.Open(args.client_id, aff4_type="VFSGRRClient",
                               token=token)

    return api_aff4_object_renderers.RenderAFF4Object(client)


class ApiAddClientsLabelsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiAddClientsLabelsArgs


class ApiAddClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Adds labels to a given client."""

  category = CATEGORY
  args_type = ApiAddClientsLabelsArgs
  privileged = True

  def Render(self, args, token=None):
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
          args.client_ids, aff4_type="VFSGRRClient", mode="rw", token=token)
      for client_obj in client_objs:
        client_obj.AddLabels(*args.labels)
        index.AddClient(client_obj)
        client_obj.Close()

        audit_events.append(
            flow.AuditEvent(
                user=token.username, action="CLIENT_ADD_LABEL",
                flow_name="handler.ApiAddClientsLabelsHandler",
                client=client_obj.urn, description=audit_description))

      return dict(status="OK")
    finally:
      flow.Events.PublishMultipleEvents({"Audit": audit_events},
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

  def Render(self, args, token=None):
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
          args.client_ids, aff4_type="VFSGRRClient", mode="rw", token=token)
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
      flow.Events.PublishMultipleEvents({"Audit": audit_events},
                                        token=token)

    return dict(status="OK")


class ApiListClientsLabelsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients labels."""

  category = CATEGORY

  def Render(self, args, token=None):
    labels_index = aff4.FACTORY.Create(standard.LabelSet.CLIENT_LABELS_URN,
                                       "LabelSet",
                                       mode="r",
                                       token=token)
    rendered_labels = []
    for label in labels_index.ListLabels():
      label_object = aff4_rdfvalues.AFF4ObjectLabel(name=label)
      rendered_labels.append(api_value_renderers.RenderValue(label_object))
    return dict(labels=rendered_labels)


class ApiListKbFieldsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all the available clients knowledge base fields."""

  category = CATEGORY

  def Render(self, args, token=None):
    fields = rdf_client.KnowledgeBase().GetKbFieldNames()
    return dict(fields=sorted(fields))


class ApiVfsRefreshOperation(rdf_structs.RDFProtoStruct):
  """ApiVfsRefreshOperation used for updating VFS paths."""
  protobuf = api_pb2.ApiVfsRefreshOperation


class ApiCreateVfsRefreshOperationHandler(
    api_call_handler_base.ApiCallHandler):
  """Creates a new refresh operation for a given VFS path.

  This effectively triggers a refresh of a given VFS path. Refresh status
  can be monitored by polling the returned URL of the operation (not implemented
  yet).
  """

  category = CATEGORY
  args_type = ApiVfsRefreshOperation

  def Render(self, args, token=None):
    aff4_path = args.client_id.Add(args.vfs_path)
    fd = aff4.FACTORY.Open(aff4_path, aff4_type="VFSDirectory", token=token)

    flow_args = filesystem.RecursiveListDirectoryArgs(
        pathspec=fd.real_pathspec,
        max_depth=args.max_depth)

    flow.GRRFlow.StartFlow(client_id=args.client_id,
                           flow_name="RecursiveListDirectory",
                           args=flow_args,
                           notify_to_user=True,
                           token=token)
    return dict(status="OK")
