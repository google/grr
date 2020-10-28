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


TRUNCATED_ROWS_COUNT = 10


class OsqueryFlow(flow_base.FlowBase):
  """A flow mixin wrapping the osquery client action."""

  friendly_name = "Osquery"
  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_osquery.OsqueryArgs
  progress_type = rdf_osquery.OsqueryProgress

  def Start(self):
    super(OsqueryFlow, self).Start()

    self.state.progress = rdf_osquery.OsqueryProgress()
    self.CallClient(
        server_stubs.Osquery,
        request=self.args,
        next_state=compatibility.GetName(self.Process))

  def Process(self, responses: flow_responses.Responses[rdf_osquery.OsqueryResult]) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    for response in responses:
      self.UpdateProgress(response.table)
      self.SendReply(response)

  def GetProgress(self) -> rdf_osquery.OsqueryProgress:
    return self.state.progress

  def UpdateProgress(self, table: rdf_osquery.OsqueryTable) -> None:
    self.state.progress.partialTable = TruncateRows(table)
    self.state.progress.totalRowsCount = len(table.rows)


def TruncateRows(table: rdf_osquery.OsqueryTable) -> rdf_osquery.OsqueryTable:
  result = rdf_osquery.OsqueryTable()

  result.query = table.query
  result.header = table.header
  result.rows = table.rows[:TRUNCATED_ROWS_COUNT]

  return result
