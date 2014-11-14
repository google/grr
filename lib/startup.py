#!/usr/bin/env python
"""Startup routines for GRR.

Contains the startup routines and Init functions for initializing GRR.
"""

import logging
import os
import platform
import sys

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


def ClientPluginInit():
  """If we are running as a Client, initialize any client plugins.

  This provides the ability to customize the pre-built client. Simply add python
  files to the binary client template zip file, and specify these in the
  configuration file as the Client.plugins parameter. The client will import
  these files (and register any plugins at run time).
  """
  for plugin in config_lib.CONFIG["Client.plugins"]:
    config_lib.PluginLoader.LoadPlugin(
        os.path.join(os.path.dirname(sys.executable), plugin))


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
  ClientPluginInit()
  registry.Init()

# Make sure we do not reinitialize multiple times.
INIT_RAN = False


def Init():
  """Run all required startup routines and initialization hooks."""
  global INIT_RAN
  if INIT_RAN:
    return

  stats.STATS = stats.StatsCollector()

  AddConfigContext()
  ConfigInit()

  ServerLoggingStartupInit()
  registry.Init()

  if platform.system() != "Windows":
    if config_lib.CONFIG["Server.username"]:
      try:
        os.setuid(pwd.getpwnam(config_lib.CONFIG["Server.username"]).pw_uid)
      except (KeyError, OSError):
        logging.exception("Unable to switch to user %s",
                          config_lib.CONFIG["Server.username"])
        raise

  INIT_RAN = True


def TestInit():
  """Only used in tests and will rerun all the hooks to create a clean state."""
  # Tests use both the server template grr_server.yaml as a primary config file
  # (this file does not contain all required options, e.g. private keys), and
  # additional configuration in test_data/grr_test.yaml which contains typical
  # values for a complete installation.
  if stats.STATS is None:
    stats.STATS = stats.StatsCollector()

  flags.FLAGS.config = config_lib.CONFIG["Test.config"]
  flags.FLAGS.secondary_configs = [
      os.path.join(config_lib.CONFIG["Test.data_dir"], "grr_test.yaml")]

  # We are running a test so let the config system know that.
  config_lib.CONFIG.AddContext(
      "Test Context", "Context applied when we run tests.")

  AddConfigContext()
  ConfigInit()

  # Tests additionally add a test configuration file.
  ServerLoggingStartupInit()
  registry.TestInit()
