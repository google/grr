#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import io
import os
import platform
import shutil
import socket
import subprocess
import unittest

from absl.testing import absltest

import mock

from grr_response_core.lib.util import filesystem
from grr_response_core.lib.util import temp
# TODO(hanuszczak): This import below is less than ideal, these functions could
# be probably moved to some more fundamental test module.
from grr.test_lib import filesystem_test_lib


class StatTest(absltest.TestCase):

  def testGetSize(self):
    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, "wb") as fd:
        fd.write(b"foobarbaz")

      stat = filesystem.Stat.FromPath(temp_filepath, follow_symlink=False)
      self.assertEqual(stat.GetSize(), 9)

  def testGetPath(self):
    with temp.AutoTempFilePath() as temp_filepath:
      stat = filesystem.Stat.FromPath(temp_filepath, follow_symlink=False)
      self.assertEqual(stat.GetPath(), temp_filepath)

  @unittest.skipIf(platform.system() == "Windows", "requires Unix-like system")
  def testGetTime(self):
    adate = datetime.datetime(2017, 10, 2, 8, 45)
    mdate = datetime.datetime(2001, 5, 3, 10, 30)

    with temp.AutoTempFilePath() as temp_filepath:
      self._Touch(temp_filepath, "-a", adate)
      self._Touch(temp_filepath, "-m", mdate)

      stat = filesystem.Stat.FromPath(temp_filepath, follow_symlink=False)
      self.assertEqual(stat.GetAccessTime(), self._EpochMillis(adate))
      self.assertEqual(stat.GetModificationTime(), self._EpochMillis(mdate))

  def testDirectory(self):
    with temp.AutoTempDirPath() as temp_dirpath:
      stat = filesystem.Stat.FromPath(temp_dirpath, follow_symlink=False)
      self.assertTrue(stat.IsDirectory())
      self.assertFalse(stat.IsRegular())
      self.assertFalse(stat.IsSocket())
      self.assertFalse(stat.IsSymlink())

  def testRegular(self):
    with temp.AutoTempFilePath() as temp_filepath:
      stat = filesystem.Stat.FromPath(temp_filepath, follow_symlink=False)
      self.assertFalse(stat.IsDirectory())
      self.assertTrue(stat.IsRegular())
      self.assertFalse(stat.IsSocket())
      self.assertFalse(stat.IsSymlink())

  @unittest.skipIf(platform.system() == "Windows", "requires Unix-like system")
  def testSocket(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      temp_socketpath = os.path.join(temp_dirpath, "foo")

      sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      try:
        sock.bind(temp_socketpath)

        stat = filesystem.Stat.FromPath(temp_socketpath, follow_symlink=False)
        self.assertFalse(stat.IsDirectory())
        self.assertFalse(stat.IsRegular())
        self.assertTrue(stat.IsSocket())
        self.assertFalse(stat.IsSymlink())
      finally:
        sock.close()

  @unittest.skipIf(platform.system() == "Windows", "requires Unix-like system")
  def testSymlink(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath, \
        temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, "wb") as fd:
        fd.write(b"foobar")

      temp_linkpath = os.path.join(temp_dirpath, "foo")
      os.symlink(temp_filepath, temp_linkpath)

      stat = filesystem.Stat.FromPath(temp_linkpath, follow_symlink=False)
      self.assertFalse(stat.IsDirectory())
      self.assertFalse(stat.IsRegular())
      self.assertFalse(stat.IsSocket())
      self.assertTrue(stat.IsSymlink())

      stat = filesystem.Stat.FromPath(temp_linkpath, follow_symlink=True)
      self.assertFalse(stat.IsDirectory())
      self.assertTrue(stat.IsRegular())
      self.assertFalse(stat.IsSocket())
      self.assertFalse(stat.IsSymlink())
      self.assertEqual(stat.GetSize(), 6)

  # http://elixir.free-electrons.com/linux/v4.9/source/include/uapi/linux/fs.h
  FS_COMPR_FL = 0x00000004
  FS_IMMUTABLE_FL = 0x00000010
  FS_NODUMP_FL = 0x00000040

  def testGetLinuxFlags(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.Chattr(temp_filepath, attrs=["+c", "+d"])

      stat = filesystem.Stat.FromPath(temp_filepath, follow_symlink=False)
      self.assertTrue(stat.IsRegular())
      self.assertTrue(stat.GetLinuxFlags() & self.FS_COMPR_FL)
      self.assertTrue(stat.GetLinuxFlags() & self.FS_NODUMP_FL)
      self.assertFalse(stat.GetLinuxFlags() & self.FS_IMMUTABLE_FL)
      self.assertEqual(stat.GetOsxFlags(), 0)

  # https://github.com/apple/darwin-xnu/blob/master/bsd/sys/stat.h
  UF_NODUMP = 0x00000001
  UF_IMMUTABLE = 0x00000002
  UF_HIDDEN = 0x00008000

  def testGetOsxFlags(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.Chflags(temp_filepath, flags=["nodump", "hidden"])

      stat = filesystem.Stat.FromPath(temp_filepath, follow_symlink=False)
      self.assertTrue(stat.IsRegular())
      self.assertTrue(stat.GetOsxFlags() & self.UF_NODUMP)
      self.assertTrue(stat.GetOsxFlags() & self.UF_HIDDEN)
      self.assertFalse(stat.GetOsxFlags() & self.UF_IMMUTABLE)
      self.assertEqual(stat.GetLinuxFlags(), 0)

  @unittest.skipIf(platform.system() == "Windows",
                   "Windows does not support os.symlink().")
  def testGetFlagsSymlink(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath, \
        temp.AutoTempFilePath() as temp_filepath:
      temp_linkpath = os.path.join(temp_dirpath, "foo")
      os.symlink(temp_filepath, temp_linkpath)

      stat = filesystem.Stat.FromPath(temp_linkpath, follow_symlink=False)
      self.assertTrue(stat.IsSymlink())
      self.assertEqual(stat.GetLinuxFlags(), 0)
      self.assertEqual(stat.GetOsxFlags(), 0)

  @unittest.skipIf(platform.system() == "Windows",
                   "Windows does not support socket.AF_UNIX.")
  def testGetFlagsSocket(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      temp_socketpath = os.path.join(temp_dirpath, "foo")

      # There is a limit on maximum length for a socket path [1]. Most of the
      # time, this should not be an issue (since generated paths are something
      # like `/tmp/tmppqnrQsZ/foo`, way below this limit). However, on strange
      # setups this might not always be the case. Since we don't want to fail
      # the test on such configurations, we simply skip it.
      #
      # pylint: disable=line-too-long
      # [1]: https://unix.stackexchange.com/questions/367008/why-is-socket-path-length-limited-to-a-hundred-chars
      # pylint: enable=ling-too-long
      if ((platform.system() == "Linux" and len(temp_socketpath) > 108) or
          (platform.system() == "Darwin" and len(temp_socketpath) > 104)):
        message = "Generated path '{}' is too long for a socket path"
        self.skipTest(message.format(temp_socketpath))

      sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      try:
        sock.bind(temp_socketpath)

        stat = filesystem.Stat.FromPath(temp_socketpath, follow_symlink=False)
        self.assertTrue(stat.IsSocket())
        self.assertEqual(stat.GetLinuxFlags(), 0)
        self.assertEqual(stat.GetOsxFlags(), 0)
      finally:
        sock.close()

  def _Touch(self, path, mode, date):
    fmt_date = date.strftime("%Y%m%d%H%M")
    subprocess.check_call(["touch", mode, "-t", fmt_date, path])

  @staticmethod
  def _EpochMillis(date):
    return int(date.strftime("%s"))


class StatCacheTest(absltest.TestCase):

  def setUp(self):
    super(StatCacheTest, self).setUp()
    self.temp_dir = temp.TempDirPath()
    self.addCleanup(shutil.rmtree, self.temp_dir)

  def Path(self, *args):
    return os.path.join(self.temp_dir, *args)

  def testBasicUsage(self):
    with io.open(self.Path("foo"), "wb") as fd:
      fd.write(b"123")
    with io.open(self.Path("bar"), "wb") as fd:
      fd.write(b"123456")
    with io.open(self.Path("baz"), "wb") as fd:
      fd.write(b"123456789")

    stat_cache = filesystem.StatCache()

    with MockStat() as stat_mock:
      foo_stat = stat_cache.Get(self.Path("foo"))
      self.assertEqual(foo_stat.GetSize(), 3)
      self.assertTrue(stat_mock.FromPath.called)

    with MockStat() as stat_mock:
      bar_stat = stat_cache.Get(self.Path("bar"))
      self.assertEqual(bar_stat.GetSize(), 6)
      self.assertTrue(stat_mock.FromPath.called)

    with MockStat() as stat_mock:
      other_foo_stat = stat_cache.Get(self.Path("foo"))
      self.assertEqual(other_foo_stat.GetSize(), 3)
      self.assertFalse(stat_mock.FromPath.called)

    with MockStat() as stat_mock:
      other_bar_stat = stat_cache.Get(self.Path("bar"))
      self.assertEqual(other_bar_stat.GetSize(), 6)
      self.assertFalse(stat_mock.FromPath.called)

    with MockStat() as stat_mock:
      baz_stat = stat_cache.Get(self.Path("baz"))
      self.assertEqual(baz_stat.GetSize(), 9)
      self.assertTrue(stat_mock.FromPath.called)

    with MockStat() as stat_mock:
      other_baz_stat = stat_cache.Get(self.Path("baz"))
      self.assertEqual(other_baz_stat.GetSize(), 9)
      self.assertFalse(stat_mock.FromPath.called)

  @unittest.skipIf(platform.system() == "Windows",
                   "Windows does not support os.symlink().")
  def testFollowSymlink(self):
    with io.open(self.Path("foo"), "wb") as fd:
      fd.write(b"123456")
    os.symlink(self.Path("foo"), self.Path("bar"))

    stat_cache = filesystem.StatCache()

    with MockStat() as stat_mock:
      bar_stat = stat_cache.Get(self.Path("bar"), follow_symlink=False)
      self.assertTrue(bar_stat.IsSymlink())
      self.assertTrue(stat_mock.FromPath.called)

    with MockStat() as stat_mock:
      foo_stat = stat_cache.Get(self.Path("bar"), follow_symlink=True)
      self.assertFalse(foo_stat.IsSymlink())
      self.assertEqual(foo_stat.GetSize(), 6)
      self.assertTrue(stat_mock.FromPath.called)

  def testSmartSymlinkCache(self):
    with open(self.Path("foo"), "wb") as fd:
      fd.write(b"12345")

    stat_cache = filesystem.StatCache()

    with MockStat() as stat_mock:
      foo_stat = stat_cache.Get(self.Path("foo"), follow_symlink=False)
      self.assertEqual(foo_stat.GetSize(), 5)
      self.assertTrue(stat_mock.FromPath.called)

    with MockStat() as stat_mock:
      other_foo_stat = stat_cache.Get(self.Path("foo"), follow_symlink=True)
      self.assertEqual(other_foo_stat.GetSize(), 5)
      self.assertFalse(stat_mock.FromPath.called)


def MockStat():
  return mock.patch.object(filesystem, "Stat", wraps=filesystem.Stat)


if __name__ == "__main__":
  absltest.main()
