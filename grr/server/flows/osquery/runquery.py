'''
Created on Mar 23, 2018

@author: ashaman
'''
#!/usr/bin/env python
"""These are OSQuery related flows."""

from grr.lib.rdfvalues import osquery as rdf_osquery
from grr.server import flow
from grr.server import osquery_stubs


class RunQuery(flow.GRRFlow):
  """Retrieve system data from OSQuery"""

  category = "/OSQuery/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = rdf_osquery.OSQueryRunQueryArgs

  @flow.StateHandler()
  def Start(self):
    """Start processing."""
    self.CallClient(
      osquery_stubs.ExecuteOSQuerySQL,
      query=self.args.query,
      next_state="ValidateSQLResult")

  @flow.StateHandler()
  def ValidateSQLResult(self, responses):
    if not responses.success:
      self.Log(responses.status)
    else:
      for response in responses:
        self.SendReply(response)

  def NotifyAboutEnd(self):
    self.Notify("ViewObject", self.urn, "SQL Result")

  @flow.StateHandler()
  def End(self):
    self.Log("Successfully executed SQL")