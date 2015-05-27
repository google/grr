#!/usr/bin/env python
"""Centralized import point for client plugins.

This acts as a centralized point for modules that need to be loaded for
the client components so that the startup.Init() function will find and
register them.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.
"""
import sys

# pylint: disable=g-import-not-at-top,unused-import,g-bad-import-order
# Load the os specific modules.
if sys.platform == "win32":
  from grr.client import windows

elif sys.platform == "darwin":
  from grr.client import osx

elif "linux" in sys.platform:
  from grr.client import linux

from grr.client import client_actions
from grr.client import comms
from grr.client import local
from grr.client import vfs_handlers
from grr.lib import log
from grr.lib.rdfvalues import registry_init

# Config definitions use Semantic Values from plugins.
from grr import config
