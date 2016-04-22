#!/usr/bin/env python
"""Tests for building and repacking clients."""
import glob
import os
import shutil

from grr.lib import build
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import maintenance_utils
from grr.lib import test_lib
from grr.lib import utils


class BuildTests(test_lib.GRRBaseTest):
  """Tests for building and repacking functionality."""

  def setUp(self):
    super(BuildTests, self).setUp()
    self.executables_dir = config_lib.Resource().Filter("executables")

  @test_lib.RequiresPackage("grr-response-templates")
  def testRepackAll(self):
    """Test repacking all binaries."""
    with utils.TempDirectory() as tmp_dir:
      new_dir = os.path.join(tmp_dir, "grr", "executables")
      os.makedirs(new_dir)

      # Copy unzipsfx so it can be used in repacking/
      shutil.copy(os.path.join(
          self.executables_dir, "windows/templates/unzipsfx/unzipsfx-i386.exe"),
                  new_dir)
      shutil.copy(os.path.join(
          self.executables_dir,
          "windows/templates/unzipsfx/unzipsfx-amd64.exe"), new_dir)

      with test_lib.ConfigOverrider({"ClientBuilder.executables_dir": new_dir}):
        with test_lib.ConfigOverrider(
            {"ClientBuilder.unzipsfx_stub_dir": new_dir}):
          maintenance_utils.RepackAllBinaries()

      self.assertEqual(len(glob.glob(
          os.path.join(new_dir, "linux/installers/*.deb"))), 2)
      self.assertEqual(len(glob.glob(os.path.join(
          new_dir, "linux/installers/*.rpm"))), 2)
      self.assertEqual(len(glob.glob(os.path.join(
          new_dir, "windows/installers/*.exe"))), 2)
      self.assertEqual(len(glob.glob(os.path.join(
          new_dir, "darwin/installers/*.pkg"))), 1)

  def testGenClientConfig(self):
    plugins = ["plugin1", "plugin2"]
    with test_lib.ConfigOverrider({"Client.plugins": plugins,
                                   "Client.build_environment": "test_env"}):

      deployer = build.ClientDeployer()
      data = deployer.GetClientConfig(["Client Context"], validate=True)

      parser = config_lib.YamlParser(data=data)
      raw_data = parser.RawData()

      self.assertIn("Client.deploy_time", raw_data)
      self.assertIn("Client.plugins", raw_data)

      self.assertEqual(raw_data["Client.plugins"], plugins)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
