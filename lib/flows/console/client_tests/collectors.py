#!/usr/bin/env python
"""End to end tests for lib.flows.general.collectors."""


from grr.lib import aff4
from grr.lib.flows.console.client_tests import base


class TestCollector(base.ClientTestBase):
  """Test ArtifactCollectorFlow."""
  platforms = ["windows"]
  flow = "ArtifactCollectorFlow"

  args = {"output": "analysis/artifact/testing",
          "artifact_list": ["VolatilityPsList"],
          "store_results_in_aff4": False}

  def setUp(self):
    super(TestCollector, self).setUp()
    self.urn = self.client_id.Add(self.args["output"])
    self.DeleteUrn(self.urn)

  def CheckFlow(self):
    collection = aff4.FACTORY.Open(self.urn, token=self.token)
    self.assertIsInstance(collection, aff4.RDFValueCollection)
    self.assertTrue(len(list(collection)) > 40)

