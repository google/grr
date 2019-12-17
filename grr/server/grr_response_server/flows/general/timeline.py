#!/usr/bin/env python
"""A module that defines the timeline flow."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Iterator
from typing import Text

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import objects as rdf_objects


class TimelineFlow(flow_base.FlowBase):
  """A flow mixin wrapping the timeline client action."""

  friendly_name = "Timeline"
  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_timeline.TimelineArgs

  def Start(self):
    super(TimelineFlow, self).Start()
    self.CallClient(
        action_cls=server_stubs.Timeline,
        request=self.args,
        next_state=self.Process.__name__)

  def Process(
      self,
      responses,
  ):
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    for response in responses:
      self.SendReply(response)


def Entries(
    client_id,
    flow_id,
):
  """Retrieves timeline entries for the specified flow.

  Args:
    client_id: An identifier of a client of the flow to retrieve the blobs for.
    flow_id: An identifier of the flow to retrieve the blobs for.

  Returns:
    An iterator over timeline entries for the specified flow.
  """
  blobs = Blobs(client_id, flow_id)
  return rdf_timeline.TimelineEntry.DeserializeStream(blobs)


def Blobs(
    client_id,
    flow_id,
):
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
      count=_READ_FLOW_RESULTS_COUNT)

  for result in results:
    payload = result.payload

    if not isinstance(payload, rdf_timeline.TimelineResult):
      message = "Unexpected timeline result of type '{}'".format(type(payload))
      raise TypeError(message)

    for entry_batch_blob_id in payload.entry_batch_blob_ids:
      blob_id = rdf_objects.BlobID(entry_batch_blob_id)
      blob = data_store.BLOBS.ReadBlob(blob_id)

      if blob is None:
        message = "Reference to non-existing blob: '{}'".format(blob_id)
        raise AssertionError(message)

      yield blob


# Number of results should never be big, usually no more than 2 or 3 results
# per flow (because each result is just a block of references to much bigger
# blobs). Just to be on the safe side, we use a number two orders of magnitude
# bigger.
_READ_FLOW_RESULTS_COUNT = 1024
