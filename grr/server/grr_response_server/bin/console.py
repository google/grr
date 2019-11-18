#!/usr/bin/env python
"""This is the GRR Console.

We can schedule a new flow for a specific client.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from absl import app
from absl import flags

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server

# This is a frequently used module. We import it here so it doesn't have
# to be manually imported when using the console.
#
# pylint: disable=unused-import
from grr_response_server import data_store
# pylint: enable=unused-import

from grr_response_server import fleetspeak_connector
from grr_response_server import ipshell
from grr_response_server import server_startup

flags.DEFINE_string(
    "code_to_execute", None,
    "If present, no console is started but the code given in "
    "the flag is run instead (comparable to the -c option of "
    "IPython).")

flags.DEFINE_string(
    "command_file", None,
    "If present, no console is started but the code given in "
    "command file is supplied as input instead.")

flags.DEFINE_bool(
    "exit_on_complete", True,
    "If set to False and command_file or code_to_execute is "
    "set we keep the console alive after the code completes.")

flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR console version number and exit immediately.")


def main(argv):
  """Main."""
  del argv  # Unused.

  if flags.FLAGS.version:
    print("GRR console {}".format(config_server.VERSION["packageversion"]))
    return

  banner = ("\nWelcome to the GRR console\n")

  config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT)
  config.CONFIG.AddContext(contexts.CONSOLE_CONTEXT,
                           "Context applied when running the console binary.")
  server_startup.Init()

  fleetspeak_connector.Init()

  locals_vars = {
      "__name__": "GRR Console",
  }

  locals_vars.update(globals())  # add global variables to console

  if flags.FLAGS.code_to_execute:
    logging.info("Running code from flag: %s", flags.FLAGS.code_to_execute)
    exec(flags.FLAGS.code_to_execute)  # pylint: disable=exec-used
  elif flags.FLAGS.command_file:
    logging.info("Running code from file: %s", flags.FLAGS.command_file)
    with open(flags.FLAGS.command_file, "r") as filedesc:
      exec(filedesc.read())  # pylint: disable=exec-used

  if (flags.FLAGS.exit_on_complete and
      (flags.FLAGS.code_to_execute or flags.FLAGS.command_file)):
    return

  else:  # We want the normal shell.
    locals_vars.update(globals())  # add global variables to console
    ipshell.IPShell(argv=[], user_ns=locals_vars, banner=banner)


if __name__ == "__main__":
  app.run(main)
