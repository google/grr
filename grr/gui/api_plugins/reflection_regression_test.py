#!/usr/bin/env python
"""This module contains regression tests for reflection API handlers."""


from grr.gui import api_regression_test_lib
from grr.gui.api_plugins import reflection as reflection_plugin

from grr.lib import flags


class ApiGetRDFValueDescriptorHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiGetRDFValueDescriptorHandler."""

  api_method = "GetRDFValueDescriptor"
  handler = reflection_plugin.ApiGetRDFValueDescriptorHandler

  def Run(self):
    self.Check(
        "GetRDFValueDescriptor",
        args=reflection_plugin.ApiGetRDFValueDescriptorArgs(type="Duration"))
    self.Check(
        "GetRDFValueDescriptor",
        args=reflection_plugin.ApiGetRDFValueDescriptorArgs(type="ApiFlow"))


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
