#!/usr/bin/env python
# Lint as: python3
"""A module with flow class calling the osquery client action."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.util import compatibility
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server import flow_responses


TRUNCATED_ROW_COUNT = 10

def _GetTotalRowCount(
  responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
) -> int:
  project_length = lambda cur_response: len(cur_response.table.rows)
  row_lengths = map(project_length, responses)
  return sum(row_lengths)


class OsqueryFlow(flow_base.FlowBase):
  """A flow mixin wrapping the osquery client action."""

  friendly_name = "Osquery"
  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_osquery.OsqueryArgs
  progress_type = rdf_osquery.OsqueryProgress

  def _UpdateProgress(
    self,
    responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
  ) -> None:
    # XXX: Less than TRUNCATED_ROW_COUNT will be used if the original table is
    # split into chunks smaller than that. It is expected that the limit will
    # always be smaller than the chunk size, so this shouldn't happen.
    first_chunk = responses.responses[0]
    table = first_chunk.table

    self.state.progress.partial_table = table.Truncated(TRUNCATED_ROW_COUNT)
    self.state.progress.total_row_count = _GetTotalRowCount(responses)

  def Start(self):
    super(OsqueryFlow, self).Start()
    self.state.progress = rdf_osquery.OsqueryProgress()

    self.CallClient(
        server_stubs.Osquery,
        request=self.args,
        next_state=compatibility.GetName(self.Process))

  def Process(
      self,
      responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    self._UpdateProgress(responses)

    for response in responses:
      self.SendReply(response)

  def GetProgress(self) -> rdf_osquery.OsqueryProgress:
    return self.state.progress
