#!/usr/bin/env python
"""A module to load all client plugins."""

# pylint: disable=unused-import,g-bad-import-order
import logging

# These imports populate the Action registry
from grr.lib import rdfvalue
from grr.lib import rdfvalues
from grr_response_client import actions
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import cloud
from grr_response_client.client_actions import components
from grr_response_client.client_actions import enrol
from grr_response_client.client_actions import file_finder
from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import network
from grr_response_client.client_actions import operating_system
from grr_response_client.client_actions import plist
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_client.client_actions import tempfiles
from grr_response_client.client_actions import yara_actions

# Former GRR component, now a built-in part of the client.
from grr_response_client.components.rekall_support import grr_rekall

from grr_response_client.client_actions import osquery_actions