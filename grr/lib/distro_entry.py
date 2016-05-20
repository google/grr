#!/usr/bin/env python
"""This file defines the entry points for typical installations."""

# Imports must be inline to stop argument pollution across the entry points.
# pylint: disable=g-import-not-at-top
import os

from grr import defaults
from grr.lib import config_lib
from grr.lib import flags


def SetConfigOptions():
  """Set location of configuration flags.

  All GRR tools must use the same configuration files so they could all work
  together. This needs to happen even before the configuration subsystem is
  loaded so it must be bootstrapped by this code (all other options are
  tweakable via the configuration system).

  There are two main parts for the config system:

  1) The main config file is shipped with the package and controls general
     parameters. Note that this file is highly dependent on the exact version of
     the grr package which is using it because it might have options which are
     not understood by another version. We typically always use the config file
     from package resources because in most cases this is the right thing to do
     as this file matches exactly the running version. If you really have a good
     reason you can override with the --config flag.

  2) The writeback location. If any GRR component updates the configuration,
     changes will be written back to a different locally modified config
     file. This file specifies overrides of the main configuration file. The
     main reason is that typically the same locally written config file may be
     used with multiple versions of the GRR server because it specifies a very
     small and rarely changing set of options.

  """
  config_opts = {}
  flag_defaults = {}

  # Allow the installer to override the platform defaults for the location of
  # the writeback config file. The writeback config file is therefore searched
  # in the following order:

  # 1. Specified on the command line with the "--config XXXX" option.
  # 2. Specified in the environment variable GRR_CONFIG_FILE.
  # 3. Specified during installation with:
  #     "python setup.py install --config-file=XXXX"
  # 4. Use the default config file from the grr-response package.
  if os.environ.get("GRR_CONFIG_FILE"):
    flag_defaults["config"] = os.environ.get("GRR_CONFIG_FILE")

  elif defaults.CONFIG_FILE:
    flag_defaults["config"] = defaults.CONFIG_FILE

  else:
    flag_defaults["config"] = config_lib.Resource().Filter(
        "install_data/etc/grr-server.yaml")

  for option, value in config_opts.items():
    config_lib.CONFIG.Set(option, value)

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


def DataServer():
  from grr.server.data_server import data_server
  SetConfigOptions()
  flags.StartMain(data_server.main)
