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
from grr.lib import utils

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


class ApiClientSearchRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientSearchRendererArgs


class ApiClientSearchRenderer(api_call_renderers.ApiCallRenderer):
  """Renders results of a client search."""

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
      rendered_client = api_aff4_object_renderers.RenderAFF4Object(
          child, [api_aff4_object_renderers.ApiAFF4ObjectRendererArgs(
              type_info="WITH_TYPES_AND_METADATA")])
      rendered_clients.append(rendered_client)

    return dict(query=args.query,
                offset=args.offset,
                count=len(rendered_clients),
                items=rendered_clients)


class ApiClientSummaryRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientSummaryRendererArgs


class ApiClientSummaryRenderer(api_call_renderers.ApiCallRenderer):
  """Renders summary of a given client."""

  args_type = ApiClientSummaryRendererArgs

  def Render(self, args, token=None):
    client = aff4.FACTORY.Open(args.client_id, aff4_type="VFSGRRClient",
                               token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        client, [api_aff4_object_renderers.ApiAFF4ObjectRendererArgs(
            type_info="WITH_TYPES_AND_METADATA")])


class ApiClientsAddLabelsRendererArgs(rdf_structs.RDFProtoStruct):
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
            flow.AuditEvent(
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


class ApiFlowStatusRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowStatusRendererArgs


class ApiFlowStatusRenderer(api_call_renderers.ApiCallRenderer):
  """Renders summary of a given flow.

  Only top-level flows can be targeted. Times returned in the response are micro
  seconds since epoch.
  """

  args_type = ApiFlowStatusRendererArgs

  # Make this SetUID, see comment below. Authentication is still required.
  privileged = True

  def Render(self, args, token=None):
    """Render flow status.

    This renderer needs to be setuid because it needs to access any top level
    flow on any client. The ACL model operates at the object level, and doesn't
    give us the ability to target specific attributes of the object. This
    renderer relies on ClientURN and SessionID type validation to check the
    input parameters to avoid allowing arbitrary reads into the client aff4
    space. This renderer filters out only the attributes that are appropriate to
    release without authorization (authentication is still required).

    Args:
      args: ApiFlowStatusRendererArgs object
      token: access token
    Returns:
      dict representing flow state
    Raises:
      ValueError: if there is no flow at the URN
    """
    # args.flow_id looks like aff4:/F:ABCDEF12, convert it into a flow urn for
    # the target client.
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    try:
      flow_obj = aff4.FACTORY.Open(flow_urn, aff4_type="GRRFlow",
                                   token=token)
    except aff4.InstantiationError:
      raise ValueError("No flow object at %s" % flow_urn)

    flow_state = flow_obj.Get(flow_obj.Schema.FLOW_STATE)

    # We expect there is a use case for exposing flow_state.args, but in the
    # interest of exposing the minimum information required, we'll leave it out
    # until there is demonstrated need.
    rdf_result_map = {
        # "args": flow_state.args,
        "backtrace": flow_state.context.backtrace,
        "client_resources": flow_state.context.client_resources,
        "create_time": flow_state.context.create_time,
        "creator": flow_state.context.creator,
        "flow_runner_args": flow_state.context.args,
        "last_update_time": flow_obj.Get(flow_obj.Schema.LAST),
        "network_bytes_sent": flow_state.context.network_bytes_sent,
        "output_urn": flow_state.context.output_urn,
        "session_id": flow_state.context.session_id,
        "state": flow_state.context.state,
        }

    result = {}
    for dest_key, src in rdf_result_map.iteritems():
      result[dest_key] = api_value_renderers.RenderValue(src)

    result["current_state"] = flow_state.context.current_state
    try:
      result_collection = aff4.FACTORY.Open(flow_state.context.output_urn,
                                            aff4_type="RDFValueCollection",
                                            token=token)
      result["result_count"] = len(result_collection)
    except aff4.InstantiationError:
      result["result_count"] = 0

    return result
