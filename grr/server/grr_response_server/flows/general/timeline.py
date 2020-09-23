#!/usr/bin/env python
# Lint as: python3
"""A module that defines the timeline flow."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Iterator
from typing import Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import timeline
from grr_response_proto import timeline_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.rdfvalues import objects as rdf_objects


class TimelineFlow(flow_base.FlowBase):
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

  def Start(self) -> None:
    super(TimelineFlow, self).Start()

    if not self.args.root:
      raise ValueError("The timeline root directory not specified")

    if not self.client_info.timeline_btime_support:
      self.Log("Collecting file birth time is not supported on this client.")

    self.CallClient(
        action_cls=server_stubs.Timeline,
        request=self.args,
        next_state=self.Process.__name__)

  def Process(
      self,
      responses: flow_responses.Responses[rdf_timeline.TimelineResult],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    blob_ids = []
    for response in responses:
      for blob_id in response.entry_batch_blob_ids:
        blob_ids.append(rdf_objects.BlobID(blob_id))

    data_store.BLOBS.WaitForBlobs(blob_ids, timeout=_BLOB_STORE_TIMEOUT)

    for response in responses:
      self.SendReply(response)


def ProtoEntries(
    client_id: Text,
    flow_id: Text,
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
    client_id: Text,
    flow_id: Text,
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

# An amount of time to wait for the blobs with timeline entries to appear in the
# blob store. This is needed, because blobs are not guaranteed to be processed
# before the flow receives results from the client. This delay should usually be
# very quick, so the timeout used here should be more than enough.
_BLOB_STORE_TIMEOUT = rdfvalue.Duration.From(30, rdfvalue.SECONDS)
