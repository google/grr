#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""A module to load all windows client plugins."""


# These import populate the Action registry
# pylint: disable=unused-import,g-import-not-at-top

import platform

if platform.system() == "Darwin":
  from grr_response_client.client_actions.osx import osx
