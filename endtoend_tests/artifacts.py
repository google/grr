#!/usr/bin/env python
"""End to end tests that run ArtifactCollectorFlow."""



from grr.endtoend_tests import base
from grr.lib import aff4


class TestDarwinPersistenceMechanisms(base.AutomatedTest):
  """Test DarwinPersistenceMechanisms."""
  platforms = ["Darwin"]
  flow = "ArtifactCollectorFlow"
  test_output_path = "analysis/persistence/testing"
  args = {"artifact_list": ["DarwinPersistenceMechanisms"],
          "output": test_output_path}

  def CheckFlow(self):
    output_urn = self.client_id.Add(self.test_output_path)
    collection = aff4.FACTORY.Open(output_urn, mode="r", token=self.token)
    self.assertIsInstance(collection, aff4.RDFValueCollection)
    persistence_list = list(collection)
    # Make sure there are at least some results.
    self.assertGreater(len(persistence_list), 5)
    launchservices = "/System/Library/CoreServices/launchservicesd"

    for p in persistence_list:
      if p.pathspec.path == launchservices:
        return
    self.fail("Service listing does not contain launchservices: %s." %
              launchservices)

