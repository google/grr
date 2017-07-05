#!/usr/bin/env python
"""A module to load all client plugins."""


# pylint: disable=unused-import,g-bad-import-order
import logging

# These imports populate the Action registry
from grr.lib import rdfvalue
from grr.lib import rdfvalues
from grr.client import actions
from grr.client.client_actions import admin
from grr.client.client_actions import cloud
from grr.client.client_actions import components
from grr.client.client_actions import enrol
from grr.client.client_actions import file_finder
from grr.client.client_actions import file_fingerprint
from grr.client.client_actions import network
from grr.client.client_actions import operating_system
from grr.client.client_actions import plist
from grr.client.client_actions import searching
from grr.client.client_actions import standard
from grr.client.client_actions import tempfiles

# Former GRR component, now a built-in part of the client.
from grr.client.components.rekall_support import grr_rekall
