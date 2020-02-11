#!/usr/bin/env python
"""A module with API handlers related to the timeline colllection."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Optional
from typing import Text

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import body
from grr_response_proto.api import timeline_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow


class ApiGetCollectedTimelineArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the arguments of timeline exporter arguments."""

  protobuf = timeline_pb2.ApiGetCollectedTimelineArgs
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
  ]


class ApiGetCollectedTimelineHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the timeline exporter."""

  args_type = ApiGetCollectedTimelineArgs

  def Handle(
      self,
      args,
      token = None,
  ):
    """Handles requests for the timeline export API call."""
    client_id = str(args.client_id)
    flow_id = str(args.flow_id)

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    if flow_obj.flow_class_name != timeline.TimelineFlow.__name__:
      message = "Flow '{}' is not a timeline flow".format(flow_id)
      raise ValueError(message)

    if args.format == ApiGetCollectedTimelineArgs.Format.BODY:  # pytype: disable=attribute-error
      return self._StreamBody(client_id=client_id, flow_id=flow_id)
    if args.format == ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED:  # pytype: disable=attribute-error
      return self._StreamRawGzchunked(client_id=client_id, flow_id=flow_id)

    message = "Incorrect timeline export format: {}".format(args.format)
    raise ValueError(message)

  def _StreamBody(
      self,
      client_id,
      flow_id,
  ):
    entries = timeline.Entries(client_id=client_id, flow_id=flow_id)
    content = body.Stream(entries)

    filename = "timeline_{}.body".format(flow_id)
    return api_call_handler_base.ApiBinaryStream(filename, content)

  def _StreamRawGzchunked(
      self,
      client_id,
      flow_id,
  ):
    content = timeline.Blobs(client_id=client_id, flow_id=flow_id)

    filename = "timeline_{}.gzchunked".format(flow_id)
    return api_call_handler_base.ApiBinaryStream(filename, content)
