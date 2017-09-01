#!/usr/bin/env python
"""This file defines the entry points for the client."""

from grr.client import client
from grr.client import client_build
from grr.client import poolclient
from grr.lib import config_lib
from grr.lib import flags


def SetConfigOptions():
  """Sets the default value for the config flag."""
  flags.PARSER.set_defaults(
      config=config_lib.Resource().Filter("install_data/etc/grr-server.yaml"))


def ClientBuild():
  SetConfigOptions()
  flags.StartMain(client_build.main)


def Client():
  SetConfigOptions()
  flags.StartMain(client.main)


def PoolClient():
  SetConfigOptions()
  flags.StartMain(poolclient.main)
