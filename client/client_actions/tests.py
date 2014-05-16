#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Loads up all client action tests."""

import platform

import logging

# pylint: disable=unused-import
# pylint: disable=g-import-not-at-top
# These import populate the action test registry
from grr.client.client_actions import admin_test
from grr.client.client_actions import file_fingerprint_test
from grr.client.client_actions import plist_test
from grr.client.client_actions import searching_test
from grr.client.client_actions import standard_test
from grr.client.client_actions import tempfiles_test

# TODO(user): Volatility is deprecated, remove this as soon as Rekall is
# rolled out.
try:
  from grr.client.client_actions import grr_volatility
  from grr.client.client_actions import grr_volatility_test
except ImportError:
  pass

# Enable the Rekall specific client actions only if Rekall is installed.
try:
  from grr.client.client_actions import grr_rekall
  from grr.client.client_actions import grr_rekall_test
except ImportError:
  logging.warning("Could not import Rekall, memory analysis will not work.")

if platform.system() == "Darwin":
  from grr.client.client_actions.osx import osx_test
