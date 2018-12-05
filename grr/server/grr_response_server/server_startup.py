#!/usr/bin/env python
"""Server startup routines."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import platform

from grr_response_core import config
from grr_response_core.lib import communicator
from grr_response_core.lib import config_lib
from grr_response_core.lib import registry
# pylint: disable=unused-import
from grr_response_core.lib.local import plugins
# pylint: enable=unused-import
from grr_response_core.lib.parsers import all as all_parsers
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_server import server_logging
from grr_response_server import server_metrics
from grr_response_server.blob_stores import registry_init as bs_registry_init
from grr_response_server.decoders import all as all_decoders


# pylint: disable=g-import-not-at-top
if platform.system() != "Windows":
  import pwd
# pylint: enable=g-import-not-at-top


def DropPrivileges():
  """Attempt to drop privileges if required."""
  if config.CONFIG["Server.username"]:
    try:
      os.setuid(pwd.getpwnam(config.CONFIG["Server.username"]).pw_uid)
    except (KeyError, OSError):
      logging.exception("Unable to switch to user %s",
                        config.CONFIG["Server.username"])
      raise


# Make sure we do not reinitialize multiple times.
INIT_RAN = False


def Init():
  """Run all required startup routines and initialization hooks."""
  global INIT_RAN
  if INIT_RAN:
    return

  # Set up a temporary syslog handler so we have somewhere to log problems
  # with ConfigInit() which needs to happen before we can start our create our
  # proper logging setup.
  syslog_logger = logging.getLogger("TempLogger")
  if os.path.exists("/dev/log"):
    handler = logging.handlers.SysLogHandler(address="/dev/log")
  else:
    handler = logging.handlers.SysLogHandler()
  syslog_logger.addHandler(handler)

  try:
    config_lib.SetPlatformArchContext()
    config_lib.ParseConfigCommandLine()
  except config_lib.Error:
    syslog_logger.exception("Died during config initialization")
    raise

  metric_metadata = server_metrics.GetMetadata()
  metric_metadata.extend(communicator.GetMetricMetadata())
  stats_collector = default_stats_collector.DefaultStatsCollector(
      metric_metadata)
  stats_collector_instance.Set(stats_collector)

  server_logging.ServerLoggingStartupInit()

  bs_registry_init.RegisterBlobStores()
  all_decoders.Register()
  all_parsers.Register()
  registry.Init()

  # Exempt config updater from this check because it is the one responsible for
  # setting the variable.
  if not config.CONFIG.ContextApplied("ConfigUpdater Context"):
    if not config.CONFIG.Get("Server.initialized"):
      raise RuntimeError("Config not initialized, run \"grr_config_updater"
                         " initialize\". If the server is already configured,"
                         " add \"Server.initialized: True\" to your config.")

  INIT_RAN = True
