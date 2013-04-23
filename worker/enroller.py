#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.
"""A special worker responsible for initial enrollment of clients."""


import re
import sys


from M2Crypto import RSA
from M2Crypto import X509

from grr.client import conf

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import startup

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

  # Try to load the CA key.
  registry.CA_KEY = RSA.load_key_string(config_lib.CONFIG["PrivateKeys.ca_key"])
  registry.CA_CERT = X509.load_cert_string(config_lib.CONFIG["CA.certificate"])

  # Start an Enroler.
  token = access_control.ACLToken("GRREnroller", "Implied.")
  worker = flow.GRREnroler(
      queue_name=config_lib.CONFIG["Enroller.queue_name"], token=token)

  worker.Run()


if __name__ == "__main__":
  conf.StartMain(main)
