#!/usr/bin/env python
"""Server startup routines."""
import logging
import os
import platform

from grr import config
from grr.lib import config_lib
from grr.lib import registry
from grr.lib import stats
# pylint: disable=unused-import
from grr.lib.local import plugins
# pylint: enable=unused-import
from grr.server.grr_response_server import server_logging
from grr.server.grr_response_server.local import registry_init

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

  if hasattr(registry_init, "stats"):
    logging.debug("Using local stats collector.")
    stats.STATS = registry_init.stats.StatsCollector()
  else:
    logging.debug("Using default stats collector.")
    stats.STATS = stats.StatsCollector()

  server_logging.ServerLoggingStartupInit()

  registry.Init()

  # Exempt config updater from this check because it is the one responsible for
  # setting the variable.
  if not config.CONFIG.ContextApplied("ConfigUpdater Context"):
    if not config.CONFIG.Get("Server.initialized"):
      raise RuntimeError("Config not initialized, run \"grr_config_updater"
                         " initialize\". If the server is already configured,"
                         " add \"Server.initialized: True\" to your config.")

  INIT_RAN = True
