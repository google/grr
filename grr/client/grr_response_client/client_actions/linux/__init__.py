#!/usr/bin/env python
"""A module to load all linux client plugins."""

# pylint: disable=unused-import
# These import populate the Action registry
from grr_response_client.client_actions.linux import linux
# Former GRR component, now built-in part of the client.
from grr_response_client.components.chipsec_support.actions import grr_chipsec
