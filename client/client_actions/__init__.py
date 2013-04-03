#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.

"""A module to load all client plugins."""


# pylint: disable=W0611,C6203
import platform

import logging

# These imports populate the Action registry
from grr.lib import rdfvalue
from grr.lib import rdfvalues
from grr.client import actions
from grr.client.client_actions import admin
from grr.client.client_actions import enrol
from grr.client.client_actions import file_fingerprint
from grr.client.client_actions import network
from grr.client.client_actions import searching
from grr.client.client_actions import standard

# pylint: disable=C6204
# pylint: disable=C6302

try:
  from grr.client.client_actions import grr_volatility
except ImportError:
  class VolatilityAction(actions.ActionPlugin):
    """Runs a volatility command on live memory."""
    in_rdfvalue = rdfvalue.VolatilityRequest
    out_rdfvalue = rdfvalue.VolatilityResult

if platform.system() == "Linux":
  from grr.client.client_actions import linux
elif platform.system() == "Windows":
  from grr.client.client_actions import windows
elif platform.system() == "Darwin":
  from grr.client.client_actions import osx
