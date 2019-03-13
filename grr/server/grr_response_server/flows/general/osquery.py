#!/usr/bin/env python
"""A module with flow class calling the osquery client action."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs


@flow_base.DualDBFlow
class OsqueryFlowMixin(object):
  """A flow mixin wrapping the osquery client action."""

  friendly_name = "Osquery"
  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  args_type = rdf_osquery.OsqueryArgs

  def Start(self):
    super(OsqueryFlowMixin, self).Start()
    self.CallClient(
        server_stubs.Osquery, request=self.args, next_state="Process")

  def Process(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.SendReply(response)
