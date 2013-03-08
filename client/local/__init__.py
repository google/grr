#!/usr/bin/env python
"""This directory contains local site-specific implementations."""
import os

from grr.lib import config_lib
from grr.lib import registry


config_lib.DEFINE_list("Client.plugins", [],
                       help="Plugins loaded by the client.")


class ClientPlugins(registry.InitHook):
  """Load plugins on the client."""

  def RunOnce(self):
    for plugin in config_lib.CONFIG["Client.plugins"]:
      config_lib.PluginLoader.LoadPlugin(
          os.path.join(config_lib.CONFIG["Client.install_path"],
                       plugin))

