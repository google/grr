#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""A special worker responsible for initial enrollment of clients."""


import re
import sys


from grr.client import conf

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import startup
from grr.lib import worker

# Make sure we also load the enroller module
from grr.lib.flows.caenroll import ca_enroller
# pylint: enable=W0611


config_lib.DEFINE_string("Enroller.queue_name", "CA",
                         "The name of the queue for this worker.")


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.SetEnv("Environment.component", "Enroller")

  # Initialise everything.
  startup.Init()

  # Start an Enroler.
  token = access_control.ACLToken("GRREnroller", "Implied.")
  enroller = worker.GRREnroler(
      queue_name=config_lib.CONFIG["Enroller.queue_name"], token=token)

  enroller.Run()


if __name__ == "__main__":
  conf.StartMain(main)
