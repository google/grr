#!/usr/bin/env python
"""This module contains regression tests for output plugins API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_server import instant_output_plugin
from grr_response_server import output_plugin
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import output_plugin as output_plugin_plugin
from grr_response_server.output_plugins import csv_plugin
from grr_response_server.output_plugins import email_plugin
from grr.test_lib import test_lib


class ApiListOutputPluginDescriptorsHandlerTest(
    api_regression_test_lib.ApiRegressionTest):
  """Regression test for ApiOutputPluginsListHandler."""

  api_method = "ListOutputPluginDescriptors"
  handler = output_plugin_plugin.ApiListOutputPluginDescriptorsHandler

  def Run(self):
    with utils.MultiStubber((output_plugin.OutputPlugin, "classes", {
        "EmailOutputPlugin": email_plugin.EmailOutputPlugin,
    }), (instant_output_plugin.InstantOutputPlugin, "classes", {
        "CSVInstantOutputPlugin": csv_plugin.CSVInstantOutputPlugin
    })):
      self.Check("ListOutputPluginDescriptors")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
