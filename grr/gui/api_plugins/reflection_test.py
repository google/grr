#!/usr/bin/env python
"""This module contains tests for reflection API handlers."""



from grr.gui import api_test_lib
from grr.gui.api_plugins import reflection as reflection_plugin

from grr.lib import flags
from grr.lib import test_lib


class ApiGetRDFValueDescriptorHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiGetRDFValueDescriptorHandler."""

  api_method = "GetRDFValueDescriptor"
  handler = reflection_plugin.ApiGetRDFValueDescriptorHandler

  def Run(self):
    self.Check("GET", "/api/reflection/rdfvalue/Duration")
    self.Check("GET", "/api/reflection/rdfvalue/ApiFlow")


class ApiGetRDFValueDescriptorHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiGetRDFValueDescriptorHandler."""

  def testSuccessfullyRendersReflectionDataForAllTypes(self):
    result = reflection_plugin.ApiListRDFValuesDescriptorsHandler().Handle(
        None, token=self.token)
    # TODO(user): enhance this test.
    self.assertTrue(result)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
