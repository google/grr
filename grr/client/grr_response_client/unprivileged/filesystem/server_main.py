#!/usr/bin/env python
"""Entry point of filesystem server."""

from absl import app

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.filesystem import server_lib


def main(argv):
  communication.Main(
      communication.Channel(pipe_input=int(argv[1]), pipe_output=int(argv[2])),
      server_lib.Dispatch)


if __name__ == "__main__":
  app.run(main)
