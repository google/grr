#!/usr/bin/env python
"""Centralized import point for server plugins.

This acts as a centralized point for modules that need to be loaded for
the server components so that the server_startup.Init() function will find and
register them.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.

# Note for gui specific plugins see gui/gui_plugins.py
"""
# pylint: disable=unused-import
from grr.lib import stats
from grr.lib.local import plugins
from grr.parsers import registry_init

from grr.server import server_plugins
