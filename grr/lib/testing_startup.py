#!/usr/bin/env python
"""Initialize for tests."""

import os

from grr import config
from grr.config import contexts
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import log
from grr.lib import registry
from grr.lib import stats
from grr.lib.blob_stores import memory_stream_bs
from grr.lib.data_stores import fake_data_store

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

  flags.FLAGS.secondary_configs.append(
      config_lib.Resource().Filter("test_data/grr_test.yaml@grr-response-test"))

  # This config contains non-public settings that should be applied during
  # tests.
  extra_test_config = config.CONFIG["Test.additional_test_config"]
  if os.path.exists(extra_test_config):
    flags.FLAGS.secondary_configs.append(extra_test_config)

  # We are running a test so let the config system know that.
  config.CONFIG.AddContext(contexts.TEST_CONTEXT,
                           "Context applied when we run tests.")

  config.CONFIG.Set("Datastore.implementation",
                    fake_data_store.FakeDataStore.__name__)
  config.CONFIG.Set("Blobstore.implementation",
                    memory_stream_bs.MemoryStreamBlobstore.__name__)

  # Tests additionally add a test configuration file.
  config_lib.SetPlatformArchContext()
  config_lib.ParseConfigCommandLine()

  data_store.DataStoreInit().Run()
  aff4.AFF4InitHook().Run()

  if not INIT_RAN:
    log.ServerLoggingStartupInit()

  registry.TestInit()

  INIT_RAN = True
