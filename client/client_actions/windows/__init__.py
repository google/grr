#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""A module to load all windows client plugins."""


# pylint: disable=W0611,C6204

# These import populate the Action registry
import platform

if platform.system() == "Windows":
  from grr.client.client_actions.windows import windows
