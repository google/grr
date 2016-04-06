#!/usr/bin/env python
"""This file defines the entry points for typical installations."""

# Imports must be inline to stop argument pollution across the entry points.
# pylint: disable=g-import-not-at-top
import os
import platform

from grr import defaults
from grr.lib import config_lib
from grr.lib import flags


# Set custom options for each distro here.
DISTRO_DEFAULTS = {
    "debian": {"flag_defaults": {"config": "/etc/grr/grr-server.yaml"},
               "config_opts": {"Config.writeback":
                               "/etc/grr/server.local.yaml"}},
    "redhat": {"flag_defaults": {"config": "/etc/grr/grr-server.yaml"},
               "config_opts": {"Config.writeback":
                               "/etc/grr/server.local.yaml"}},
}


def GetDistroDefaults():
  """Return the distro specific config to use."""
  if platform.system() == "Linux":
    distribution = platform.linux_distribution()[0].lower()
    if distribution in ["ubuntu", "debian"]:
      return DISTRO_DEFAULTS["debian"]
    if distribution in ["red hat enterprise linux server", "centos linux"]:
      return DISTRO_DEFAULTS["redhat"]

  return {"flag_defaults": {}, "config_opts": {}}


def SetConfigOptions():
  """Set distro specific options."""
  distro_default = GetDistroDefaults()
  config_opts = distro_default["config_opts"]
  flag_defaults = distro_default["flag_defaults"]

  for option, value in config_opts.items():
    config_lib.CONFIG.Set(option, value)

  # Allow the installer to override the platform defaults for the location of
  # the config file. The config file is therefore searched in the following
  # order:
  # 1. Specified on the command line with the "--config XXXX" option.
  # 2. Specified in the environment variable GRR_CONFIG_FILE.
  # 3. Specified during installation with:
  #     "python setup.py install --config-file=XXXX"
  # 4. Searched in the default location for this platform.
  if os.environ.get("GRR_CONFIG_FILE"):
    flag_defaults["config"] = os.environ.get("GRR_CONFIG_FILE")

  elif defaults.CONFIG_FILE:
    flag_defaults["config"] = defaults.CONFIG_FILE

  flags.PARSER.set_defaults(**flag_defaults)


def Console():
  from grr.tools import console
  SetConfigOptions()
  flags.StartMain(console.main)


def ConfigUpdater():
  from grr.tools import config_updater
  SetConfigOptions()
  flags.StartMain(config_updater.main)


def GrrServer():
  from grr.tools import grr_server
  SetConfigOptions()
  flags.StartMain(grr_server.main)


def GrrFrontEnd():
  from grr.tools import http_server
  SetConfigOptions()
  flags.StartMain(http_server.main)


def EndToEndTests():
  from grr.tools import end_to_end_tests
  SetConfigOptions()
  flags.StartMain(end_to_end_tests.main)


def Export():
  from grr.tools import export
  export.AddPluginsSubparsers()
  SetConfigOptions()
  flags.StartMain(export.main)


def Worker():
  from grr.worker import worker
  SetConfigOptions()
  flags.StartMain(worker.main)


def GRRFuse():
  from grr.tools import fuse_mount
  SetConfigOptions()
  flags.StartMain(fuse_mount.main)


def ClientBuild():
  from grr.client import client_build
  SetConfigOptions()
  flags.StartMain(client_build.main)


def Client():
  from grr.client import client
  SetConfigOptions()
  flags.StartMain(client.main)


def AdminUI():
  from grr.gui import admin_ui
  SetConfigOptions()
  flags.StartMain(admin_ui.main)
