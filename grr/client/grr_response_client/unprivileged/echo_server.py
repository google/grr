#!/usr/bin/env python
"""Simple echo server for testing.

The server receives data and an attachment and replies with:

* data + "x"
* attachment + "x"
"""

from absl import app

from grr_response_client.unprivileged import communication


def Handler(connection: communication.Connection):
  while True:
    recv_result = connection.Recv()
    connection.Send(
        communication.Message(recv_result.data + b"x",
                              recv_result.attachment + b"x"))


def main(argv):
  communication.Main(
      communication.Channel.FromSerialized(
          pipe_input=int(argv[1]), pipe_output=int(argv[2])),
      Handler,
      user="",
      group="")


if __name__ == "__main__":
  app.run(main)
