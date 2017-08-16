#!/usr/bin/env python
"""End to end tests for lib.flows.general.collectors."""


from grr.endtoend_tests import base
from grr.lib.rdfvalues import client as rdf_client
from grr.server.flows.general import collectors


class TestCollector(base.AutomatedTest):
  """Test ArtifactCollectorFlow."""
  platforms = ["Windows"]
  flow = collectors.ArtifactCollectorFlow.__name__
  args = {
      "artifact_list": ["WindowsExplorerNamespaceMyComputer"],
      "store_results_in_aff4": False
  }

  def CheckFlow(self):
    statentry_list = self.CheckResultCollectionNotEmptyWithRetry(
        self.session_id)
    for statentry in statentry_list:
      self.assertTrue(isinstance(statentry, rdf_client.StatEntry))
      self.assertTrue("NameSpace" in statentry.pathspec.path)
