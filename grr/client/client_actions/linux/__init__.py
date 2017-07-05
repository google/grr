#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""A module to load all linux client plugins."""


# pylint: disable=unused-import
# These import populate the Action registry
from grr.client.client_actions.linux import linux
# Former GRR component, now built-in part of the client.
from grr.client.components.chipsec_support.actions import grr_chipsec
