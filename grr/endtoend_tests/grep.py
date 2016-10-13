#!/usr/bin/env python
"""End to end tests for lib.flows.general.grep."""


from grr.endtoend_tests import base
from grr.lib import flow_runner
from grr.lib.rdfvalues import client as rdf_client


class TestSearchFilesGrep(base.AutomatedTest):
  """Test SearchFileContent with grep."""
  platforms = ["Linux"]
  flow = "SearchFileContent"
  args = {
      "paths": ["/bin/ls*"],
      "grep": rdf_client.BareGrepSpec(literal="ELF"),
      "also_download": True
  }

  def CheckFlow(self):
    results = self.CheckCollectionNotEmptyWithRetry(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX), self.token)
    for result in results:
      self.assertTrue("ELF" in result.data)
      self.assertTrue("ls" in result.pathspec.path)
