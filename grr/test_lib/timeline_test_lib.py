#!/usr/bin/env python
"""Testing utilities for the timeline flow."""
from collections.abc import Sequence
import random
from typing import Optional

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_proto import flows_pb2
from grr_response_proto import timeline_pb2
from grr_response_server import data_store
from grr_response_server.flows.general import timeline


def WriteTimeline(
    client_id: str,
    entries: Sequence[timeline_pb2.TimelineEntry],
    hunt_id: Optional[str] = None,
) -> str:
  """Writes a timeline to the database (as fake flow result).

  Args:
    client_id: An identifier of the client for which the flow ran.
    entries: A sequence of timeline entries produced by the flow run.
    hunt_id: An (optional) identifier of a hunt the flows belong to.

  Returns:
    An identifier of the flow.
  """
  if hunt_id is None:
    flow_id = "".join(random.choice("ABCDEF") for _ in range(8))
  else:
    flow_id = hunt_id

  flow_obj = flows_pb2.Flow()
  flow_obj.flow_id = flow_id
  flow_obj.client_id = client_id
  flow_obj.flow_class_name = timeline.TimelineFlow.__name__
  if hunt_id is not None:
    flow_obj.parent_hunt_id = hunt_id
  data_store.REL_DB.WriteFlowObject(flow_obj)

  blobs = list(rdf_timeline.SerializeTimelineEntryStream(entries))
  blob_ids = data_store.BLOBS.WriteBlobsWithUnknownHashes(blobs)

  result = timeline_pb2.TimelineResult()
  result.entry_batch_blob_ids.extend(list(map(bytes, blob_ids)))

  flow_result = flows_pb2.FlowResult()
  flow_result.client_id = client_id
  flow_result.flow_id = flow_id
  if hunt_id is not None:
    flow_result.hunt_id = hunt_id
  flow_result.payload.Pack(result)

  data_store.REL_DB.WriteFlowResults([flow_result])

  return flow_id
