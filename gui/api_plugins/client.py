#!/usr/bin/env python
"""API renderers for accessing and searching clients and managing labels."""

import shlex
import sys

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderers
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import client_index
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils

from grr.proto import api_pb2


class ApiClientSearchRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiClientSearchRendererArgs


class ApiClientSearchRenderer(api_call_renderers.ApiCallRenderer):
  """Renders results of a client search."""

  args_type = ApiClientSearchRendererArgs

  def Render(self, args, token=None):
    end = args.count or sys.maxint
    rendered_clients = []

    # An empty query matches all clients, use the universal keyword ".".
    query = args.query or "."
    keywords = shlex.split(query)
    if not keywords:
      raise ValueError("Couldn't parse query string.")

    index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                                aff4_type="ClientIndex",
                                mode="rw",
                                token=token)
    result_urns = sorted(index.LookupClients(keywords),
                         key=str)[args.offset:args.offset + end]
    result_set = aff4.FACTORY.MultiOpen(result_urns, token=token)

    for child in result_set:
      rendered_client = api_aff4_object_renderers.RenderAFF4Object(
          child, [rdfvalue.ApiAFF4ObjectRendererArgs(
              type_info="WITH_TYPES_AND_METADATA")])
      rendered_clients.append(rendered_client)

    return dict(query=args.query,
                offset=args.offset,
                count=len(rendered_clients),
                items=rendered_clients)


class ApiClientSummaryRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiClientSummaryRendererArgs


class ApiClientSummaryRenderer(api_call_renderers.ApiCallRenderer):
  """Renders summary of a given client."""

  args_type = ApiClientSummaryRendererArgs

  def Render(self, args, token=None):
    client = aff4.FACTORY.Open(args.client_id, aff4_type="VFSGRRClient",
                               token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        client, [rdfvalue.ApiAFF4ObjectRendererArgs(
            type_info="WITH_TYPES_AND_METADATA")])


class ApiClientsAddLabelsRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiClientsAddLabelsRendererArgs


class ApiClientsAddLabelsRenderer(api_call_renderers.ApiCallRenderer):
  """Adds labels to a given client."""

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
            rdfvalue.AuditEvent(
                user=token.username, action="CLIENT_ADD_LABEL",
                flow_name="renderer.ApiClientsAddLabelsRenderer",
                client=client_obj.urn, description=audit_description))

      return dict(status="OK")
    finally:
      flow.Events.PublishMultipleEvents({"Audit": audit_events},
                                        token=token)


class ApiClientsRemoveLabelsRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiClientsRemoveLabelsRendererArgs


class ApiClientsRemoveLabelsRenderer(api_call_renderers.ApiCallRenderer):
  """Remove labels from a given client."""

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
        self.RemoveClientLabels(client_obj, args.labels)
        # TODO(user): AddClient doesn't remove labels. Make sure removed labels
        # are actually removed from the index.
        index.AddClient(client_obj)
        client_obj.Close()

        audit_events.append(
            rdfvalue.AuditEvent(
                user=token.username, action="CLIENT_REMOVE_LABEL",
                flow_name="renderer.ApiClientsRemoveLabelsRenderer",
                client=client_obj.urn, description=audit_description))
    finally:
      flow.Events.PublishMultipleEvents({"Audit": audit_events},
                                        token=token)

    return dict(status="OK")


class ApiClientsLabelsListRenderer(api_call_renderers.ApiCallRenderer):
  """Lists all the available clients labels."""

  def Render(self, args, token=None):
    labels_index = aff4.FACTORY.Create(
        aff4.VFSGRRClient.labels_index_urn, "AFF4LabelsIndex",
        mode="rw", token=token)

    rendered_labels = []
    for label in labels_index.ListUsedLabels():
      rendered_labels.append(api_value_renderers.RenderValue(label))

    return dict(labels=sorted(rendered_labels))
