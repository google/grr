#!/usr/bin/env python
"""Centralized import point for client plugins.

This acts as a centralized point for modules that need to be loaded for
the client components so that the client_startup.Init() function will find and
register them.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.
"""

import sys

# pylint: disable=g-import-not-at-top,unused-import,g-bad-import-order
# Load the os specific modules.
if sys.platform == "win32":
  from grr_response_client.windows import registry_init as windows_registry_init

elif sys.platform == "darwin":
  from grr_response_client.osx import registry_init as osx_registry_init

elif "linux" in sys.platform:
  from grr_response_client.linux import registry_init as linux_registry_init

from grr_response_client import local
# pylint: enable=g-import-not-at-top,unused-import,g-bad-import-order


def RegisterPlugins():
  if sys.platform == "win32":
    windows_registry_init.RegisterPlugins()
