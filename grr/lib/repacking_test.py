#!/usr/bin/env python
"""Tests for grr.lib.repacking."""

import glob
import os
import shutil

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import repacking
from grr.lib import test_lib
from grr.lib import utils


class RepackingTests(test_lib.GRRBaseTest):
  """Tests for maintenance utils functionality."""

  # TODO(user): temporarily disable this test until we have released new
  # templates that can actually be repacked. Re-enabling is on the release
  # checklist:
  # https://github.com/google/grr/issues/366
  @test_lib.RequiresPackage("grr-response-templates")
  def disabled_testRepackAll(self):
    """Test repacking all binaries."""
    self.executables_dir = config_lib.Resource().Filter("executables")
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

      with test_lib.ConfigOverrider(
          {"ClientBuilder.executables_dir": new_dir,
           "ClientBuilder.unzipsfx_stub_dir": new_dir}):
        repacking.TemplateRepacker().RepackAllTemplates()

      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "linux/installers/*.deb"))), 2)
      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "linux/installers/*.rpm"))), 2)
      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "windows/installers/*.exe"))), 2)
      self.assertEqual(
          len(glob.glob(os.path.join(new_dir, "darwin/installers/*.pkg"))), 1)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
