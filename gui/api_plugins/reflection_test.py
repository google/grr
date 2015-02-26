#!/usr/bin/env python
"""This module contains tests for reflection API renderers."""



from grr.gui import api_test_lib

from grr.lib import flags
from grr.lib import test_lib


# TODO(user): Implement unit tests in addition to regression tests.


class ApiRDFValueReflectionRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):

  renderer = "ApiRDFValueReflectionRenderer"

  def Run(self):
    self.Check("GET", "/api/reflection/rdfvalue/Duration")
    self.Check("GET", "/api/reflection/rdfvalue/"
               "ApiRDFValueCollectionRendererArgs")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
