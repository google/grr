#!/usr/bin/env python
"""Centralized import point for gui plugins.

This acts as a centralized point for modules that need to be loaded for
the gui so that the startup.Init() function will find and register them.

This also acts as a sensible single place to add deployment specific gui plugin
modules that have been customized for your deployment.
"""

# pylint: disable=unused-import
from grr.gui import api_call_robot_router
from grr.gui import api_call_router_with_approval_checks
from grr.gui import api_call_router_without_checks

from grr.gui import api_plugins
from grr.gui import local
from grr.gui import plugins
from grr.gui import renderers
from grr.gui import urls
from grr.gui import views
