#!/usr/bin/env python
"""This file defines the entry points for the client."""

# pylint: disable=g-import-not-at-top
# Argparse runs on import, and maintains static state.

from grr.lib import config_lib
from grr.lib import flags


def SetConfigOptions():
  """Sets the default value for the config flag."""
  flags.PARSER.set_defaults(
      config=config_lib.Resource().Filter("install_data/etc/grr-server.yaml"))


def ClientBuild():
  from grr.client import client_build
  SetConfigOptions()
  flags.StartMain(client_build.main)


def Client():
  from grr.client import client
  SetConfigOptions()
  flags.StartMain(client.main)


def PoolClient():
  from grr.client import poolclient
  SetConfigOptions()
  flags.StartMain(poolclient.main)
