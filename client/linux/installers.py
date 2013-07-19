#!/usr/bin/env python
"""The Linux specific installers."""



import re

import logging

from grr.client import installer
from grr.lib import config_lib


class UpdateClients(installer.Installer):
  """Copy configuration from old clients."""

  def Run(self):
    """The actual run method."""

    old_config_file = config_lib.CONFIG.Get("Installer.old_writeback")
    if not old_config_file:
      return

    logging.info("Copying old configuration from %s", old_config_file)

    new_config = config_lib.CONFIG.MakeNewConfig()
    new_config.SetWriteBack(config_lib.CONFIG["Config.writeback"])

    try:
      data = open(old_config_file, "rb").read()
      m = re.search(
          ("certificate ?= ?(-----BEGIN PRIVATE KEY-----[^-]*"
           "-----END PRIVATE KEY-----)"),
          data, flags=re.DOTALL)
      if m:
        cert = m.group(1).replace("\t", "")
        logging.info("Found a valid private key!")
        new_config.Set("Client.private_key", cert)
        new_config.Write()
    except IOError:
      logging.info("Previous config file not found.")
