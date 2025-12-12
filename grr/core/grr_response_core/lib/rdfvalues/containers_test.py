#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import containers as rdf_containers
from grr.test_lib import test_lib


class ContainersTest(test_lib.GRRBaseTest):

  def testListContainersRequest(self):
    request = rdf_containers.ListContainersRequest()
    self.assertFalse(request.inspect_hostroot)
    request = rdf_containers.ListContainersRequest(inspect_hostroot=True)
    self.assertTrue(request.inspect_hostroot)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
