#!/usr/bin/env python
r"""This is the GRR client for Fleetspeak enabled installations.
"""

import pdb

from grr import config

# pylint: disable=unused-import
from grr.client import client_plugins
# pylint: enable=unused-import

from grr.client import client_startup
from grr.client import fleetspeak_client
from grr.config import contexts
from grr.lib import flags

flags.DEFINE_bool("break_on_start", False,
                  "If True break into a pdb shell immediately on startup. This"
                  " can be used for debugging the client manually.")


def main(unused_args):
  config.CONFIG.AddContext(contexts.CLIENT_CONTEXT,
                           "Context applied when we run the client process.")

  client_startup.ClientInit()

  prod_client = fleetspeak_client.GRRFleetspeakClient()

  if flags.FLAGS.break_on_start:
    pdb.set_trace()
  else:
    prod_client.Run()


if __name__ == "__main__":
  flags.StartMain(main)
