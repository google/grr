#!/usr/bin/env python
"""This module contains tests for reflection API renderers."""



from grr.gui import api_test_lib
from grr.gui.api_plugins import reflection as reflection


from grr.lib import flags
from grr.lib import test_lib


class ApiRDFValueReflectionRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):
  """Regression test for ApiRDFValueReflectionRenderer."""

  renderer = "ApiRDFValueReflectionRenderer"

  def Run(self):
    self.Check("GET", "/api/reflection/rdfvalue/Duration")
    self.Check("GET", "/api/reflection/rdfvalue/"
               "ApiRDFValueCollectionRendererArgs")


class ApiAllRDFValuesReflectionRendererTest(test_lib.GRRBaseTest):
  """Test for ApiAllRDFValuesReflectionRenderer."""

  def testSuccessfullyRendersReflectionDataForAllTypes(self):
    result = reflection.ApiAllRDFValuesReflectionRenderer().Render(
        None, token=self.token)
    self.assertTrue(result)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
