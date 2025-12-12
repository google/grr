#!/usr/bin/env python
import os
import stat

from absl.testing import absltest

from grr_response_server import rrg_fs
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2


class StatEntryTest(absltest.TestCase):

  def testFile(self):
    metadata = rrg_fs_pb2.FileMetadata()
    metadata.type = rrg_fs_pb2.FileMetadata.FILE
    metadata.size = 42
    metadata.access_time.GetCurrentTime()
    metadata.modification_time.GetCurrentTime()
    metadata.creation_time.GetCurrentTime()
    metadata.unix_dev = 13
    metadata.unix_ino = 1337
    metadata.unix_mode = 0o777
    metadata.unix_nlink = 0
    metadata.unix_uid = os.getuid()
    metadata.unix_gid = os.getgid()
    metadata.unix_blksize = 4096
    metadata.unix_blocks = 1

    stat_entry = rrg_fs.StatEntry(metadata)
    self.assertTrue(stat.S_ISREG(stat_entry.st_mode))
    self.assertEqual(stat_entry.st_size, 42)
    self.assertEqual(stat_entry.st_dev, 13)
    self.assertEqual(stat_entry.st_ino, 1337)
    self.assertEqual(stat_entry.st_mode & 0o777, 0o777)
    self.assertEqual(stat_entry.st_nlink, 0)
    self.assertEqual(stat_entry.st_uid, os.getuid())
    self.assertEqual(stat_entry.st_gid, os.getgid())
    self.assertEqual(stat_entry.st_blksize, 4096)
    self.assertEqual(stat_entry.st_blocks, 1)

  def testDir(self):
    metadata = rrg_fs_pb2.FileMetadata()
    metadata.type = rrg_fs_pb2.FileMetadata.DIR

    stat_entry = rrg_fs.StatEntry(metadata)
    self.assertTrue(stat.S_ISDIR(stat_entry.st_mode))

  def testSymlink(self):
    metadata = rrg_fs_pb2.FileMetadata()
    metadata.type = rrg_fs_pb2.FileMetadata.SYMLINK

    stat_entry = rrg_fs.StatEntry(metadata)
    self.assertTrue(stat.S_ISLNK(stat_entry.st_mode))


class PathInfoTest(absltest.TestCase):

  def testFile(self):
    metadata = rrg_fs_pb2.FileMetadata()
    metadata.type = rrg_fs_pb2.FileMetadata.FILE
    metadata.size = 42

    path_info = rrg_fs.PathInfo(metadata)
    self.assertFalse(path_info.directory)
    self.assertEqual(path_info.stat_entry.st_size, 42)

  def testDir(self):
    metadata = rrg_fs_pb2.FileMetadata()
    metadata.type = rrg_fs_pb2.FileMetadata.DIR

    path_info = rrg_fs.PathInfo(metadata)
    self.assertTrue(path_info.directory)


if __name__ == "__main__":
  absltest.main()
