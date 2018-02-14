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
  from grr_response_client import windows

elif sys.platform == "darwin":
  from grr_response_client import osx

elif "linux" in sys.platform:
  from grr_response_client import linux

from grr_response_client import client_actions
from grr_response_client import comms
from grr_response_client import local
from grr_response_client import vfs_handlers
# pylint: enable=g-import-not-at-top,unused-import,g-bad-import-order
