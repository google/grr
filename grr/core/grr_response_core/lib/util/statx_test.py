#!/usr/bin/env python
import ctypes
import os
import platform
import stat
import time

from absl.testing import absltest

from grr_response_core.lib.util import statx
from grr_response_core.lib.util import temp


class GetTest(absltest.TestCase):

  def testNlink(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      target = os.path.join(tempdir, "foo")
      link_1 = os.path.join(tempdir, "bar")
      link_2 = os.path.join(tempdir, "baz")

      with open(target, mode="wb"):
        pass

      os.link(target, link_1)
      os.link(target, link_2)

      result = statx.Get(target.encode("utf-8"))
      self.assertEqual(result.nlink, 3)

  @absltest.skipIf(platform.system() == "Windows", "UID not available")
  def testUid(self):
    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))
      self.assertEqual(result.uid, os.getuid())

  @absltest.skipIf(platform.system() == "Windows", "GID not available")
  def testGid(self):
    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))
      self.assertEqual(result.gid, os.getgid())

  def testModeReg(self):
    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))
      self.assertTrue(stat.S_ISREG(result.mode))

  def testModeDir(self):
    with temp.AutoTempDirPath() as tempdir:
      result = statx.Get(tempdir.encode("utf-8"))
      self.assertTrue(stat.S_ISDIR(result.mode))

  def testModeLink(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      target = os.path.join(tempdir, "foo")
      link = os.path.join(tempdir, "bar")

      with open(target, mode="wb"):
        pass

      os.symlink(target, link)

      result = statx.Get(link.encode("utf-8"))
      self.assertTrue(stat.S_ISLNK(result.mode))

  def testIno(self):
    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))
      self.assertNotEqual(result.ino, 0)

  def testSize(self):
    with temp.AutoTempFilePath() as tempfile:
      with open(tempfile, mode="wb") as tempfile_handle:
        tempfile_handle.write(b"A" * 42)

      result = statx.Get(tempfile.encode("utf-8"))
      self.assertEqual(result.size, 42)

  def testDev(self):
    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))
      self.assertEqual(result.dev, os.lstat(tempfile).st_dev)

  @absltest.skipIf(platform.system() == "Windows", "`rdev` unavailable")
  def testRdev(self):
    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))
      self.assertEqual(result.rdev, os.lstat(tempfile).st_rdev)

  def testBaseTime(self):
    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))

      self.assertGreater(result.atime_ns, 0)
      self.assertGreater(result.mtime_ns, 0)
      self.assertGreater(result.ctime_ns, 0)

      # TODO(hanuszczak): Remove this once support for Python 3.6 is dropped.
      if hasattr(time, "time_ns"):
        self.assertLess(result.atime_ns, time.time_ns())
        self.assertLess(result.mtime_ns, time.time_ns())
        self.assertLess(result.ctime_ns, time.time_ns())

  def testBirthTime(self):
    # On Linux, file birth time is collected only if `statx` is available.
    if platform.system() == "Linux":
      try:
        ctypes.CDLL("libc.so.6").statx
      except AttributeError:
        raise absltest.SkipTest("`statx` not available")

    with temp.AutoTempFilePath() as tempfile:
      result = statx.Get(tempfile.encode("utf-8"))

      self.assertGreater(result.btime_ns, 0)

      # TODO(hanuszczak): Remove this once support for Python 3.6 is dropped.
      if hasattr(time, "time_ns"):
        self.assertLess(result.btime_ns, time.time_ns())

  def testRaisesExceptionOnError(self):
    with temp.AutoTempDirPath() as tempdir:
      with self.assertRaises(OSError):
        statx.Get(os.path.join(tempdir, "non-existing-file").encode("utf-8"))


if __name__ == "__main__":
  absltest.main()
