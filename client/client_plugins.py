#!/usr/bin/env python
"""Centralized import point for client plugins.

This acts as a centralized point for modules that need to be loaded for
the client components so that the registry.Init() function will find and
register them.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.
"""
import sys

# pylint: disable=W0611
from grr.client import client_actions
from grr.client import comms
from grr.client import local
from grr.client import vfs_handlers
from grr.lib import log
from grr.lib import rdfvalues

# pylint: disable=g-import-not-at-top
# Load the os specific modules.
if sys.platform == "win32":
  from grr.client import windows

elif sys.platform == "darwin":
  from grr.client import osx
