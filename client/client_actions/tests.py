#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.

"""Loads up all client action tests."""

import platform

# pylint: disable=unused-import
# pylint: disable=g-import-not-at-top
# These import populate the action test registry
from grr.client.client_actions import admin_test
from grr.client.client_actions import file_fingerprint_test
from grr.client.client_actions import searching_test
from grr.client.client_actions import standard_test
from grr.client.client_actions import tempfiles_test

# Enable the volatility specific client actions only if volatility is installed.
try:
  from grr.client.client_actions import grr_volatility
  from grr.client.client_actions import grr_volatility_test
except ImportError:
  pass

if platform.system() == "Darwin":
  from grr.client.client_actions.osx import osx_test
