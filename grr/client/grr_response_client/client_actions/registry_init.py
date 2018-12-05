#!/usr/bin/env python
"""A module to load all client plugins."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# pylint: disable=unused-import,g-bad-import-order
import logging

# These imports populate the Action registry
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import rdfvalues
from grr_response_client import actions
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import artifact_collector
from grr_response_client.client_actions import cloud
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
