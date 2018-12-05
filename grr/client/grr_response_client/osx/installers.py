#!/usr/bin/env python
"""These are osx specific installers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import zipfile

from grr_response_client import installer
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import type_info


class OSXInstaller(installer.Installer):
  """Tries to find an existing certificate and copies it to the config."""

  def ExtractConfig(self):
    """This installer extracts a config file from the .pkg file."""
    logging.info("Extracting config file from .pkg.")
    pkg_path = os.environ.get("PACKAGE_PATH", None)
    if pkg_path is None:
      logging.error("Could not locate package, giving up.")
      return

    zf = zipfile.ZipFile(pkg_path, mode="r")
    fd = zf.open("config.yaml")
    install_dir = os.path.dirname(config.CONFIG.parser.filename)

    # We write this config to disk so that Intialize can find the build.yaml
    # referenced inside the config as a relative path. This config isn't used
    # after install time.
    installer_config = os.path.join(install_dir, "installer_config.yaml")
    with open(installer_config, "wb") as f:
      f.write(fd.read())

    packaged_config = config.CONFIG.MakeNewConfig()
    packaged_config.Initialize(
        filename=installer_config, parser=config_lib.YamlParser)

    new_config = config.CONFIG.MakeNewConfig()
    new_config.SetWriteBack(config.CONFIG["Config.writeback"])

    for info in config.CONFIG.type_infos:
      try:
        new_value = packaged_config.GetRaw(info.name, None)
      except type_info.TypeValueError:
        continue

      try:
        old_value = config.CONFIG.GetRaw(info.name, None)

        if not new_value or new_value == old_value:
          continue
      except type_info.TypeValueError:
        pass

      new_config.SetRaw(info.name, new_value)

    new_config.Write()
    logging.info("Config file extracted successfully.")

    logging.info("Extracting additional files.")

    for zinfo in zf.filelist:
      basename = os.path.basename(zinfo.filename)
      if basename != "config.yaml":
        with open(os.path.join(install_dir, basename), "wb") as f:
          f.write(zf.open(zinfo.filename).read())

  def Run(self):
    self.ExtractConfig()
