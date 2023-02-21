#!/usr/bin/env python
"""Tests for grr.lib.repacking."""


import glob
import os
import shutil
import zipfile

from absl import app
import yaml

from grr_response_client_builder import build
from grr_response_client_builder import build_helpers
from grr_response_client_builder import repacking
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import package
from grr_response_core.lib import utils
from grr.test_lib import test_lib


class RepackingTests(test_lib.GRRBaseTest):
  """Tests for maintenance utils functionality."""

  @test_lib.RequiresPackage("grr-response-templates")
  def testRepackAll(self):
    """Test repacking all binaries."""
    self.executables_dir = package.ResourcePath("grr-response-core",
                                                "executables")
    with utils.TempDirectory() as tmp_dir:
      new_dir = os.path.join(tmp_dir, "grr", "executables")
      os.makedirs(new_dir)

      # Copy unzipsfx so it can be used in repacking/
      shutil.copy(
          os.path.join(self.executables_dir,
                       "windows/templates/unzipsfx/unzipsfx-i386.exe"), new_dir)
      shutil.copy(
          os.path.join(self.executables_dir,
                       "windows/templates/unzipsfx/unzipsfx-amd64.exe"),
          new_dir)

      with test_lib.ConfigOverrider({
          "ClientBuilder.executables_dir": new_dir,
          "ClientBuilder.unzipsfx_stub_dir": new_dir
      }):
        repacking.TemplateRepacker().RepackAllTemplates()

      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "installers/*.deb"))), 2)
      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "installers/*.rpm"))), 2)
      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "installers/*.exe"))), 4)
      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "installers/*.pkg"))), 1)

      # Validate the config appended to the OS X package.
      zf = zipfile.ZipFile(
          glob.glob(os.path.join(new_dir, "installers/*.pkg")).pop(), mode="r")
      fd = zf.open("config.yaml")

      # We can't load the included build.yaml because the package hasn't been
      # installed.
      loaded = yaml.safe_load(fd)
      loaded.pop("Config.includes")

      packaged_config = config.CONFIG.MakeNewConfig()
      data = yaml.safe_dump(loaded)
      packaged_config.Initialize(parser=config_lib.YamlParser, data=data)
      packaged_config.Validate(sections=build.ClientRepacker.CONFIG_SECTIONS)
      build_helpers.ValidateEndConfig(packaged_config)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
