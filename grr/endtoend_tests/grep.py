#!/usr/bin/env python
"""End to end tests for lib.flows.general.grep."""


from grr.endtoend_tests import base
from grr.lib.rdfvalues import client as rdf_client
from grr.server.flows.general import grep


class TestSearchFilesGrep(base.AutomatedTest):
  """Test SearchFileContent with grep."""
  platforms = ["Linux"]
  flow = grep.SearchFileContent.__name__
  args = {
      "paths": ["/bin/ls*"],
      "grep": rdf_client.BareGrepSpec(literal="ELF"),
      "also_download": True
  }

  def CheckFlow(self):
    results = self.CheckResultCollectionNotEmptyWithRetry(self.session_id)
    for result in results:
      self.assertTrue("ELF" in result.data)
      self.assertTrue("ls" in result.pathspec.path)
