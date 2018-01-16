#!/usr/bin/env python
"""This is the GRR Console.

We can schedule a new flow for a specific client.
"""

# pylint: disable=unused-import
# Import things that are useful from the console.
import collections
import csv
import datetime
import getpass
import logging
import os
import re
import sys
import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order

from grr import config
from grr.config import contexts
from grr.lib import flags
from grr.lib import fleetspeak_connector
from grr.lib import type_info
from grr.lib import utils
from grr.server import access_control
from grr.server import aff4
from grr.server import artifact
from grr.server import artifact_utils
from grr.server import console_utils
from grr.server import data_store
from grr.server import export_utils
from grr.server import flow
from grr.server import flow_runner
from grr.server import flow_utils
from grr.server import hunts
from grr.server import ipshell
from grr.server import maintenance_utils
from grr.server import server_startup
from grr.server import worker
from grr.server.aff4_objects import aff4_grr
from grr.server.aff4_objects import security

# All the functions in this lib we want in local namespace.
# pylint: disable=wildcard-import
from grr.server.console_utils import *
# pylint: enable=wildcard-import

from grr.server.flows import console
from grr.server.flows.console import debugging
from grr.server.flows.general import memory
# pylint: enable=unused-import

flags.DEFINE_string("client", None,
                    "Initialise the console with this client id "
                    "(e.g. C.1234345).")

flags.DEFINE_string("reason", None,
                    "Create a default token with this access reason ")

flags.DEFINE_string("code_to_execute", None,
                    "If present, no console is started but the code given in "
                    "the flag is run instead (comparable to the -c option of "
                    "IPython).")

flags.DEFINE_string("command_file", None,
                    "If present, no console is started but the code given in "
                    "command file is supplied as input instead.")

flags.DEFINE_bool("exit_on_complete", True,
                  "If set to False and command_file or code_to_execute is "
                  "set we keep the console alive after the code completes.")


def Lister(arg):
  for x in arg:
    print x


def GetChildrenList(urn, token=None):
  return list(aff4.FACTORY.Open(urn, token=token).ListChildren())


def main(argv):
  """Main."""
  del argv  # Unused.
  banner = ("\nWelcome to the GRR console\n")

  config.CONFIG.AddContext(contexts.COMMAND_LINE_CONTEXT)
  config.CONFIG.AddContext(contexts.CONSOLE_CONTEXT,
                           "Context applied when running the console binary.")
  server_startup.Init()

  fleetspeak_connector.Init()

  # To make the console easier to use, we make a default token which will be
  # used in StartFlow operations.
  data_store.default_token = access_control.ACLToken(
      username=getpass.getuser(), reason=flags.FLAGS.reason)

  locals_vars = {
      "__name__": "GRR Console",
      "l": Lister,
      "lc": GetChildrenList,
      "o": aff4.FACTORY.Open,

      # Bring some symbols from other modules into the console's
      # namespace.
      "StartFlowAndWait": flow_utils.StartFlowAndWait,
      "StartFlowAndWorker": debugging.StartFlowAndWorker,
  }

  locals_vars.update(globals())  # add global variables to console
  if flags.FLAGS.client is not None:
    locals_vars["client"], locals_vars["token"] = console_utils.OpenClient(
        client_id=flags.FLAGS.client)

  if flags.FLAGS.code_to_execute:
    logging.info("Running code from flag: %s", flags.FLAGS.code_to_execute)
    exec (flags.FLAGS.code_to_execute)  # pylint: disable=exec-used
  elif flags.FLAGS.command_file:
    logging.info("Running code from file: %s", flags.FLAGS.command_file)
    execfile(flags.FLAGS.command_file)

  if (flags.FLAGS.exit_on_complete and
      (flags.FLAGS.code_to_execute or flags.FLAGS.command_file)):
    return

  else:  # We want the normal shell.
    locals_vars.update(globals())  # add global variables to console
    ipshell.IPShell(argv=[], user_ns=locals_vars, banner=banner)


if __name__ == "__main__":
  flags.StartMain(main)
