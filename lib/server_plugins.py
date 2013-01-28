#!/usr/bin/env python
"""Centralized import point for server plugins.

This acts as a centralized point for modules that need to be loaded for
the server components so that the registry.Init() function will find and
register them.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.

# Note for gui specific plugins see gui/gui_plugins.py
"""

# pylint: disable=W0611

from grr.client import client_config

from grr import artifacts
from grr.lib import access_control
from grr.lib import aff4_objects
from grr.lib import config_lib
from grr.lib import data_stores
from grr.lib import flow
from grr.lib import hunts
from grr.lib import server_flags
from grr.lib import stats
from grr.lib.flows import general
