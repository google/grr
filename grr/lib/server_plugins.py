#!/usr/bin/env python
"""Centralized import point for server plugins.

This acts as a centralized point for modules that need to be loaded for
the server components so that the startup.Init() function will find and
register them.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.

# Note for gui specific plugins see gui/gui_plugins.py
"""
# pylint: disable=unused-import,g-import-not-at-top

# Server code needs to know about client actions as well.
from grr.client import client_plugins

from grr.lib import access_control
from grr.lib import client_compatibility
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import hunts
from grr.lib import ip_resolver
from grr.lib import local
from grr.lib import master
from grr.lib import output_plugin
from grr.lib import output_plugins
from grr.lib import stats
from grr.lib.aff4_objects import registry_init
from grr.lib.blob_stores import registry_init
from grr.lib.data_stores import registry_init
from grr.lib.flows.cron import registry_init
from grr.lib.flows.general import registry_init

from grr.parsers import registry_init

from grr.server import server_plugins
