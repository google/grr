#!/usr/bin/env python
"""This file defines the entry points for the client."""

from absl import app

# pylint: disable=g-import-not-at-top


def FleetspeakClient():
  from grr_response_client import client

  app.run(client.main)


def FleetspeakClientWrapper():
  from grr_response_client import fleetspeak_client_wrapper

  app.run(fleetspeak_client_wrapper.main)
