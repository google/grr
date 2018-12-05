#!/usr/bin/env python
"""Program that generates golden regression data."""
from __future__ import absolute_import
from __future__ import division


from grr_response_core.lib import flags

from grr_response_server.gui import api_regression_test_lib

# pylint: disable=unused-import
from grr_response_server.gui.api_plugins import artifact_regression_test
from grr_response_server.gui.api_plugins import client_regression_test
from grr_response_server.gui.api_plugins import config_regression_test
from grr_response_server.gui.api_plugins import cron_regression_test
from grr_response_server.gui.api_plugins import flow_regression_test
from grr_response_server.gui.api_plugins import hunt_regression_test
from grr_response_server.gui.api_plugins import output_plugin_regression_test
from grr_response_server.gui.api_plugins import reflection_regression_test
from grr_response_server.gui.api_plugins import stats_regression_test
from grr_response_server.gui.api_plugins import user_regression_test
from grr_response_server.gui.api_plugins import vfs_regression_test

# pylint: enable=unused-import


def main(argv):
  """Entry function."""
  api_regression_test_lib.main(argv)


def DistEntry():
  """The main entry point for packages."""
  flags.StartMain(main)


if __name__ == "__main__":
  flags.StartMain(main)
