#!/usr/bin/env python
"""This is the GRR client."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import pdb


from future.utils import iterkeys

# pylint: disable=unused-import
from grr_response_client import client_plugins
# pylint: enable=unused-import
from grr_response_client import client_startup
from grr_response_client import comms
from grr_response_client import installer
from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import config_lib
from grr_response_core.lib import flags

flags.DEFINE_bool("install", False, "Specify this to install the client.")

flags.DEFINE_bool(
    "break_on_start", False,
    "If True break into a pdb shell immediately on startup. This"
    " can be used for debugging the client manually.")

flags.DEFINE_bool(
    "debug_client_actions", False,
    "If True break into a pdb shell before executing any client"
    " action.")


def main(unused_args):
  # Allow per platform configuration.
  config.CONFIG.AddContext(contexts.CLIENT_CONTEXT,
                           "Context applied when we run the client process.")

  client_startup.ClientInit()

  if flags.FLAGS.install:
    installer.RunInstaller()

  errors = config.CONFIG.Validate(["Client", "CA", "Logging"])

  if errors and list(iterkeys(errors)) != ["Client.private_key"]:
    raise config_lib.ConfigFormatError(errors)

  if config.CONFIG["Client.fleetspeak_enabled"]:
    raise ValueError(
        "This is not a Fleetspeak client, yet 'Client.fleetspeak_enabled' is "
        "set to 'True'.")

  enrollment_necessary = not config.CONFIG.Get("Client.private_key")
  # Instantiating the client will create a private_key so we need to use a flag.
  client = comms.GRRHTTPClient(
      ca_cert=config.CONFIG["CA.certificate"],
      private_key=config.CONFIG.Get("Client.private_key", default=None))

  if enrollment_necessary:
    logging.info("No private key found, starting enrollment.")
    client.InitiateEnrolment()

  if flags.FLAGS.break_on_start:
    pdb.set_trace()
  else:
    client.Run()


if __name__ == "__main__":
  flags.StartMain(main)
