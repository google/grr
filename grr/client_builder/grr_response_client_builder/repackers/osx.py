#!/usr/bin/env python
"""MacOS client repackers."""

import contextlib
import os
import shutil
import zipfile


from grr_response_client_builder import build
from grr_response_client_builder import build_helpers
from grr_response_client_builder import pkg_utils

from grr_response_core import config
from grr_response_core.lib import utils


class DarwinClientRepacker(build.ClientRepacker):
  """Repackage OSX clients."""

  def MakeDeployableBinary(self, template_path, output_path):
    context = self.context + ["Client Context"]
    utils.EnsureDirExists(os.path.dirname(output_path))

    fleetspeak_bundled = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_bundled", context=self.context)

    with contextlib.ExitStack() as stack:
      tmp_dir = stack.enter_context(utils.TempDirectory())
      shutil.unpack_archive(template_path, tmp_dir, format="zip")

      if fleetspeak_bundled:
        variant = "fleetspeak-bundled"
      else:
        variant = "fleetspeak-enabled"

      pkg_utils.JoinPkg(
          os.path.join(tmp_dir, variant), os.path.join(tmp_dir, "blocks"),
          output_path)

      zf = stack.enter_context(zipfile.ZipFile(output_path, mode="a"))
      with open(os.path.join(tmp_dir, "build.yaml"), "r") as build_yaml_file:
        zf.writestr("build.yaml", build_yaml_file.read())

      client_config_data = build_helpers.GetClientConfig(context)
      zf.writestr("config.yaml", client_config_data)

      if fleetspeak_bundled:
        fleetspeak_client_config = config.CONFIG.Get(
            "ClientBuilder.fleetspeak_client_config", context=self.context)
        with open(fleetspeak_client_config,
                  "r") as fleetspeak_client_config_file:
          zf.writestr("client.config", fleetspeak_client_config_file.read())

    return output_path
