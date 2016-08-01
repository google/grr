#!/usr/bin/env python
"""End to end tests for lib.flows.general.collectors."""


from grr.endtoend_tests import base
from grr.lib import flow_runner
from grr.lib.rdfvalues import client as rdf_client


class TestCollector(base.AutomatedTest):
  """Test ArtifactCollectorFlow."""
  platforms = ["Windows"]
  flow = "ArtifactCollectorFlow"
  args = {"artifact_list": ["WindowsRunKeys"], "store_results_in_aff4": False}

  def CheckFlow(self):
    statentry_list = self.CheckCollectionNotEmptyWithRetry(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX), self.token)
    for statentry in statentry_list:
      self.assertTrue(isinstance(statentry, rdf_client.StatEntry))
      self.assertTrue("Run" in statentry.pathspec.path)
