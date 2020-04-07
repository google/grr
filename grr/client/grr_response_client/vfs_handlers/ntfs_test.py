#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import stat

from absl import app

from grr_response_client import vfs
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


# File references manually extracted from ntfs.img.
A_FILE_REF = 281474976710721
NUMBERS_TXT_FILE_REF = 281474976710720
A_B1_C1_D_FILE_REF = 281474976710728


class NTFSTest(vfs_test_lib.VfsTestCase, test_lib.GRRBaseTest):

  def _GetNTFSPathSpec(self, path, inode=None, path_options=None):
    # ntfs.img is an NTFS formatted filesystem containing:
    # -rwxrwxrwx 1 root root    4 Mar  4 15:00 ./a/b1/c1/d
    # -rwxrwxrwx 1 root root 3893 Mar  3 21:10 ./numbers.txt
    ntfs_img_path = os.path.join(self.base_path, "ntfs.img")
    return rdf_paths.PathSpec(
        path=ntfs_img_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
        nested_path=rdf_paths.PathSpec(
            path=path,
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
            inode=inode,
            path_options=path_options))

  def testNTFSNestedFile(self):
    pathspec = self._GetNTFSPathSpec("/a/b1/c1/d")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"foo\n")
    result = fd.Stat()
    self.assertEqual(
        result.pathspec,
        self._GetNTFSPathSpec("/a/b1/c1/d", A_B1_C1_D_FILE_REF,
                              rdf_paths.PathSpec.Options.CASE_LITERAL))

  def testNTFSOpenByInode(self):
    pathspec = self._GetNTFSPathSpec("/a/b1/c1/d")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"foo\n")

    self.assertTrue(fd.pathspec.last.inode)
    fd2 = vfs.VFSOpen(fd.pathspec)
    self.assertEqual(fd2.Read(100), b"foo\n")

  def testNTFSStat(self):
    pathspec = self._GetNTFSPathSpec("numbers.txt")

    fd = vfs.VFSOpen(pathspec)
    s = fd.Stat()
    self.assertEqual(
        s.pathspec,
        self._GetNTFSPathSpec("/numbers.txt", NUMBERS_TXT_FILE_REF,
                              rdf_paths.PathSpec.Options.CASE_LITERAL))
    self.assertEqual(str(s.st_atime), "2020-03-03 20:10:46")
    self.assertEqual(str(s.st_mtime), "2020-03-03 20:10:46")
    self.assertEqual(str(s.st_crtime), "2020-03-03 16:46:00")
    self.assertEqual(s.st_size, 3893)

  def testNTFSListNames(self):
    pathspec = self._GetNTFSPathSpec("/")
    fd = vfs.VFSOpen(pathspec)
    names = fd.ListNames()
    expected_names = [
        "$AttrDef", "$BadClus", "$Bitmap", "$Boot", "$Extend", "$LogFile",
        "$MFT", "$MFTMirr", "$Secure", "$UpCase", "$Volume", "a", "numbers.txt"
    ]
    self.assertSameElements(names, expected_names)

  def testNTFSListFiles(self):
    pathspec = self._GetNTFSPathSpec("/")
    fd = vfs.VFSOpen(pathspec)
    files = fd.ListFiles()
    files = [f for f in files if not f.pathspec.Basename().startswith("$")]
    files = list(files)
    files.sort(key=lambda x: x.pathspec.Basename())
    expected_files = [
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/a",
                inode=A_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:48:16"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:47:43"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:47:50"),
            st_mode=stat.S_IFDIR,
        ),
        rdf_client_fs.StatEntry(
            pathspec=self._GetNTFSPathSpec(
                "/numbers.txt",
                inode=NUMBERS_TXT_FILE_REF,
                path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
            st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 20:10:46"),
            st_crtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 16:46:00"),
            st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                "2020-03-03 20:10:46"),
            st_mode=stat.S_IFREG,
            st_size=3893,
        ),
    ]
    self.assertEqual(files, expected_files)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
