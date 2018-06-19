#!/usr/bin/env python
"""This file defines the entry points for typical installations."""

# pylint: disable=g-import-not-at-top
# Argparse runs on import, and maintains static state.

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
  # The writeback config file is searched in the following order:

  # 1. Specified on the command line with the "--config XXXX" option.
  # 2. Use the default config file from the grr-response package.
  flags.PARSER.set_defaults(
      config=config_lib.Resource().Filter("install_data/etc/grr-server.yaml"))


def Console():
  from grr.server.grr_response_server.bin import console
  SetConfigOptions()
  flags.StartMain(console.main)


def ApiShellRawAccess():
  from grr.server.grr_response_server.bin import api_shell_raw_access
  SetConfigOptions()
  flags.StartMain(api_shell_raw_access.main)


def ConfigUpdater():
  from grr.server.grr_response_server.bin import config_updater
  SetConfigOptions()
  flags.StartMain(config_updater.main)


def GrrServer():
  from grr.server.grr_response_server.bin import grr_server
  SetConfigOptions()
  flags.StartMain(grr_server.main)


def GrrFrontend():
  from grr.server.grr_response_server.bin import frontend
  SetConfigOptions()
  flags.StartMain(frontend.main)


def Worker():
  from grr.server.grr_response_server.bin import worker
  SetConfigOptions()
  flags.StartMain(worker.main)


def GRRFuse():
  from grr.server.grr_response_server.bin import fuse_mount
  SetConfigOptions()
  flags.StartMain(fuse_mount.main)


def AdminUI():
  from grr.server.grr_response_server.gui import admin_ui
  SetConfigOptions()
  flags.StartMain(admin_ui.main)
