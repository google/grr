#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Loads up all client action tests."""

# pylint: disable=unused-import
import logging

# These import populate the action test registry
from grr.client.client_actions import action_test
from grr.client.client_actions import admin_test
from grr.client.client_actions import components_test
from grr.client.client_actions import file_fingerprint_test
from grr.client.client_actions import plist_test
from grr.client.client_actions import searching_test
from grr.client.client_actions import standard_test
from grr.client.client_actions import tempfiles_test
from grr.client.client_actions.osx import osx_test
from grr.client.client_actions.windows import windows_test
