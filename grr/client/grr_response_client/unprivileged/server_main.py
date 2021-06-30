#!/usr/bin/env python
"""Entry point of filesystem server."""

from absl import app

from grr_response_client.unprivileged import server_main_lib

if __name__ == "__main__":
  app.run(server_main_lib.main)
