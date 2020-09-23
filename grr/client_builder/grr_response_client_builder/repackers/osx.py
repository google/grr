#!/usr/bin/env python
"""MacOS client repackers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

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

  def _MakeDeployableBinaryV1(self, template_path, output_path):
    """This will add the config to the client template."""

    context = self.context + ["Client Context"]
    utils.EnsureDirExists(os.path.dirname(output_path))

    client_config_data = build_helpers.GetClientConfig(context)
    shutil.copyfile(template_path, output_path)
    zip_file = zipfile.ZipFile(output_path, mode="a")
    zip_info = zipfile.ZipInfo(filename="config.yaml")
    zip_file.writestr(zip_info, client_config_data)
    zip_file.close()
    return output_path

  def _MakeDeployableBinaryV2(self, template_path, output_path):
    context = self.context + ["Client Context"]
    utils.EnsureDirExists(os.path.dirname(output_path))

    fleetspeak_enabled = config.CONFIG.Get(
        "Client.fleetspeak_enabled", context=self.context)
    fleetspeak_bundled = config.CONFIG.Get(
        "ClientBuilder.fleetspeak_bundled", context=self.context)

    with contextlib.ExitStack() as stack:
      tmp_dir = stack.enter_context(utils.TempDirectory())
      shutil.unpack_archive(template_path, tmp_dir, format="zip")

      if fleetspeak_bundled:
        variant = "fleetspeak-bundled"
      elif fleetspeak_enabled:
        variant = "fleetspeak-enabled"
      else:
        variant = "legacy"

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

  def MakeDeployableBinary(self, template_path, output_path):
    with open(template_path, "rb") as template:
      is_v1 = (template.read(4) == b"xar!")
    if is_v1:
      return self._MakeDeployableBinaryV1(template_path, output_path)
    else:
      return self._MakeDeployableBinaryV2(template_path, output_path)
