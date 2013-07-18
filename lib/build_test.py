#!/usr/bin/env python
"""Tests for building and repacking clients."""
import os
import shutil
import stat

from grr.client import conf

from grr.lib import build
from grr.lib import config_lib
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
    templates = build.GetTemplateVersions(executables_dir=self.executables_dir)
    templates = list(templates)
    self.assertGreater(len(templates), 2)

    with utils.TempDirectory() as tmp_dir:
      new_dir = os.path.join(tmp_dir, "grr", "executables")

      # Copy templates and ensure our resulting directory is writeable.
      shutil.copytree(self.executables_dir, new_dir)
      for root, dirs, _ in os.walk(new_dir):
        for this_dir in dirs:
          os.chmod(os.path.join(root, this_dir),
                   stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR)

      config_lib.CONFIG.Set("ClientBuilder.source", tmp_dir)
      # Note, this is made tricky because we try to operate with a cleansed
      # config when we do the repack, so any config settings we set here
      # will be ignored. We need to write things we want used to the config file
      # itself.
      config_lib.CONFIG.Write()

      built = build.RepackAllBinaries(executables_dir=new_dir)
      self.assertEqual(len(templates), len(built))


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  conf.StartMain(main)
