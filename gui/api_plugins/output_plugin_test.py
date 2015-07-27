#!/usr/bin/env python
"""This module contains tests for output plugins-related API renderers."""



from grr.gui import api_test_lib
from grr.lib import flags
from grr.lib import output_plugin
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.output_plugins import csv_plugin
from grr.lib.output_plugins import email_plugin


class ApiOutputPluginsListRendererRegressionTest(
    api_test_lib.ApiCallRendererRegressionTest):
  """Regression test for ApiOutputPluginsListRenderer."""

  renderer = "ApiOutputPluginsListRenderer"

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
