#!/usr/bin/env python
"""End to end tests for lib.flows.general.grep."""


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.flows.console.client_tests import base


class TestSearchFiles(base.ClientTestBase):
  """Test SearchFileContent."""
  platforms = ["linux"]
  flow = "SearchFileContent"

  args = {"output": "analysis/SearchFiles/testing",
          "paths": ["/bin/ls*"],
          "also_download": True}

  def setUp(self):
    super(TestSearchFiles, self).setUp()
    self.urn = self.client_id.Add(self.args["output"])
    self.DeleteUrn(self.urn)
    self.assertRaises(Exception, self.CheckFlow)

  def CheckFlow(self):
    results = aff4.FACTORY.Open(self.urn, token=self.token)
    self.assertGreater(len(results), 1)
    for result in results:
      self.assertTrue(result.pathspec.path.startswith("/bin/ls"))


class TestSearchFilesGrep(TestSearchFiles):
  args = {"output": "analysis/SearchFilesGrep/testing",
          "paths": ["/bin/ls*"],
          "grep": rdfvalue.BareGrepSpec(literal="ELF"),
          "also_download": True}

  def CheckFlow(self):
    results = aff4.FACTORY.Open(self.urn, token=self.token)
    self.assertGreater(len(results), 1)
    for result in results:
      self.assertTrue("ELF" in result.data)
      self.assertTrue("ls" in result.pathspec.path)
