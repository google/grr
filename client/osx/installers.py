#!/usr/bin/env python
"""These are osx specific installers."""
import os
import re
import zipfile

import logging

from grr.client import installer
from grr.lib import config_lib


config_lib.DEFINE_string(
    name="Client.prev_config_file", default="",
    help="Where to copy the client certificate from.")


class OSXInstaller(installer.Installer):
  """Tries to find an existing certificate and copies it to the config."""

  def CopySystemCert(self):
    """Makes a copy of the client private key."""
    config_url = config_lib.CONFIG["Client.prev_config_file"]
    if not config_url:
      return
    logging.info("Copying old configuration from %s", config_url)

    data = open(config_url, "rb").read()
    m = re.search(
        ("certificate ?= ?(-----BEGIN PRIVATE KEY-----[^-]*"
         "-----END PRIVATE KEY-----)"),
        data, flags=re.DOTALL)
    if m:
      cert = m.group(1).replace("\t", "")

      logging.info("Found a valid private key!")

      config_lib.CONFIG.Set("Client.private_key", cert)
      config_lib.CONFIG.Write()

  def ExtractConfig(self):
    """This installer extracts a config file from the .pkg file."""
    logging.info("Extracting config file from .pkg.")
    pkg_path = os.environ.get("PACKAGE_PATH", None)
    if pkg_path is None:
      logging.error("Could not locate package, giving up.")
      return

    zf = zipfile.ZipFile(pkg_path, mode="r")
    fd = zf.open("config.txt")

    parser = config_lib.ConfigFileParser(fd=fd)
    config_lib.CONFIG.MergeData(parser.RawData())
    config_lib.CONFIG.Write()
    logging.info("Config file extracted successfully.")

  def Run(self):
    self.ExtractConfig()
    self.CopySystemCert()
