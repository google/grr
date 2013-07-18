#!/usr/bin/env python
"""Startup routines for GRR.

Contains the startup routines and Init functions for initializing GRR.
"""

import os

import logging
from grr.lib import config_lib
from grr.lib import log
from grr.lib import registry


# Disable this warning for this section, we import dynamically a lot in here.
# pylint: disable=g-import-not-at-top


def ConfigInit():
  """Initialize the configuration manager."""
  try:
    # Check for a config init function in the local directory first.
    # pylint: disable=g-import-not-at-top
    from grr.lib.local import config as local_config
    local_config.ConfigLibInit()
    logging.debug("Using local ConfigLibInit from %s", local_config)
  except (AttributeError, ImportError):
    # If it doesn't exist load the default one.
    config_lib.ConfigLibInit()


def ClientPluginInit():
  """If we are running as a Client, initialize any client plugins."""
  for plugin in config_lib.CONFIG["Client.plugins"]:
    config_lib.PluginLoader.LoadPlugin(
        os.path.join(config_lib.CONFIG["Client.install_path"], plugin))


def ClientLoggingStartupInit():
  """Initialize client logging."""
  try:
    from grr.client.local import log as local_log
    local_log.LogInit()
    logging.debug("Using local LogInit from %s", local_log)
  except (AttributeError, ImportError):
    # If it doesn't exist load the default one.
    log.LogInit()


def ServerLoggingStartupInit():
  """Initialize the logging configuration."""
  # First initialize the main logging features. These control the logging.xxxx
  # functions.
  try:
    # Check for a LogInit function in the local directory first.
    from grr.lib.local import log as local_log
    local_log.LogInit()
    logging.debug("Using local LogInit from %s", local_log)
  except (AttributeError, ImportError):
    # If it doesn't exist load the default one.
    log.LogInit()

  # Now setup the server side advanced application logging.
  try:
    # Check for a AppLogInit function in the local directory first.
    from grr.lib.local import log as local_log
    local_log.AppLogInit()
    logging.debug("Using local AppLogInit from %s", local_log)
  except (AttributeError, ImportError):
    # If it doesn't exist load the default one.
    log.AppLogInit()


def ClientInit():
  """Run all startup routines for the client."""
  ConfigInit()
  ClientLoggingStartupInit()
  ClientPluginInit()
  from grr.client import installer
  installer.InstallerPluginInit()
  registry.Init()


def Init():
  """Run all required startup routines and initialization hooks."""
  ConfigInit()
  ServerLoggingStartupInit()
  registry.Init()


def TestInit():
  """Only used in tests and will rerun all the hooks to create a clean state."""
  ConfigInit()
  ServerLoggingStartupInit()
  registry.TestInit()
