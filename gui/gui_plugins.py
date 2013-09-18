#!/usr/bin/env python
"""Centralized import point for gui plugins.

This acts as a centralized point for modules that need to be loaded for
the gui so that the startup.Init() function will find and register them.

This also acts as a sensible single place to add deployment specific gui plugin
modules that have been customized for your deployment.
"""

# pylint: disable=unused-import

from grr.gui import plugins
from grr.gui import renderers
from grr.gui import urls
from grr.gui import views
