#!/usr/bin/env python
"""A module that defines the timeline flow."""

from collections.abc import Iterator
from typing import Optional

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_timeline
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import timeline
from grr_response_proto import flows_pb2
from grr_response_proto import timeline_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_path
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg.action import get_filesystem_timeline_pb2 as rrg_get_filesystem_timeline_pb2


class TimelineFlow(
    flow_base.FlowBase[
        timeline_pb2.TimelineArgs,
        flows_pb2.DefaultFlowStore,
        timeline_pb2.TimelineProgress,
    ]
):
  """A flow recursively collecting stat information under the given directory.

  The timeline flow collects stat information for every file under the given
  directory (including all subfolders recursively). Unlike the file finder flow,
  the search does not have any depth limit and is extremely fast—it should
  complete the scan within minutes on an average machine.

  The results can be then exported in multiple formats (e.g. BODY [1]) and
  analyzed locally using existing forensic tools.

  Note that the flow is optimized for collecting stat data only. If any extra
  information about the file (e.g. its content or hash) is needed, other more
  flows (like the file finder flow) should be utilized instead.

  [1]: https://wiki.sleuthkit.org/index.php?title=Body_file
  """

  friendly_name = "Timeline"
  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_timeline.TimelineArgs
  progress_type = rdf_timeline.TimelineProgress
  result_types = (rdf_timeline.TimelineResult,)

  proto_args_type = timeline_pb2.TimelineArgs
  proto_progress_type = timeline_pb2.TimelineProgress
  proto_result_types = (timeline_pb2.TimelineResult,)

  only_protos_allowed = True

  def Start(self) -> None:
    super().Start()

    if not self.proto_args.root:
      raise ValueError("The timeline root directory not specified")

    if not self.client_info.timeline_btime_support:
      self.Log("Collecting file birth time is not supported on this client.")

    self.progress = timeline_pb2.TimelineProgress()

    if self.rrg_support:
      root = rrg_fs_pb2.Path()
      root.raw_bytes = self.proto_args.root

      if not rrg_path.PurePath.For(self.rrg_os_type, root).is_absolute():
        raise ValueError(f"Non-absolute path: {root.raw_bytes.decode()}")

      action = rrg_stubs.GetFilesystemTimeline()
      action.args.root.CopyFrom(root)
      action.Call(self.HandleRRGGetFilesystemTimeline)
    else:
      self.CallClientProto(
          action_cls=server_stubs.Timeline,
          action_args=self.proto_args,
          next_state=self.Process.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def Process(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    unpacked_responses: list[timeline_pb2.TimelineResult] = []
    for response_any in responses:
      response = timeline_pb2.TimelineResult()
      response.ParseFromString(response_any.value)
      unpacked_responses.append(response)

    blob_ids = []
    for response in unpacked_responses:
      for blob_id in response.entry_batch_blob_ids:
        blob_ids.append(models_blobs.BlobID(blob_id))

    data_store.BLOBS.WaitForBlobs(blob_ids, timeout=_BLOB_STORE_TIMEOUT)

    for response in unpacked_responses:
      self.SendReplyProto(response)
      self.progress.total_entry_count += response.entry_count

  @flow_base.UseProto2AnyResponses
  def HandleRRGGetFilesystemTimeline(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      message = f"Timeline collection failure: {responses.status}"
      raise flow_base.FlowError(message)

    blob_ids: list[models_blobs.BlobID] = []
    flow_results: list[timeline_pb2.TimelineResult] = []

    # TODO: Add support for streaming responses in RRG.
    for response in responses:
      result = rrg_get_filesystem_timeline_pb2.Result()
      result.ParseFromString(response.value)

      blob_ids.append(models_blobs.BlobID(result.blob_sha256))

      flow_result = timeline_pb2.TimelineResult()
      flow_result.entry_batch_blob_ids.append(result.blob_sha256)
      flow_result.entry_count = result.entry_count
      flow_results.append(flow_result)

      self.progress.total_entry_count += result.entry_count

    data_store.BLOBS.WaitForBlobs(blob_ids, timeout=_BLOB_STORE_TIMEOUT)

    for flow_result in flow_results:
      self.SendReplyProto(flow_result)

  # TODO: Remove this method.
  def GetProgress(self) -> rdf_timeline.TimelineProgress:
    return mig_timeline.ToRDFTimelineProgress(self.progress)

  def GetProgressProto(self) -> timeline_pb2.TimelineProgress:
    return self.progress


def ProtoEntries(
    client_id: str,
    flow_id: str,
) -> Iterator[timeline_pb2.TimelineEntry]:
  """Retrieves timeline entries for the specified flow.

  Args:
    client_id: An identifier of a client of the flow to retrieve the blobs for.
    flow_id: An identifier of the flow to retrieve the blobs for.

  Returns:
    An iterator over timeline entries protos for the specified flow.
  """
  blobs = Blobs(client_id, flow_id)
  return timeline.DeserializeTimelineEntryProtoStream(blobs)


def Blobs(
    client_id: str,
    flow_id: str,
) -> Iterator[bytes]:
  """Retrieves timeline blobs for the specified flow.

  Args:
    client_id: An identifier of a client of the flow to retrieve the blobs for.
    flow_id: An identifier of the flow to retrieve the blobs for.

  Yields:
    Blobs of the timeline data in the gzchunked format for the specified flow.
  """
  results = data_store.REL_DB.ReadFlowResults(
      client_id=client_id,
      flow_id=flow_id,
      offset=0,
      count=_READ_FLOW_MAX_RESULTS_COUNT,
  )
  results = [mig_flow_objects.ToRDFFlowResult(r) for r in results]

  # `_READ_FLOW_MAX_RESULTS_COUNT` is far too much than we should ever get. If
  # we really got this many results that it means this assumption is not correct
  # and we should fail loudly to investigate this issue.
  if len(results) >= _READ_FLOW_MAX_RESULTS_COUNT:
    message = f"Unexpected number of timeline results: {len(results)}"
    raise AssertionError(message)

  for result in results:
    payload = result.payload

    if not isinstance(payload, rdf_timeline.TimelineResult):
      message = "Unexpected timeline result of type '{}'".format(type(payload))
      raise TypeError(message)

    for entry_batch_blob_id in payload.entry_batch_blob_ids:
      blob_id = models_blobs.BlobID(entry_batch_blob_id)
      blob = data_store.BLOBS.ReadBlob(blob_id)

      if blob is None:
        message = "Reference to non-existing blob: '{}'".format(blob_id)
        raise AssertionError(message)

      yield blob


def FilesystemType(client_id: str, flow_id: str) -> Optional[str]:
  """Retrieves a filesystem type information of the specified timeline flow.

  Args:
    client_id: An identifier of a client of the flow.
    flow_id: An identifier of the flow.

  Returns:
    A string representing filesystem type if available.
  """
  results = data_store.REL_DB.ReadFlowResults(
      client_id=client_id, flow_id=flow_id, offset=0, count=1
  )
  results = [mig_flow_objects.ToRDFFlowResult(r) for r in results]

  if not results:
    return None

  result = results[0].payload
  if not isinstance(result, rdf_timeline.TimelineResult):
    raise TypeError(f"Unexpected timeline result of type '{type(result)}'")

  return result.filesystem_type


# Number of results should never be big, usually no more than 2 or 3 results
# per flow (because each result is just a block of references to much bigger
# blobs). Just to be on the safe side, we use a number two orders of magnitude
# bigger.
_READ_FLOW_MAX_RESULTS_COUNT = 1024

# An amount of time to wait for the blobs with timeline entries to appear in the
# blob store. This is needed, because blobs are not guaranteed to be processed
# before the flow receives results from the client. This delay should usually be
# very quick, so the timeout used here should be more than enough.
_BLOB_STORE_TIMEOUT = rdfvalue.Duration.From(30, rdfvalue.SECONDS)
