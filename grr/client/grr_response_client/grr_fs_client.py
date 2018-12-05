#!/usr/bin/env python
r"""This is the GRR client for Fleetspeak enabled installations.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import pdb

# pylint: disable=unused-import
from grr_response_client import client_plugins
# pylint: enable=unused-import

from grr_response_client import client_startup
from grr_response_client import fleetspeak_client
from grr_response_client import installer
from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import flags

flags.DEFINE_bool("install", False, "Specify this to install the client.")

flags.DEFINE_bool(
    "break_on_start", False,
    "If True break into a pdb shell immediately on startup. This"
    " can be used for debugging the client manually.")


def main(unused_args):
  config.CONFIG.AddContext(contexts.CLIENT_CONTEXT,
                           "Context applied when we run the client process.")

  client_startup.ClientInit()

  if flags.FLAGS.install:
    installer.RunInstaller()

  if not config.CONFIG["Client.fleetspeak_enabled"]:
    raise ValueError(
        "This is a Fleetspeak client, yet 'Client.fleetspeak_enabled' is "
        "'False'.")

  if flags.FLAGS.break_on_start:
    pdb.set_trace()
  else:
    fleetspeak_client.GRRFleetspeakClient().Run()


if __name__ == "__main__":
  flags.StartMain(main)
