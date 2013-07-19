#!/usr/bin/env python
"""Startup routines for GRR.

Contains the startup routines and Init functions for initializing GRR.
"""
import os
import platform

import logging

from grr.lib import config_lib
from grr.lib import local
from grr.lib import log
from grr.lib import registry


# Disable this warning for this section, we import dynamically a lot in here.
# pylint: disable=g-import-not-at-top
def AddConfigContext():
  """Add the running contexts to the config system."""
  # Initialize the running platform context:
  config_lib.CONFIG.AddContext("Platform:%s" % platform.system().title())

  if platform.architecture()[0] == "32bit":
    config_lib.CONFIG.AddContext("Arch:i386")
  elif platform.architecture()[0] == "64bit":
    config_lib.CONFIG.AddContext("Arch:amd64")


def ConfigInit():
  """Initialize the configuration manager."""
  local.ConfigInit()

  if config_lib.CONFIG["Config.writeback"]:
    config_lib.CONFIG.SetWriteBack(config_lib.CONFIG["Config.writeback"])


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
  AddConfigContext()
  ClientLoggingStartupInit()
  ClientPluginInit()
  from grr.client import installer
  installer.InstallerPluginInit()
  registry.Init()


# Make sure we do not reinitialize multiple times.
INIT_RAN = False


def Init():
  """Run all required startup routines and initialization hooks."""
  global INIT_RAN
  if INIT_RAN:
    return

  ConfigInit()
  AddConfigContext()
  ServerLoggingStartupInit()
  registry.Init()
  INIT_RAN = True


def TestInit():
  """Only used in tests and will rerun all the hooks to create a clean state."""
  AddConfigContext()
  ServerLoggingStartupInit()
  registry.TestInit()
