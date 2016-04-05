#!/usr/bin/env python
"""End to end tests for lib.flows.general.collectors."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib.rdfvalues import client as rdf_client


class TestCollector(base.AutomatedTest):
  """Test ArtifactCollectorFlow."""
  platforms = ["Windows"]
  flow = "ArtifactCollectorFlow"
  test_output_path = "analysis/artifact/testing"
  args = {"output": test_output_path,
          "artifact_list": ["WindowsRunKeys"],
          "store_results_in_aff4": False}

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                   token=self.token)
    self.assertIsInstance(collection, aff4.RDFValueCollection)

    self.assertTrue(len(collection) >= 1)
    for statentry in collection:
      self.assertTrue(isinstance(statentry, rdf_client.StatEntry))
      self.assertTrue("Run" in statentry.pathspec.path)
