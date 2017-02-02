#!/usr/bin/env python
"""Initialize for tests."""

import os

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import log
from grr.lib import registry
from grr.lib import stats

# Make sure we do not reinitialize multiple times.
INIT_RAN = False


def TestInit():
  """Only used in tests and will rerun all the hooks to create a clean state."""
  global INIT_RAN

  if stats.STATS is None:
    stats.STATS = stats.StatsCollector()

  # Tests use both the server template grr_server.yaml as a primary config file
  # (this file does not contain all required options, e.g. private keys), and
  # additional configuration in test_data/grr_test.yaml which contains typical
  # values for a complete installation.
  flags.FLAGS.config = config_lib.Resource().Filter(
      "install_data/etc/grr-server.yaml")

  flags.FLAGS.secondary_configs.append(config_lib.Resource().Filter(
      "test_data/grr_test.yaml@grr-response-test"))

  # This config contains non-public settings that should be applied during
  # tests.
  extra_test_config = config_lib.CONFIG["Test.additional_test_config"]
  if os.path.exists(extra_test_config):
    flags.FLAGS.secondary_configs.append(extra_test_config)

  # We are running a test so let the config system know that.
  config_lib.CONFIG.AddContext("Test Context",
                               "Context applied when we run tests.")

  # Tests additionally add a test configuration file.
  config_lib.SetPlatformArchContext()
  config_lib.ParseConfigCommandLine()

  if not INIT_RAN:
    log.ServerLoggingStartupInit()

  registry.TestInit()

  INIT_RAN = True
