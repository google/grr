#!/usr/bin/env python
"""Centralized import point for server plugins in grr/server directory.

This acts as a centralized point for modules that need to be loaded for
the server components so that the server_startup.Init() function will find and
register them.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.
"""
# pylint: disable=unused-import

from grr.server import access_control
from grr.server import export
from grr.server import file_store
from grr.server import flow
from grr.server import foreman
from grr.server import hunts
from grr.server import ip_resolver
from grr.server import master
from grr.server import output_plugin
from grr.server import output_plugins
from grr.server import stats_server
from grr.server.aff4_objects import registry_init
from grr.server.blob_stores import registry_init
from grr.server.data_stores import registry_init
from grr.server.flows.cron import registry_init
from grr.server.flows.general import registry_init
from grr.server.flows.local import registry_init
from grr.server.local import registry_init
