#!/usr/bin/env python
"""End to end tests for lib.flows.general.grep."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib.rdfvalues import client as rdf_client


class TestSearchFilesGrep(base.AutomatedTest):
  """Test SearchFileContent with grep."""
  platforms = ["Linux"]
  flow = "SearchFileContent"
  test_output_path = "analysis/SearchFilesGrep/testing"
  args = {"output": test_output_path,
          "paths": ["/bin/ls*"],
          "grep": rdf_client.BareGrepSpec(literal="ELF"),
          "also_download": True}

  def CheckFlow(self):
    results = aff4.FACTORY.Open(self.client_id.Add(self.test_output_path),
                                token=self.token)
    self.assertGreaterEqual(len(results), 1)
    for result in results:
      self.assertTrue("ELF" in result.data)
      self.assertTrue("ls" in result.pathspec.path)
