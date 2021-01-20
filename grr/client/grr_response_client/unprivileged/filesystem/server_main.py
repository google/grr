#!/usr/bin/env python
"""Entry point of filesystem server."""

from absl import app

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.filesystem import server_lib


def main(argv):
  communication.Main(int(argv[1]), server_lib.Dispatch)


if __name__ == "__main__":
  app.run(main)
