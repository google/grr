#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Loads up all client action tests."""
import platform

# pylint: disable=unused-import,g-import-not-at-top

# These import populate the action test registry
from grr_response_client.client_actions import action_test
from grr_response_client.client_actions import admin_test
from grr_response_client.client_actions import cloud_test
from grr_response_client.client_actions import file_finder_test
from grr_response_client.client_actions import file_fingerprint_test
from grr_response_client.client_actions import network_test
from grr_response_client.client_actions import plist_test
from grr_response_client.client_actions import searching_test
from grr_response_client.client_actions import standard_test
from grr_response_client.client_actions import tempfiles_test
if platform.system() == "Linux":
  from grr_response_client.client_actions.linux import linux_test
from grr_response_client.client_actions.osx import osx_test
from grr_response_client.client_actions.windows import windows_test
