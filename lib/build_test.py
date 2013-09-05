#!/usr/bin/env python
"""Tests for building and repacking clients."""
import os
import shutil
import stat

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

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
                   stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR)

      config_lib.CONFIG.Set("ClientBuilder.source", tmp_dir)

      # If this doesn't raise, it means that there were either no templates,
      # or all of them were repacked successfully.
      maintenance_utils.RepackAllBinaries()


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
