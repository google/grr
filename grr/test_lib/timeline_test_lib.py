#!/usr/bin/env python
"""Testing utilities for the timeline flow."""
import random
from typing import Optional
from typing import Sequence
from typing import Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_server import data_store
from grr_response_server.flows.general import timeline
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


def WriteTimeline(
    client_id: Text,
    entries: Sequence[rdf_timeline.TimelineEntry],
    hunt_id: Optional[Text] = None,
) -> Text:
  """Writes a timeline to the database (as fake flow result).

  Args:
    client_id: An identifier of the client for which the flow ran.
    entries: A sequence of timeline entries produced by the flow run.
    hunt_id: An (optional) identifier of a hunt the flows belong to.

  Returns:
    An identifier of the flow.
  """
  flow_id = "".join(random.choice("ABCDEF") for _ in range(8))

  flow_obj = rdf_flow_objects.Flow()
  flow_obj.flow_id = flow_id
  flow_obj.client_id = client_id
  flow_obj.flow_class_name = timeline.TimelineFlow.__name__
  flow_obj.create_time = rdfvalue.RDFDatetime.Now()
  flow_obj.parent_hunt_id = hunt_id
  data_store.REL_DB.WriteFlowObject(flow_obj)

  blobs = list(rdf_timeline.TimelineEntry.SerializeStream(iter(entries)))
  blob_ids = data_store.BLOBS.WriteBlobsWithUnknownHashes(blobs)

  result = rdf_timeline.TimelineResult()
  result.entry_batch_blob_ids = [blob_id.AsBytes() for blob_id in blob_ids]

  flow_result = rdf_flow_objects.FlowResult()
  flow_result.client_id = client_id
  flow_result.flow_id = flow_id
  flow_result.payload = result

  data_store.REL_DB.WriteFlowResults([flow_result])

  return flow_id
