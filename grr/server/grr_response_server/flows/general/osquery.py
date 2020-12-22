#!/usr/bin/env python
# Lint as: python3
"""A module with flow class calling the osquery client action."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.util import compatibility
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


TRUNCATED_ROW_COUNT = 10


def _GetTotalRowCount(
    responses: flow_responses.Responses[rdf_osquery.OsqueryResult],) -> int:
  get_row_lengths = lambda response: len(response.table.rows)
  row_lengths = map(get_row_lengths, responses)
  return sum(row_lengths)


def _GetTruncatedTable(
    responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
) -> rdf_osquery.OsqueryTable:
  """Constructs a truncated OsqueryTable.

  Constructs an OsqueryTable by extracting the first TRUNCATED_ROW_COUNT rows
  from the tables contained in the given OsqueryResult list.

  Args:
    responses: List of OsqueryResult elements from which to construct the
      truncated table.

  Returns:
    A truncated OsqueryTable.
  """
  tables = [response.table for response in responses]

  result = tables[0].Truncated(TRUNCATED_ROW_COUNT)

  for table in tables[1:]:
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
    if not responses.success:
      self.state.progress.error_message = responses.status.error_message
      self.state.progress.partial_table = None
      self.state.progress.total_row_count = None
    else:
      self.state.progress.error_message = None
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
    self._UpdateProgress(responses)

    if not responses.success:
      raise flow_base.FlowError(responses.status)

    for response in responses:
      self.SendReply(response)

  def GetProgress(self) -> rdf_osquery.OsqueryProgress:
    return self.state.progress
