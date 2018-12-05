#!/usr/bin/env python
"""This file defines the entry points for the client."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags

# pylint: disable=g-import-not-at-top


def ClientBuild():
  from grr_response_client import client_build
  flags.StartMain(client_build.main)


def Client():
  from grr_response_client import client
  flags.StartMain(client.main)


def FleetspeakClient():
  from grr_response_client import grr_fs_client
  flags.StartMain(grr_fs_client.main)


def PoolClient():
  from grr_response_client import poolclient
  flags.StartMain(poolclient.main)
