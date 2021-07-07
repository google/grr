#!/usr/bin/env python
# pylint: mode=test

import abc
import os
import stat
from typing import Optional

from absl.testing import absltest

from grr_response_client import vfs
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs

# File references manually extracted from ntfs.img.
A_FILE_REF = 281474976710721
ADS_FILE_REF = 1125899906842697
ADS_ADS_TXT_FILE_REF = 562949953421386
NUMBERS_TXT_FILE_REF = 281474976710720
A_B1_C1_D_FILE_REF = 281474976710728
READ_ONLY_FILE_TXT_FILE_REF = 844424930132043
HIDDEN_FILE_TXT_FILE_REF = 562949953421388
CHINESE_FILE_FILE_REF = 844424930132045

# Default st_mode flags for files and directories
S_DEFAULT_FILE = (stat.S_IFREG | stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
S_DEFAULT_DIR = (stat.S_IFDIR | stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)


class NTFSImageTest(absltest.TestCase, abc.ABC):

  PATH_TYPE: Optional[rdf_structs.EnumNamedValue] = None

  @abc.abstractmethod
  def _FileRefToInode(self, file_ref: int) -> int:
    """Converts a file reference to an inode number."""
    pass

  @abc.abstractmethod
  def _ExpectedStatEntry(
      self, st: rdf_client_fs.StatEntry) -> rdf_client_fs.StatEntry:
    """Fixes an expected StatEntry for the respective implementation."""
    pass

  def _GetNTFSPathSpec(self,
                       path,
                       file_ref=None,
                       path_options=None,
                       stream_name=None):
    # ntfs.img is an NTFS formatted filesystem containing:
    # -rwxrwxrwx 1 root root    4 Mar  4 15:00 ./a/b1/c1/d
    # -rwxrwxrwx 1 root root 3893 Mar  3 21:10 ./numbers.txt
    # drwxrwxrwx 1 root root    0 Apr  7 15:23 ./ads
    # -rwxrwxrwx 1 root root    5 Apr  7 15:19 ./ads/ads.txt
    # -rwxrwxrwx 1 root root    6 Apr  7 15:48 ./ads/ads.txt:one
    # -rwxrwxrwx 1 root root    7 Apr  7 15:48 ./ads/ads.txt:two
    # -rwxrwxrwx 1 root root    0 Apr  8 22:14 ./hidden_file.txt
    # -rwxrwxrwx 1 root root    0 Apr  8 22:14 ./read_only_file.txt
    # -rwxrwxrwx 1 root root   26 Jun 10 15:34 '入乡随俗 海外春节别样过法.txt'

    ntfs_img_path = os.path.join(config.CONFIG["Test.data_dir"], "ntfs.img")

    if file_ref is None:
      inode = None
    else:
      inode = self._FileRefToInode(file_ref)

    return rdf_paths.PathSpec(
        path=ntfs_img_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
        nested_path=rdf_paths.PathSpec(
            path=path,
            pathtype=self.PATH_TYPE,
            inode=inode,
            path_options=path_options,
            stream_name=stream_name))

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

    pathspec = self._GetNTFSPathSpec("/ignored", fd.pathspec.last.inode,
                                     rdf_paths.PathSpec.Options.CASE_LITERAL)
    fd3 = vfs.VFSOpen(pathspec)
    self.assertEqual(fd3.Read(100), b"foo\n")

  def testNTFSRead_PastTheEnd(self):
    pathspec = self._GetNTFSPathSpec("/a/b1/c1/d")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"foo\n")
    self.assertEqual(fd.Read(100), b"")

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
    self.assertEqual(str(s.st_btime), "2020-03-03 16:46:00")
    self.assertEqual(s.st_size, 3893)

  def testNTFSListNames(self):
    pathspec = self._GetNTFSPathSpec("/")
    fd = vfs.VFSOpen(pathspec)
    names = fd.ListNames()
    expected_names = [
        "$AttrDef",
        "$BadClus",
        "$Bitmap",
        "$Boot",
        "$Extend",
        "$LogFile",
        "$MFT",
        "$MFTMirr",
        "$Secure",
        "$UpCase",
        "$Volume",
        "a",
        "ads",
        "numbers.txt",
        "read_only_file.txt",
        "hidden_file.txt",
        "入乡随俗 海外春节别样过法.txt",
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
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/a",
                    file_ref=A_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 16:48:16"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 16:47:43"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 16:47:50"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 16:47:50"),
                st_mode=S_DEFAULT_DIR,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/ads",
                    file_ref=ADS_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 14:57:02"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:23:07"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 14:56:47"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 14:56:47"),
                st_mode=S_DEFAULT_DIR,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/hidden_file.txt",
                    file_ref=HIDDEN_FILE_TXT_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:14:38"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:14:38"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:14:38"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:15:07"),
                st_mode=(stat.S_IFREG | stat.S_IWUSR | stat.S_IWGRP
                         | stat.S_IWOTH
                         | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
                st_size=0,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/numbers.txt",
                    file_ref=NUMBERS_TXT_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 20:10:46"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 16:46:00"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 20:10:46"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-03-03 20:10:46"),
                st_mode=S_DEFAULT_FILE,
                st_size=3893,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/read_only_file.txt",
                    file_ref=READ_ONLY_FILE_TXT_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:14:33"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:14:33"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:14:33"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-08 20:14:55"),
                st_mode=(stat.S_IFREG | stat.S_IRUSR | stat.S_IRGRP
                         | stat.S_IROTH
                         | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH),
                st_size=0,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/入乡随俗 海外春节别样过法.txt",
                    file_ref=CHINESE_FILE_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-06-10 13:34:36"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-06-10 13:34:36"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-06-10 13:34:36"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-06-10 13:34:36"),
                st_mode=S_DEFAULT_FILE,
                st_size=26,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
    ]
    self.assertEqual(files, expected_files)

  def testNTFSListFiles_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec("/ads")
    fd = vfs.VFSOpen(pathspec)
    files = fd.ListFiles()
    files = list(files)
    files.sort(key=lambda x: x.pathspec.last.stream_name)
    expected_files = [
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/ads/ads.txt",
                    file_ref=ADS_ADS_TXT_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:51"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:18:53"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:56"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:56"),
                st_mode=S_DEFAULT_FILE,
                st_size=5,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/ads/ads.txt",
                    file_ref=ADS_ADS_TXT_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
                    stream_name="one"),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:51"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:18:53"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:56"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:56"),
                st_mode=S_DEFAULT_FILE,
                st_size=6,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
        self._ExpectedStatEntry(
            rdf_client_fs.StatEntry(
                pathspec=self._GetNTFSPathSpec(
                    "/ads/ads.txt",
                    file_ref=ADS_ADS_TXT_FILE_REF,
                    path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
                    stream_name="two"),
                st_atime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:51"),
                st_btime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:18:53"),
                st_mtime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:56"),
                st_ctime=rdfvalue.RDFDatetimeSeconds.FromHumanReadable(
                    "2020-04-07 13:48:56"),
                st_mode=S_DEFAULT_FILE,
                st_size=7,
                st_gid=0,
                st_uid=48,
                st_nlink=1,
            )),
    ]
    self.assertEqual(files, expected_files)

  def testNTFSOpen_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec("/ads/ads.txt")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Foo.\n")

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="one")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Bar..\n")

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="ONE")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Bar..\n")

    with self.assertRaises(IOError):
      pathspec = self._GetNTFSPathSpec(
          "/ads/ads.txt",
          stream_name="ONE",
          path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
      vfs.VFSOpen(pathspec)

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="two")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Baz...\n")

    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="TWO")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Baz...\n")

    with self.assertRaises(IOError):
      pathspec = self._GetNTFSPathSpec(
          "/ads/ads.txt",
          stream_name="TWO",
          path_options=rdf_paths.PathSpec.Options.CASE_LITERAL)
      vfs.VFSOpen(pathspec)

  def testNTFSStat_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec("/ads/ads.txt", stream_name="ONE")

    fd = vfs.VFSOpen(pathspec)
    s = fd.Stat()
    self.assertEqual(
        s.pathspec,
        self._GetNTFSPathSpec(
            "/ads/ads.txt",
            ADS_ADS_TXT_FILE_REF,
            stream_name="one",
            path_options=rdf_paths.PathSpec.Options.CASE_LITERAL))
    self.assertEqual(str(s.st_atime), "2020-04-07 13:48:51")
    self.assertEqual(str(s.st_mtime), "2020-04-07 13:48:56")
    self.assertEqual(str(s.st_btime), "2020-04-07 13:18:53")
    self.assertEqual(s.st_size, 6)

  def testNTFSOpenByInode_alternateDataStreams(self):
    pathspec = self._GetNTFSPathSpec(
        "/ignore", file_ref=ADS_ADS_TXT_FILE_REF, stream_name="ONE")
    fd = vfs.VFSOpen(pathspec)
    self.assertEqual(fd.Read(100), b"Bar..\n")

  def testNTFSReadUnicode(self):
    pathspec = self._GetNTFSPathSpec("/入乡随俗 海外春节别样过法.txt")
    fd = vfs.VFSOpen(pathspec)
    expected = "Chinese news\n中国新闻\n".encode("utf-8")
    self.assertEqual(fd.Read(100), expected)

  def testNTFSRead_fromDirectoryRaises(self):
    pathspec = self._GetNTFSPathSpec("/")
    fd = vfs.VFSOpen(pathspec)
    with self.assertRaises(IOError):
      fd.Read(1)
