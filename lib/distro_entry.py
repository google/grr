#!/usr/bin/env python
"""This file defines the entry points for typical installations."""

# Imports must be inline to stop argument pollution across the entry points.
# pylint: disable=g-import-not-at-top

import platform

from grr.lib import config_lib
from grr.lib import flags


# Set custom options for each distro here.
DISTRO_DEFAULTS = {
    "debian": {"flag_defaults": {"config": "/etc/grr/grr-server.yaml"},
               "config_opts": {"Config.writeback": "/etc/grr/server.local.yaml"}
              },
    "redhat": {"flag_defaults": {"config": "/etc/grr/grr-server.yaml"},
               "config_opts": {"Config.writeback": "/etc/grr/server.local.yaml"}
              },
}


def GetDistro():
  """Return the distro specific config to use."""
  if hasattr(platform, "linux_distribution"):
    distribution = platform.linux_distribution()[0].lower()
    if distribution in ["ubuntu", "debian"]:
      return "debian"
    if distribution in ["red hat enterprise linux server"]:
      return "redhat"
  raise RuntimeError("Missing distro specific config. Please update "
                     "distro_entry.py.")


def SetConfigOptions():
  """Set distro specific options."""
  distro = GetDistro()
  for option, value in DISTRO_DEFAULTS[distro]["config_opts"].items():
    config_lib.CONFIG.Set(option, value)
  flags.PARSER.set_defaults(**DISTRO_DEFAULTS[distro]["flag_defaults"])


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


def EndToEndTests():
  from grr.tools import end_to_end_tests
  SetConfigOptions()
  flags.StartMain(end_to_end_tests.main)


def Export():
  from grr.tools import export
  export.AddPluginsSubparsers()
  SetConfigOptions()
  flags.StartMain(export.main)


def Enroller():
  from grr.worker import enroller
  SetConfigOptions()
  flags.StartMain(enroller.main)


def Worker():
  from grr.worker import worker
  SetConfigOptions()
  flags.StartMain(worker.main)


def GRRFuse():
  from grr.tools import fuse_mount
  SetConfigOptions()
  flags.StartMain(fuse_mount.main)


def Client():
  from grr.client import client
  # Note client doesn't call SetConfigOptions as this entry point is primarily
  # used for testing on the server.
  flags.StartMain(client.main)


def AdminUI():
  from grr.gui import admin_ui
  SetConfigOptions()
  flags.StartMain(admin_ui.main)
