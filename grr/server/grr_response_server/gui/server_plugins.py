#!/usr/bin/env python
"""Centralized import point for server plugins in gui directory.

This acts as a centralized point for modules that need to be loaded for
the GUI- and API-related code work.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.
"""

# pylint: disable=unused-import

from grr.server.grr_response_server.gui import api_call_robot_router
from grr.server.grr_response_server.gui import api_call_router
from grr.server.grr_response_server.gui import api_call_router_with_approval_checks
from grr.server.grr_response_server.gui import api_call_router_without_checks
from grr.server.grr_response_server.gui import api_labels_restricted_call_router
from grr.server.grr_response_server.gui import local
