#!/usr/bin/env python
"""Client startup routines."""

from grr_response_client import client_logging
from grr_response_client.client_actions import registry_init
from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import config_lib


def ClientInit():
  """Run all startup routines for the client."""
  registry_init.RegisterClientActions()

  config_lib.SetPlatformArchContext()
  config_lib.ParseConfigCommandLine()

  client_logging.LogInit()

  if not config.CONFIG.ContextApplied(contexts.CLIENT_BUILD_CONTEXT):
    config.CONFIG.Persist("Client.proxy_servers")
    config.CONFIG.Persist("Client.tempdir_roots")
