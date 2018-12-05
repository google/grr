#!/usr/bin/env python
"""Centralized import point for server plugins in gui directory.

This acts as a centralized point for modules that need to be loaded for
the GUI- and API-related code work.

This also acts as a sensible single place to add deployment specific plugin
modules that have been customized for your deployment.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# pylint: disable=unused-import

from grr_response_server.gui import api_call_robot_router
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui import api_labels_restricted_call_router
from grr_response_server.gui import local
