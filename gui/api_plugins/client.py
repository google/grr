#!/usr/bin/env python
"""API renderers for accessing and searching clients and managing labels."""

import shlex
import sys

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderer_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import client_index
from grr.lib import flow
from grr.lib import utils

from grr.lib.aff4_objects import standard

from grr.lib.rdfvalues import aff4_rdfvalues
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "Clients"


class ApiClientSearchRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientSearchRendererArgs


class ApiClientSearchRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders results of a client search."""

  category = CATEGORY
  args_type = ApiClientSearchRendererArgs

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


class ApiClientSummaryRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientSummaryRendererArgs


class ApiClientSummaryRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders summary of a given client."""

  category = CATEGORY
  args_type = ApiClientSummaryRendererArgs

  def Render(self, args, token=None):
    client = aff4.FACTORY.Open(args.client_id, aff4_type="VFSGRRClient",
                               token=token)

    return api_aff4_object_renderers.RenderAFF4Object(client)


class ApiClientsAddLabelsRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientsAddLabelsRendererArgs


class ApiClientsAddLabelsRenderer(api_call_renderer_base.ApiCallRenderer):
  """Adds labels to a given client."""

  category = CATEGORY
  args_type = ApiClientsAddLabelsRendererArgs
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
                flow_name="renderer.ApiClientsAddLabelsRenderer",
                client=client_obj.urn, description=audit_description))

      return dict(status="OK")
    finally:
      flow.Events.PublishMultipleEvents({"Audit": audit_events},
                                        token=token)


class ApiClientsRemoveLabelsRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientsRemoveLabelsRendererArgs


class ApiClientsRemoveLabelsRenderer(api_call_renderer_base.ApiCallRenderer):
  """Remove labels from a given client."""

  category = CATEGORY
  args_type = ApiClientsRemoveLabelsRendererArgs
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
                flow_name="renderer.ApiClientsRemoveLabelsRenderer",
                client=client_obj.urn, description=audit_description))
    finally:
      flow.Events.PublishMultipleEvents({"Audit": audit_events},
                                        token=token)

    return dict(status="OK")


class ApiClientsLabelsListRenderer(api_call_renderer_base.ApiCallRenderer):
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


class ApiListKbFieldsRenderer(api_call_renderer_base.ApiCallRenderer):
  """Lists all the available clients knowledge base fields."""

  category = CATEGORY

  def Render(self, args, token=None):
    fields = rdf_client.KnowledgeBase().GetKbFieldNames()
    return dict(fields=sorted(fields))
