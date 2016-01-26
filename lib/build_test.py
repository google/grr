#!/usr/bin/env python
"""Tests for building and repacking clients."""
import os
import shutil
import stat

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
    self.executables_dir = os.path.join(config_lib.CONFIG["Test.srcdir"],
                                        "grr", "executables")

  def testRepackAll(self):
    """Testing repacking all binaries."""
    with utils.TempDirectory() as tmp_dir:
      new_dir = os.path.join(tmp_dir, "grr", "executables")

      # Copy templates and ensure our resulting directory is writeable.
      shutil.copytree(self.executables_dir, new_dir)
      for root, dirs, _ in os.walk(new_dir):
        for this_dir in dirs:
          os.chmod(os.path.join(root, this_dir),
                   stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

      with test_lib.ConfigOverrider({"ClientBuilder.source": tmp_dir}):
        # If this doesn't raise, it means that there were either no templates,
        # or all of them were repacked successfully.
        maintenance_utils.RepackAllBinaries()

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
