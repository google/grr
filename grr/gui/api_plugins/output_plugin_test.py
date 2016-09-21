#!/usr/bin/env python
"""This module contains tests for output plugins-related API handlers."""



from grr.gui import api_test_lib
from grr.gui.api_plugins import output_plugin as output_plugin_plugin
from grr.lib import flags
from grr.lib import output_plugin
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.output_plugins import csv_plugin
from grr.lib.output_plugins import email_plugin


class ApiListOutputPluginDescriptorsHandlerTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiOutputPluginsListHandler."""

  api_method = "ListOutputPluginDescriptors"
  handler = output_plugin_plugin.ApiListOutputPluginDescriptorsHandler

  def Run(self):
    with utils.Stubber(output_plugin.OutputPlugin, "classes", {
        "EmailOutputPlugin": email_plugin.EmailOutputPlugin,
        "CSVOutputPlugin": csv_plugin.CSVOutputPlugin
    }):
      self.Check("GET", "/api/output-plugins/all")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
