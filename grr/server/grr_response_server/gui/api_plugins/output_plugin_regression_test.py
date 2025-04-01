#!/usr/bin/env python
"""This module contains regression tests for output plugins API handlers."""

from unittest import mock

from absl import app

from grr_response_core.lib import registry
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import output_plugin as output_plugin_plugin
from grr_response_server.output_plugins import csv_plugin
from grr_response_server.output_plugins import email_plugin
from grr.test_lib import test_lib


class ApiListOutputPluginDescriptorsHandlerTest(
    api_regression_test_lib.ApiRegressionTest
):
  """Regression test for ApiOutputPluginsListHandler."""

  api_method = "ListOutputPluginDescriptors"
  handler = output_plugin_plugin.ApiListOutputPluginDescriptorsHandler

  def Run(self):
    with mock.patch.object(
        registry.OutputPluginRegistry,
        "PLUGIN_REGISTRY",
        {
            "CSVInstantOutputPlugin": csv_plugin.CSVInstantOutputPlugin,
            "EmailOutputPlugin": email_plugin.EmailOutputPlugin,
        },
    ):
      self.Check("ListOutputPluginDescriptors")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
