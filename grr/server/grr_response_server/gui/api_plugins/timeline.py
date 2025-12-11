#!/usr/bin/env python
"""A module with API handlers related to the timeline colllection."""
from collections.abc import Iterator
from typing import Optional

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import body
from grr_response_core.lib.util import chunked
from grr_response_proto import objects_pb2
from grr_response_proto.api import timeline_pb2
from grr_response_server import data_store
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow


class ApiTimelineBodyOpts(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the body exporter options."""

  protobuf = timeline_pb2.ApiTimelineBodyOpts
  rdf_deps = []


class ApiGetCollectedTimelineArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the arguments of timeline exporter arguments."""

  protobuf = timeline_pb2.ApiGetCollectedTimelineArgs
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
      ApiTimelineBodyOpts,
  ]


class ApiGetCollectedHuntTimelinesArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the arguments of time hunt timeline exporter."""

  protobuf = timeline_pb2.ApiGetCollectedHuntTimelinesArgs
  rdf_deps = [
      ApiTimelineBodyOpts,
  ]


class ApiGetCollectedTimelineHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the timeline exporter."""

  proto_args_type = timeline_pb2.ApiGetCollectedTimelineArgs

  def Handle(
      self,
      args: timeline_pb2.ApiGetCollectedTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    """Handles requests for the timeline export API call."""
    client_id = args.client_id
    flow_id = args.flow_id

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    if flow_obj.flow_class_name != timeline.TimelineFlow.__name__:
      message = "Flow '{}' is not a timeline flow".format(flow_id)
      raise ValueError(message)

    if args.format == timeline_pb2.ApiGetCollectedTimelineArgs.BODY:
      return self._StreamBody(args)
    if args.format == timeline_pb2.ApiGetCollectedTimelineArgs.RAW_GZCHUNKED:
      return self._StreamRawGzchunked(client_id=client_id, flow_id=flow_id)

    message = "Incorrect timeline export format: {}".format(args.format)
    raise ValueError(message)

  def _StreamBody(
      self,
      args: timeline_pb2.ApiGetCollectedTimelineArgs,
  ) -> api_call_handler_base.ApiBinaryStream:
    client_id = args.client_id
    flow_id = args.flow_id

    opts = body.Opts()
    opts.timestamp_subsecond_precision = (
        args.body_opts.timestamp_subsecond_precision
    )
    opts.backslash_escape = args.body_opts.backslash_escape
    opts.carriage_return_escape = args.body_opts.carriage_return_escape
    opts.non_printable_escape = args.body_opts.non_printable_escape

    if args.body_opts.HasField("inode_ntfs_file_reference_format"):
      # If the field is set explicitly, we respect the choice no matter what
      # filesystem we detected.
      if args.body_opts.inode_ntfs_file_reference_format:
        opts.inode_format = body.Opts.InodeFormat.NTFS_FILE_REFERENCE
    else:
      fstype = timeline.FilesystemType(client_id=client_id, flow_id=flow_id)
      if fstype is not None and fstype.lower() == "ntfs":
        opts.inode_format = body.Opts.InodeFormat.NTFS_FILE_REFERENCE

    entries = timeline.ProtoEntries(client_id=client_id, flow_id=flow_id)
    content = body.Stream(entries, opts=opts)

    filename = "timeline_{}.body".format(flow_id)
    return api_call_handler_base.ApiBinaryStream(filename, content)

  def _StreamRawGzchunked(
      self,
      client_id: str,
      flow_id: str,
  ) -> api_call_handler_base.ApiBinaryStream:
    content = timeline.Blobs(client_id=client_id, flow_id=flow_id)
    content = map(chunked.Encode, content)

    filename = "timeline_{}.gzchunked".format(flow_id)
    return api_call_handler_base.ApiBinaryStream(filename, content)


class ApiGetCollectedHuntTimelinesHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the hunt timelines exporter."""

  proto_args_type = timeline_pb2.ApiGetCollectedHuntTimelinesArgs

  def __init__(self):
    super().__init__()
    self._handler = ApiGetCollectedTimelineHandler()

  def Handle(
      self,
      args: timeline_pb2.ApiGetCollectedHuntTimelinesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    """Handles requests for the hunt timelines export API call."""
    hunt_id = args.hunt_id

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    if hunt_obj.args.standard.flow_name != timeline.TimelineFlow.__name__:
      message = f"Hunt '{hunt_id}' is not a timeline hunt"
      raise ValueError(message)

    fmt = args.format
    if (
        fmt != timeline_pb2.ApiGetCollectedTimelineArgs.RAW_GZCHUNKED
        and fmt != timeline_pb2.ApiGetCollectedTimelineArgs.BODY
    ):
      message = f"Incorrect timeline export format: {fmt}"
      raise ValueError(message)

    filename = f"timelines_{hunt_id}.zip"
    content = self._GenerateArchive(args)
    return api_call_handler_base.ApiBinaryStream(filename, content)

  def _GenerateArchive(
      self,
      args: timeline_pb2.ApiGetCollectedHuntTimelinesArgs,
  ) -> Iterator[bytes]:
    zipgen = utils.StreamingZipGenerator()
    yield from self._GenerateHuntTimelines(args, zipgen)
    yield zipgen.Close()

  def _GenerateHuntTimelines(
      self,
      args: timeline_pb2.ApiGetCollectedHuntTimelinesArgs,
      zipgen: utils.StreamingZipGenerator,
  ) -> Iterator[bytes]:

    offset = 0
    while True:
      flows = data_store.REL_DB.ReadHuntFlows(
          args.hunt_id, offset, _FLOW_BATCH_SIZE
      )

      client_ids = [flow.client_id for flow in flows]
      client_snapshots = data_store.REL_DB.MultiReadClientSnapshot(client_ids)

      for flow in flows:
        snapshot = client_snapshots[flow.client_id]
        filename = _GetHuntTimelineFilename(snapshot, args.format)

        subargs = timeline_pb2.ApiGetCollectedTimelineArgs()
        subargs.client_id = flow.client_id
        subargs.flow_id = flow.flow_id
        subargs.format = args.format
        subargs.body_opts.CopyFrom(args.body_opts)

        yield zipgen.WriteFileHeader(filename)
        yield from map(zipgen.WriteFileChunk, self._GenerateTimeline(subargs))
        yield zipgen.WriteFileFooter()

      if len(flows) < _FLOW_BATCH_SIZE:
        break

  def _GenerateTimeline(
      self,
      args: timeline_pb2.ApiGetCollectedTimelineArgs,
  ) -> Iterator[bytes]:
    return self._handler.Handle(args).GenerateContent()


def _GetHuntTimelineFilename(
    snapshot: objects_pb2.ClientSnapshot,
    fmt: timeline_pb2.ApiGetCollectedTimelineArgs.Format,
) -> str:
  """Computes a timeline filename for the given client snapshot."""
  client_id = snapshot.client_id
  fqdn = snapshot.knowledge_base.fqdn

  if fmt == timeline_pb2.ApiGetCollectedTimelineArgs.RAW_GZCHUNKED:
    return f"{client_id}_{fqdn}.gzchunked"
  if fmt == timeline_pb2.ApiGetCollectedTimelineArgs.BODY:
    return f"{client_id}_{fqdn}.body"

  raise ValueError(f"Unsupported file format: '{fmt}'")


_FLOW_BATCH_SIZE = 32_768  # A number of flows to fetch in a database call.
