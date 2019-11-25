#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import io
import os
import platform
import stat

from absl.testing import absltest

from grr_response_client.vfs_handlers import files
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr.test_lib import skip


class FileTest(absltest.TestCase):

  @skip.If(platform.system() == "Windows", "Symlinks not supported on Windows.")
  def testStatFollowSymlink(self):
    data = b"quux" * 1024

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      target_filepath = os.path.join(temp_dirpath, "target")
      symlink_filepath = os.path.join(temp_dirpath, "symlink")

      with io.open(target_filepath, mode="wb") as filedesc:
        filedesc.write(data)

      os.symlink(target_filepath, symlink_filepath)

      pathspec = rdf_paths.PathSpec.OS(path=symlink_filepath)
      with files.File(None, handlers={}, pathspec=pathspec) as filedesc:
        stat_entry = filedesc.Stat(follow_symlink=True)

      self.assertFalse(stat.S_ISLNK(int(stat_entry.st_mode)))
      self.assertEqual(stat_entry.st_size, len(data))  # pylint: disable=g-generic-assert

  @skip.If(platform.system() == "Windows", "Symlinks not supported on Windows.")
  def testStatNotFollowSymlink(self):
    data = b"thud" * 1024

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      target_filepath = os.path.join(temp_dirpath, "target")
      symlink_filepath = os.path.join(temp_dirpath, "symlink")

      with io.open(target_filepath, mode="wb") as filedesc:
        filedesc.write(data)

      os.symlink(target_filepath, symlink_filepath)

      pathspec = rdf_paths.PathSpec.OS(path=symlink_filepath)
      with files.File(None, handlers={}, pathspec=pathspec) as filedesc:
        stat_entry = filedesc.Stat(follow_symlink=False)

      self.assertTrue(stat.S_ISLNK(int(stat_entry.st_mode)))
      self.assertLess(stat_entry.st_size, len(data))
      self.assertEqual(stat_entry.symlink, target_filepath)


if __name__ == "__main__":
  absltest.main()
