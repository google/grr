#!/usr/bin/env python
"""Entry point of filesystem server."""

from absl import flags

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged import interface_registry

flags.DEFINE_integer(
    "unprivileged_server_pipe_input", -1,
    "The file descriptor of the input pipe used for communication.")

flags.DEFINE_integer(
    "unprivileged_server_pipe_output", -1,
    "The file descriptor of the output pipe used for communication.")

flags.DEFINE_string("unprivileged_server_interface", "",
                    "The name of the RPC interface used.")

flags.DEFINE_string("unprivileged_user", "",
                    "Name of user to run unprivileged server as.")

flags.DEFINE_string("unprivileged_group", "",
                    "Name of group to run unprivileged server as.")


def main(argv):
  del argv
  communication.Main(
      communication.Channel.FromSerialized(
          pipe_input=flags.FLAGS.unprivileged_server_pipe_input,
          pipe_output=flags.FLAGS.unprivileged_server_pipe_output),
      interface_registry.GetConnectionHandlerForInterfaceString(
          flags.FLAGS.unprivileged_server_interface),
      flags.FLAGS.unprivileged_user, flags.FLAGS.unprivileged_group)
