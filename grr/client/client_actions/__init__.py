#!/usr/bin/env python
"""A module to load all client plugins."""


# pylint: disable=unused-import,g-bad-import-order
import platform

import logging

# These imports populate the Action registry
from grr.lib import rdfvalue
from grr.lib import rdfvalues
from grr.client import actions
from grr.client.client_actions import admin
from grr.client.client_actions import components
from grr.client.client_actions import enrol
from grr.client.client_actions import file_fingerprint
from grr.client.client_actions import network
from grr.client.client_actions import plist
from grr.client.client_actions import searching
from grr.client.client_actions import standard
from grr.client.client_actions import tempfiles

# pylint: disable=g-import-not-at-top
# pylint: disable=g-wrong-blank-lines

if platform.system() == "Linux":
  from grr.client.client_actions import linux
elif platform.system() == "Windows":
  from grr.client.client_actions import windows
elif platform.system() == "Darwin":
  from grr.client.client_actions import osx
