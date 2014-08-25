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
import os
import re
import sys
import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order

import logging

from grr.endtoend_tests import base
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import config_lib
from grr.lib import console_utils
from grr.lib import data_store
from grr.lib import export_utils
from grr.lib import flags
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import flow_utils
from grr.lib import hunts
from grr.lib import ipshell
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import search
from grr.lib import startup
from grr.lib import type_info
from grr.lib import utils
from grr.lib import worker

from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import reports
from grr.lib.aff4_objects import security

# All the functions in this lib we want in local namespace.
from grr.lib.console_utils import *

from grr.lib.flows import console
from grr.lib.flows.console import debugging
from grr.lib.flows.general import memory
# pylint: enable=unused-import

from grr.tools import end_to_end_tests


flags.DEFINE_string("client", None,
                    "Initialise the console with this client id "
                    "(e.g. C.1234345).")

flags.DEFINE_string("reason", None,
                    "Create a default token with this access reason ")

flags.DEFINE_string("code_to_execute", None,
                    "If present, no console is started but the code given in "
                    "the flag is run instead (comparable to the -c option of "
                    "IPython).")


def Help():
  """Print out help information."""
  print "Help is not implemented yet"


def Lister(arg):
  for x in arg:
    print x


def main(unused_argv):
  """Main."""
  banner = ("\nWelcome to the GRR console\n"
            "Type help<enter> to get help\n\n")

  config_lib.CONFIG.AddContext("Commandline Context")
  config_lib.CONFIG.AddContext(
      "Console Context",
      "Context applied when running the console binary.")
  startup.Init()

  # To make the console easier to use, we make a default token which will be
  # used in StartFlow operations.
  data_store.default_token = rdfvalue.ACLToken(username=getpass.getuser(),
                                               reason=flags.FLAGS.reason)

  locals_vars = {
      "hilfe": Help,
      "help": Help,
      "__name__": "GRR Console",
      "l": Lister,
      "o": aff4.FACTORY.Open,

      # Bring some symbols from other modules into the console's
      # namespace.
      "StartFlowAndWait": flow_utils.StartFlowAndWait,
      "StartFlowAndWorker": debugging.StartFlowAndWorker,
      "RunEndToEndTests": end_to_end_tests.RunEndToEndTests,
      }

  locals_vars.update(globals())   # add global variables to console
  if flags.FLAGS.client is not None:
    locals_vars["client"], locals_vars["token"] = console_utils.OpenClient(
        client_id=flags.FLAGS.client)

  if flags.FLAGS.code_to_execute:
    logging.info("Running code from flag: %s", flags.FLAGS.code_to_execute)
    exec(flags.FLAGS.code_to_execute)  # pylint: disable=exec-used
  else:
    ipshell.IPShell(argv=[], user_ns=locals_vars, banner=banner)


if __name__ == "__main__":
  flags.StartMain(main)
