#!/usr/bin/env python
# Lint as: python3
"""A module with API handlers related to the timeline colllection."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Iterator
from typing import Optional
from typing import Text

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import body
from grr_response_core.lib.util import chunked
from grr_response_proto.api import timeline_pb2
from grr_response_server import data_store
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_call_context
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


class ApiGetCollectedHuntTimelinesArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the arguments of time hunt timeline exporter."""

  protobuf = timeline_pb2.ApiGetCollectedHuntTimelinesArgs
  rdf_deps = []


class ApiGetCollectedTimelineHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the timeline exporter."""

  args_type = ApiGetCollectedTimelineArgs

  def Handle(
      self,
      args: ApiGetCollectedTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
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
      client_id: Text,
      flow_id: Text,
  ) -> api_call_handler_base.ApiBinaryStream:
    entries = timeline.ProtoEntries(client_id=client_id, flow_id=flow_id)
    content = body.Stream(entries)

    filename = "timeline_{}.body".format(flow_id)
    return api_call_handler_base.ApiBinaryStream(filename, content)

  def _StreamRawGzchunked(
      self,
      client_id: Text,
      flow_id: Text,
  ) -> api_call_handler_base.ApiBinaryStream:
    content = timeline.Blobs(client_id=client_id, flow_id=flow_id)
    content = map(chunked.Encode, content)

    filename = "timeline_{}.gzchunked".format(flow_id)
    return api_call_handler_base.ApiBinaryStream(filename, content)


class ApiGetCollectedHuntTimelinesHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the hunt timelines exporter."""

  args_type = ApiGetCollectedHuntTimelinesArgs

  def __init__(self):
    super().__init__()
    self._handler = ApiGetCollectedTimelineHandler()

  def Handle(
      self,
      args: ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    """Handles requests for the hunt timelines export API call."""
    hunt_id = str(args.hunt_id)

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    if hunt_obj.args.standard.flow_name != timeline.TimelineFlow.__name__:
      message = f"Hunt '{hunt_id}' is not a timeline hunt"
      raise ValueError(message)

    # TODO(hanuszczak): Enum-related attribute errors can by bypassed by using
    # raw protobuf enums.
    # pytype: disable=attribute-error
    if (args.format != ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED and
        args.format != ApiGetCollectedTimelineArgs.Format.BODY):
      message = f"Incorrect timeline export format: {args.format}"
      raise ValueError(message)
    # pytype: enable=attribute-error

    filename = f"timelines_{hunt_id}.zip"
    content = self._Generate(hunt_id, args.format)
    return api_call_handler_base.ApiBinaryStream(filename, content)

  def _Generate(
      self,
      hunt_id: Text,
      fmt: rdf_structs.EnumNamedValue,
  ) -> Iterator[bytes]:
    zipgen = utils.StreamingZipGenerator()
    yield from self._GenerateTimelines(hunt_id, fmt, zipgen)
    yield zipgen.Close()

  def _GenerateTimelines(
      self,
      hunt_id: Text,
      fmt: rdf_structs.EnumNamedValue,
      zipgen: utils.StreamingZipGenerator,
  ) -> Iterator[bytes]:
    offset = 0
    while True:
      flows = data_store.REL_DB.ReadHuntFlows(hunt_id, offset, _FLOW_BATCH_SIZE)

      client_ids = [flow.client_id for flow in flows]
      client_snapshots = data_store.REL_DB.MultiReadClientSnapshot(client_ids)

      client_fqdns = {
          client_id: snapshot.knowledge_base.fqdn
          for client_id, snapshot in client_snapshots.items()
      }

      for flow in flows:
        client_id = flow.client_id
        flow_id = flow.flow_id
        fqdn = client_fqdns[client_id]

        yield from self._GenerateTimeline(client_id, flow_id, fqdn, fmt, zipgen)

      if len(flows) < _FLOW_BATCH_SIZE:
        break

  def _GenerateTimeline(
      self,
      client_id: Text,
      flow_id: Text,
      fqdn: Text,
      fmt: rdf_structs.EnumNamedValue,
      zipgen: utils.StreamingZipGenerator,
  ) -> Iterator[bytes]:
    args = ApiGetCollectedTimelineArgs()
    args.client_id = client_id
    args.flow_id = flow_id
    args.format = fmt

    if fmt == ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED:  # pytype: disable=attribute-error
      filename = f"{client_id}_{fqdn}.gzchunked"
    elif fmt == ApiGetCollectedTimelineArgs.Format.BODY:  # pytype: disable=attribute-error
      filename = f"{client_id}_{fqdn}.body"
    else:
      raise AssertionError()

    yield zipgen.WriteFileHeader(filename)

    for chunk in self._handler.Handle(args).GenerateContent():
      yield zipgen.WriteFileChunk(chunk)

    yield zipgen.WriteFileFooter()


_FLOW_BATCH_SIZE = 32_768  # A number of flows to fetch in a database call.
