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
  get_row_lengths = lambda response: len(response.table.rows)
  row_lengths = map(get_row_lengths, responses)
  return sum(row_lengths)


def _GetTruncatedTable(
  responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
) -> rdf_osquery.OsqueryTable:
  get_table = lambda response: response.table

  head_table = get_table(responses.responses[0])
  tail_tables = map(get_table, responses.responses[1:])

  result = head_table.Truncated(TRUNCATED_ROW_COUNT)

  for table in tail_tables:
    to_add = TRUNCATED_ROW_COUNT - len(result.rows)
    if to_add == 0:
      break

    result.rows.Extend(table.rows[:to_add])

  return result


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
    self.state.progress.partial_table = _GetTruncatedTable(responses)
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
