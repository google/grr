#!/usr/bin/env python
"""This module contains regression tests for reflection API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_server.gui import api_regression_test_lib

from grr_response_server.gui.api_plugins import reflection as reflection_plugin


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
