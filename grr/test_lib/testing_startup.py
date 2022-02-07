#!/usr/bin/env python
"""Initialize for tests."""

import os

from absl import flags

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import config_lib
from grr_response_core.lib import package
from grr_response_core.lib import utils
from grr_response_core.lib.util import temp
from grr_response_core.stats import stats_collector_instance
from grr_response_server import artifact
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import ip_resolver
from grr_response_server import prometheus_stats_collector
from grr_response_server import server_logging
from grr_response_server import stats_server
from grr_response_server.authorization import client_approval_auth
from grr_response_server.check_lib import checks
from grr_response_server.gui import http_api
from grr_response_server.gui import registry_init as gui_api_registry_init
from grr_response_server.gui import webauth
from grr.test_lib import blob_store_test_lib

# Make sure we do not reinitialize multiple times.
INIT_RAN = False

flags.DEFINE_string(
    "test_data_store", None, "The data store implementation to use for running "
    "the tests.")


def TestInit():
  """Only used in tests and will rerun all the hooks to create a clean state."""
  global INIT_RAN

  stats_collector = prometheus_stats_collector.PrometheusStatsCollector()
  stats_collector_instance.Set(stats_collector)

  # Tests use both the server template grr_server.yaml as a primary config file
  # (this file does not contain all required options, e.g. private keys), and
  # additional configuration in test_data/grr_test.yaml which contains typical
  # values for a complete installation.
  flags.FLAGS.config = package.ResourcePath("grr-response-core",
                                            "install_data/etc/grr-server.yaml")

  flags.FLAGS.secondary_configs.append(
      package.ResourcePath("grr-response-test",
                           "grr_response_test/test_data/grr_test.yaml"))

  # This config contains non-public settings that should be applied during
  # tests.
  extra_test_config = config.CONFIG["Test.additional_test_config"]
  if os.path.exists(extra_test_config):
    flags.FLAGS.secondary_configs.append(extra_test_config)

  # Prevent using the default writeback location since it may clash with local
  # setup.
  writeback_filepath = temp.TempFilePath(prefix="grr_writeback", suffix=".yaml")
  config.CONFIG.global_override["Config.writeback"] = writeback_filepath

  # Tests additionally add a test configuration file.
  config_lib.SetPlatformArchContext()
  config_lib.ParseConfigCommandLine()

  # We are running a test so let the config system know that.
  config.CONFIG.AddContext(contexts.TEST_CONTEXT,
                           "Context applied when we run tests.")

  if not INIT_RAN:
    server_logging.ServerLoggingStartupInit()
    server_logging.SetTestVerbosity()

  blob_store_test_lib.UseTestBlobStore()

  data_store.InitializeDataStore()

  artifact.LoadArtifactsOnce()
  checks.LoadChecksFromFilesystemOnce()
  client_approval_auth.InitializeClientApprovalAuthorizationManagerOnce()
  email_alerts.InitializeEmailAlerterOnce()
  http_api.InitializeHttpRequestHandlerOnce()
  ip_resolver.IPResolverInitOnce()
  stats_server.InitializeStatsServerOnce()
  webauth.InitializeWebAuthOnce()

  if not utils.TimeBasedCache.house_keeper_thread:
    utils.TimeBasedCache()
  utils.TimeBasedCache.house_keeper_thread.exit = True
  utils.TimeBasedCache.house_keeper_thread.join()

  gui_api_registry_init.RegisterApiCallRouters()

  INIT_RAN = True
