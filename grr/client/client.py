#!/usr/bin/env python
"""This is the GRR client."""


import pdb

import logging

# pylint: disable=unused-import
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.client import comms
from grr.client import installer
# pylint: disable=unused-import
from grr.client import stdlib
# pylint: enable=unused-import
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup

flags.DEFINE_bool("install", False, "Specify this to install the client.")

flags.DEFINE_bool("break_on_start", False,
                  "If True break into a pdb shell immediately on startup. This"
                  " can be used for debugging the client manually.")

flags.DEFINE_bool("debug_client_actions", False,
                  "If True break into a pdb shell before executing any client"
                  " action.")


def main(unused_args):
  # Allow per platform configuration.
  config_lib.CONFIG.AddContext(
      "Client Context", "Context applied when we run the client process.")

  startup.ClientInit()

  if flags.FLAGS.install:
    installer.RunInstaller()

  errors = config_lib.CONFIG.Validate(["Client", "CA", "Logging"])

  if errors and errors.keys() != ["Client.private_key"]:
    raise config_lib.ConfigFormatError(errors)

  enrollment_necessary = not config_lib.CONFIG.Get("Client.private_key")
  # Instantiating the client will create a private_key so we need to use a flag.
  client = comms.GRRHTTPClient(
      ca_cert=config_lib.CONFIG["CA.certificate"],
      private_key=config_lib.CONFIG.Get("Client.private_key",
                                        default=None))

  if enrollment_necessary:
    logging.info("No private key found, starting enrollment.")
    client.InitiateEnrolment()

  if flags.FLAGS.break_on_start:
    pdb.set_trace()
  else:
    client.Run()


if __name__ == "__main__":
  flags.StartMain(main)
