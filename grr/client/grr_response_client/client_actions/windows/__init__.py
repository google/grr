#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""A module to load all windows client plugins."""

# pylint: disable=unused-import,g-import-not-at-top

# These import populate the Action registry
import platform

if platform.system() == "Windows":
  from grr_response_client.client_actions.windows import windows
