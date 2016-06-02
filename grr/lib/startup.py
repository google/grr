#!/usr/bin/env python
"""Startup routines for GRR.

Contains the startup routines and Init functions for initializing GRR.
"""

import logging
import os
import platform

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import log
from grr.lib import registry
from grr.lib import stats

# Disable this warning for this section, we import dynamically a lot in here.
# pylint: disable=g-import-not-at-top
if platform.system() != "Windows":
  import pwd


def AddConfigContext():
  """Add the running contexts to the config system."""
  # Initialize the running platform context:
  config_lib.CONFIG.AddContext("Platform:%s" % platform.system().title())

  if platform.architecture()[0] == "32bit":
    config_lib.CONFIG.AddContext("Arch:i386")
  elif platform.architecture()[0] == "64bit":
    config_lib.CONFIG.AddContext("Arch:amd64")


def ConfigInit():
  """Initialize the configuration manager from the command line arg."""
  # Initialize the config system from the command line options.
  config_lib.ParseConfigCommandLine()


def ClientLoggingStartupInit():
  """Initialize client logging."""
  log.LogInit()


def ServerLoggingStartupInit():
  """Initialize the logging configuration."""
  log.LogInit()
  log.AppLogInit()


def ClientInit():
  """Run all startup routines for the client."""
  if stats.STATS is None:
    stats.STATS = stats.StatsCollector()

  AddConfigContext()
  ConfigInit()

  ClientLoggingStartupInit()
  registry.Init()

# Make sure we do not reinitialize multiple times.
INIT_RAN = False


def Init():
  """Run all required startup routines and initialization hooks."""
  global INIT_RAN
  if INIT_RAN:
    return

  stats.STATS = stats.StatsCollector()

  # Set up a temporary syslog handler so we have somewhere to log problems with
  # ConfigInit() which needs to happen before we can start our create our proper
  # logging setup.
  syslog_logger = logging.getLogger("TempLogger")
  if os.path.exists("/dev/log"):
    handler = logging.handlers.SysLogHandler(address="/dev/log")
  else:
    handler = logging.handlers.SysLogHandler()
  syslog_logger.addHandler(handler)

  try:
    AddConfigContext()
    ConfigInit()
  except config_lib.Error:
    syslog_logger.exception("Died during config initialization")
    raise

  ServerLoggingStartupInit()
  registry.Init()

  # Exempt config updater from this check because it is the one responsible for
  # setting the variable.
  if not config_lib.CONFIG.ContextApplied("ConfigUpdater Context"):
    if not config_lib.CONFIG.Get("Server.initialized"):
      raise RuntimeError("Config not initialized, run \"grr_config_updater"
                         " initialize\". If the server is already configured,"
                         " add \"Server.initialized: True\" to your config.")

  INIT_RAN = True


def DropPrivileges():
  """Attempt to drop privileges if required."""
  if config_lib.CONFIG["Server.username"]:
    try:
      os.setuid(pwd.getpwnam(config_lib.CONFIG["Server.username"]).pw_uid)
    except (KeyError, OSError):
      logging.exception("Unable to switch to user %s",
                        config_lib.CONFIG["Server.username"])
      raise


def TestInit():
  """Only used in tests and will rerun all the hooks to create a clean state."""
  # Tests use both the server template grr_server.yaml as a primary config file
  # (this file does not contain all required options, e.g. private keys), and
  # additional configuration in test_data/grr_test.yaml which contains typical
  # values for a complete installation.
  if stats.STATS is None:
    stats.STATS = stats.StatsCollector()

  flags.FLAGS.config = config_lib.Resource().Filter(
      "install_data/etc/grr-server.yaml")

  flags.FLAGS.secondary_configs = [
      config_lib.Resource().Filter("test_data/grr_test.yaml@grr-response-test")
  ]

  # We are running a test so let the config system know that.
  config_lib.CONFIG.AddContext("Test Context",
                               "Context applied when we run tests.")

  AddConfigContext()
  ConfigInit()

  # Tests additionally add a test configuration file.
  ServerLoggingStartupInit()
  registry.TestInit()
