#!/usr/bin/env python
# Lint as: python3
r"""This is the GRR client for Fleetspeak enabled installations.
"""

from absl import app

from grr_response_client import client

if __name__ == "__main__":
  app.run(client.main)
