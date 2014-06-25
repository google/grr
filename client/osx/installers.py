#!/usr/bin/env python
"""These are osx specific installers."""
import os
import re
import zipfile

import logging

from grr.client import installer
from grr.lib import config_lib
from grr.lib import type_info


class OSXInstaller(installer.Installer):
  """Tries to find an existing certificate and copies it to the config."""

  def CopySystemCert(self):
    """Makes a copy of the client private key."""
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
      if not m:
        m = re.search(
            ("private_key ?= ?(-----BEGIN PRIVATE KEY-----[^-]*"
             "-----END PRIVATE KEY-----)"),
            data, flags=re.DOTALL)

      if m:
        cert = m.group(1).replace("\t", "")
        logging.info("Found a valid private key!")
        new_config.Set("Client.private_key", cert)
        new_config.Write()
    except IOError:
      # Nothing we can do here.
      logging.info("IO Error while opening %s", old_config_file)

  def ExtractConfig(self):
    """This installer extracts a config file from the .pkg file."""
    logging.info("Extracting config file from .pkg.")
    pkg_path = os.environ.get("PACKAGE_PATH", None)
    if pkg_path is None:
      logging.error("Could not locate package, giving up.")
      return

    zf = zipfile.ZipFile(pkg_path, mode="r")
    fd = zf.open("config.yaml")

    packaged_config = config_lib.CONFIG.MakeNewConfig()
    packaged_config.Initialize(fd=fd, parser=config_lib.YamlParser)

    new_config = config_lib.CONFIG.MakeNewConfig()
    new_config.SetWriteBack(config_lib.CONFIG["Config.writeback"])

    for info in config_lib.CONFIG.type_infos:
      try:
        new_value = packaged_config.GetRaw(info.name, None)
      except type_info.TypeValueError:
        continue

      try:
        old_value = config_lib.CONFIG.GetRaw(info.name, None)

        if not new_value or new_value == old_value:
          continue
      except type_info.TypeValueError:
        pass

      new_config.SetRaw(info.name, new_value)

    new_config.Write()
    logging.info("Config file extracted successfully.")

    logging.info("Extracting additional files.")

    install_dir = os.path.dirname(config_lib.CONFIG.parser.filename)
    for zinfo in zf.filelist:
      basename = os.path.basename(zinfo.filename)
      if basename != "config.yaml":
        with open(os.path.join(install_dir, basename), "wb") as f:
          f.write(zf.open(zinfo.filename).read())

  def Run(self):
    self.ExtractConfig()
    self.CopySystemCert()
