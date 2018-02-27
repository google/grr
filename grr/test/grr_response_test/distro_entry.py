#!/usr/bin/env python
"""This file defines the entry points for typical installations."""

# pylint: disable=g-import-not-at-top
# Argparse runs on import, and maintains static state.

from grr.lib import config_lib
from grr.lib import flags


def SetConfigOptions():
  """Set location of configuration flags."""
  flags.PARSER.set_defaults(
      config=config_lib.Resource().Filter("install_data/etc/grr-server.yaml"))


def EndToEndTests():
  from grr_response_test import run_end_to_end_tests
  SetConfigOptions()
  flags.StartMain(run_end_to_end_tests.main)


def ApiRegressionTestsGenerate():
  from grr_response_test import api_regression_test_generate
  SetConfigOptions()
  flags.StartMain(api_regression_test_generate.main)
