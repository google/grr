#!/usr/bin/env python
"""This is the GRR Console.

We can schedule a new flow for a specific client.
"""

import logging

from absl import app
from absl import flags

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

_CODE_TO_EXECUTE = flags.DEFINE_string(
    "code_to_execute", None,
    "If present, no console is started but the code given in "
    "the flag is run instead (comparable to the -c option of "
    "IPython).")

_COMMAND_FILE = flags.DEFINE_string(
    "command_file", None,
    "If present, no console is started but the code given in "
    "command file is supplied as input instead.")

_EXIT_ON_COMPLETE = flags.DEFINE_bool(
    "exit_on_complete", True,
    "If set to False and command_file or code_to_execute is "
    "set we keep the console alive after the code completes.")

_VERSION = flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR console version number and exit immediately.")


def main(argv):
  """Main."""
  del argv  # Unused.

  if _VERSION.value:
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

  if _CODE_TO_EXECUTE.value:
    logging.info("Running code from flag: %s", _CODE_TO_EXECUTE.value)
    exec(_CODE_TO_EXECUTE.value)  # pylint: disable=exec-used
  elif _COMMAND_FILE.value:
    logging.info("Running code from file: %s", _COMMAND_FILE.value)
    with open(_COMMAND_FILE.value, "r") as filedesc:
      exec(filedesc.read())  # pylint: disable=exec-used

  if (_EXIT_ON_COMPLETE.value and
      (_CODE_TO_EXECUTE.value or _COMMAND_FILE.value)):
    return

  else:  # We want the normal shell.
    locals_vars.update(globals())  # add global variables to console
    ipshell.IPShell(argv=[], user_ns=locals_vars, banner=banner)


if __name__ == "__main__":
  app.run(main)
