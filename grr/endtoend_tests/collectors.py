#!/usr/bin/env python
"""End to end tests for lib.flows.general.collectors."""


from grr.endtoend_tests import base
from grr.lib.flows.general import collectors
from grr.lib.rdfvalues import client as rdf_client


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
      self.assertTrue("Namespace" in statentry.pathspec.path)
