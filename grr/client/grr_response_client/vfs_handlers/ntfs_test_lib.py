#!/usr/bin/env python
import os
import platform
import tempfile
import unittest

from absl.testing import absltest

from grr_response_client import vfs
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_client.vfs_handlers import ntfs_image_test_lib
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths


class NTFSTest(ntfs_image_test_lib.NTFSImageTest):
  PATH_TYPE = rdf_paths.PathSpec.PathType.NTFS

  def _FileRefToInode(self, file_ref: int) -> int:
    return file_ref

  def _ExpectedStatEntry(
      self, st: rdf_client_fs.StatEntry) -> rdf_client_fs.StatEntry:
    # libfsntfs doesn't report these fields.
    st.st_gid = None
    st.st_uid = None
    st.st_nlink = None
    return st


@unittest.skipIf(platform.system() != "Windows", "This test is Windows-only.")
class NTFSNativeWindowsTest(absltest.TestCase):
  """Runs tests against actual files on the local NTFS filesystem."""

  def testNTFSReadUnicode(self):
    with tempfile.TemporaryDirectory() as tmp_dir:
      path = os.path.join(tmp_dir, "入乡随俗 海外春节别样过法")
      file_data = "中国新闻"
      with open(path, "w", encoding="utf-8") as f:
        f.write(file_data)
      pathspec = rdf_paths.PathSpec(
          path=path, pathtype=rdf_paths.PathSpec.PathType.NTFS)
      fd = vfs.VFSOpen(pathspec)
      self.assertEqual(fd.Read(100).decode("utf-8"), file_data)

  def testGlobComponentGenerate(self):
    opts = globbing.PathOpts(pathtype=rdf_paths.PathSpec.PathType.NTFS)
    paths = globbing.GlobComponent(u"Windows", opts=opts).Generate("C:\\")
    self.assertEqual(list(paths), [u"C:\\Windows"])

  def testGlobbingExpandPath(self):
    opts = globbing.PathOpts(pathtype=rdf_paths.PathSpec.PathType.NTFS)
    paths = globbing.ExpandPath("C:/Windows/System32/notepad.exe", opts=opts)
    self.assertEqual(list(paths), [u"C:\\Windows\\System32\\notepad.exe"])
