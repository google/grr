#!/usr/bin/env python
"""This file defines the entry points for the client."""

from absl import app

# pylint: disable=g-import-not-at-top


def Client():
  from grr_response_client import client
  app.run(client.main)


def FleetspeakClient():
  from grr_response_client import grr_fs_client
  app.run(grr_fs_client.main)


def PoolClient():
  from grr_response_client import poolclient
  app.run(poolclient.main)
