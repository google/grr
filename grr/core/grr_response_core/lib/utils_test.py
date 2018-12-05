#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for utility classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import os
import platform
import shutil
import socket
import subprocess
import threading
import unittest


from absl.testing import absltest
from builtins import int  # pylint: disable=redefined-builtin
from builtins import range  # pylint: disable=redefined-builtin
import mock

from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr.test_lib import client_test_lib
from grr.test_lib import temp
from grr.test_lib import test_lib

# Test method names don't conform with Google style
# pylint: disable=g-bad-name


class StoreTests(test_lib.GRRBaseTest):
  """Store tests."""

  def test01StoreExpiration(self):
    """Testing store removes objects when full."""
    s = utils.FastStore(max_size=5)
    keys = []
    for i in range(0, 100):
      keys.append(s.Put(i, i))

    # This should not raise
    s.Get(keys[-1])

    # This should raise though
    self.assertRaises(KeyError, s.Get, keys[0])

  def test02StoreRefresh(self):
    """Test that store keeps recently gotten objects fresh."""
    s = utils.FastStore(max_size=5)
    keys = []
    for i in range(0, 5):
      keys.append(s.Put(i, i))

    # This should not raise because keys[0] should be refreshed each time its
    # gotten
    for i in range(0, 1000):
      s.Get(keys[0])
      s.Put(i, i)

  def test03Expire(self):
    """Tests the expire mechanism."""
    s = utils.FastStore(max_size=100)
    key = "test1"
    s.Put(key, 1)

    # This should not raise
    self.assertEqual(s.Get(key), 1)
    s.ExpireObject(key)

    self.assertRaises(KeyError, s.Get, key)

  def test04KillObject(self):
    """Test that callbacks are called using object destruction."""
    results = []

    class TestStore(utils.FastStore):

      def KillObject(self, obj):
        results.append(obj)

    s = TestStore(max_size=5)
    for i in range(0, 10):
      s.Put(i, i)

    # Only the first 5 messages have been expired (and hence called)
    self.assertEqual(results, list(range(0, 5)))

  def test05TimeBasedCache(self):

    key = "key"
    tested_cache = utils.TimeBasedCache(max_age=50)
    with test_lib.FakeTime(100):

      # Stop the housekeeper thread - we test it explicitely here
      tested_cache.exit = True
      tested_cache.Put(key, "hello")

      self.assertEqual(tested_cache.Get(key), "hello")

    with test_lib.FakeTime(160):

      # Force the housekeeper to run
      tested_cache.house_keeper_thread.target()

      # This should now be expired
      self.assertRaises(KeyError, tested_cache.Get, key)

  def testTimeBasedCacheSingleThread(self):

    utils.TimeBasedCache()
    num_threads = threading.active_count()
    utils.TimeBasedCache()
    self.assertEqual(threading.active_count(), num_threads)

  def testWeakRefSet(self):

    c1 = utils.TimeBasedCache()
    c2 = utils.TimeBasedCache()

    self.assertIn(c1, utils.TimeBasedCache.active_caches)
    self.assertIn(c2, utils.TimeBasedCache.active_caches)

    l = len(utils.TimeBasedCache.active_caches)

    del c1

    # This should work even though the weak ref to c1 should be gone.
    utils.TimeBasedCache.house_keeper_thread.target()

    # Make sure it's actually gone.
    self.assertLess(len(utils.TimeBasedCache.active_caches), l)


class UtilsTest(test_lib.GRRBaseTest):
  """Utilities tests."""

  def testNormpath(self):
    """Test our Normpath."""
    data = [
        ("foo/../../../../", "/"),
        ("/foo/../../../../bar", "/bar"),
        ("/foo/bar/../3sdfdfsa/.", "/foo/3sdfdfsa"),
        ("../foo/bar", "/foo/bar"),
        ("./foo/bar", "/foo/bar"),
        ("/", "/"),
    ]

    for test, expected in data:
      self.assertEqual(expected, utils.NormalizePath(test))

  def FormatAsHexStringTest(self):
    self.assertEqual(utils.FormatAsHexString(10), "0x1b")
    self.assertEqual(utils.FormatAsHexString(10, 4), "0x001b")
    self.assertEqual(utils.FormatAsHexString(10, 16), "0x000000000000001b")
    # No trailing "L".
    self.assertEqual(utils.FormatAsHexString(int(1e19)), "0x8ac7230489e80000")
    self.assertEqual(
        utils.FormatAsHexString(int(1e19), 5), "0x8ac7230489e80000")

  def testXor(self):
    test_str = b"foobar4815162342"
    for key in [1, 5, 123, 255]:
      xor_str = utils.Xor(test_str, key)
      self.assertNotEqual(xor_str, test_str)
      xor_str = utils.Xor(xor_str, key)
      self.assertEqual(xor_str, test_str)

  def LinkedListTest(self):

    l = utils.LinkedList()

    # Test empty list properties.
    self.assertEmpty(l)
    self.assertEqual(list(l), [])
    self.assertRaises(IndexError, l.Pop)
    self.assertRaises(IndexError, l.PopLeft)
    self.CheckList(l)

    # Just one element.
    l.Append(1)
    self.CheckList(l)
    self.assertLen(l, 1)
    self.assertEqual(list(l), [1])

    # Pop it, check that list is empty again.
    self.assertEqual(l.Pop(), 1)
    self.CheckList(l)
    self.assertEmpty(l)
    self.assertEqual(list(l), [])
    self.assertRaises(IndexError, l.Pop)
    self.assertRaises(IndexError, l.PopLeft)

    # Simple popleft test.
    l.Append(1)
    self.assertLen(l, 1)
    self.assertEqual(list(l), [1])
    self.assertEqual(l.PopLeft(), 1)

    # Now make a bigger list.
    l.Append(1)
    l.Append(2)
    node3 = l.Append(3)
    l.Append(4)
    l.Append(5)
    l.Append(6)
    l.Append(7)
    self.CheckList(l)

    self.assertLen(l, 7)
    self.assertEqual(list(l), [1, 2, 3, 4, 5, 6, 7])

    # Unlink a node in the middle.
    l.Unlink(node3)
    self.CheckList(l)

    self.assertLen(l, 6)
    self.assertEqual(list(l), [1, 2, 4, 5, 6, 7])

    # Unlink head.
    l.Unlink(l.head)
    self.CheckList(l)

    self.assertLen(l, 5)
    self.assertEqual(list(l), [2, 4, 5, 6, 7])

    # Unlink tail.
    l.Unlink(l.tail)
    self.CheckList(l)

    # Some more unlinks.
    self.assertLen(l, 4)
    self.assertEqual(list(l), [2, 4, 5, 6])
    self.CheckList(l)

    self.assertEqual(l.PopLeft(), 2)
    self.assertLen(l, 3)
    self.assertEqual(list(l), [4, 5, 6])
    self.CheckList(l)

    self.assertEqual(l.Pop(), 6)
    self.assertLen(l, 2)
    self.assertEqual(list(l), [4, 5])
    self.CheckList(l)

    l.Append(6)
    self.assertEqual(l.Pop(), 6)
    self.assertLen(l, 2)
    self.assertEqual(list(l), [4, 5])
    self.CheckList(l)

    self.assertEqual(l.Pop(), 5)
    self.assertLen(l, 1)
    self.assertEqual(list(l), [4])
    self.CheckList(l)

    self.assertEqual(l.PopLeft(), 4)
    self.assertEmpty(l)
    self.CheckList(l)

    self.assertRaises(IndexError, l.Pop)
    self.assertRaises(IndexError, l.PopLeft)

    # Unlink the only element present.
    l = utils.LinkedList()
    n = l.Append(1)
    l.Unlink(n)
    self.assertEmpty(l)
    self.CheckList(l)

    self.assertRaises(IndexError, l.Pop)
    self.assertRaises(IndexError, l.PopLeft)

  def CheckList(self, l):
    """Quickly checks if the list is sane."""
    if not l.head:
      self.assertFalse(bool(l.tail))
    self.assertFalse(bool(l.head.prev))
    self.assertFalse(bool(l.tail.next))

    p = self.head
    p1 = self.head.next
    while p1:
      self.assertEqual(p1.prev, p)
      p = p1
      p1 = p1.next
    self.assertEqual(p, self.tail)


class RollingMemoryStreamTest(test_lib.GRRBaseTest):
  """Tests for RollingMemoryStream."""

  def setUp(self):
    super(RollingMemoryStreamTest, self).setUp()
    self.stream = utils.RollingMemoryStream()

  def testGetValueAndResetReturnsSingleWrittenValue(self):
    self.stream.write(b"blah")
    self.assertEqual(self.stream.GetValueAndReset(), b"blah")

  def testSecondCallToGetValueAndResetReturnsEmptyValue(self):
    self.stream.write(b"blah")
    self.stream.GetValueAndReset()
    self.assertEqual(self.stream.GetValueAndReset(), b"")

  def testGetValueAndResetReturnsLastValueSincePreviousReset(self):
    self.stream.write(b"foo")
    self.stream.GetValueAndReset()
    self.stream.write(b"bar")
    self.assertEqual(self.stream.GetValueAndReset(), b"bar")

  def testWriteAfterCloseRaises(self):
    self.stream.close()
    with self.assertRaises(utils.ArchiveAlreadyClosedError):
      self.stream.write(b"blah")


class StatTest(absltest.TestCase):

  def testGetSize(self):
    with temp.AutoTempFilePath() as temp_filepath:
      with open(temp_filepath, "wb") as fd:
        fd.write("foobarbaz")

      stat = utils.Stat(temp_filepath, follow_symlink=False)
      self.assertEqual(stat.GetSize(), 9)

  def testGetPath(self):
    with temp.AutoTempFilePath() as temp_filepath:
      stat = utils.Stat(temp_filepath, follow_symlink=False)
      self.assertEqual(stat.GetPath(), temp_filepath)

  @unittest.skipIf(platform.system() == "Windows", "requires Unix-like system")
  def testGetTime(self):
    adate = datetime.datetime(2017, 10, 2, 8, 45)
    mdate = datetime.datetime(2001, 5, 3, 10, 30)

    with temp.AutoTempFilePath() as temp_filepath:
      self._Touch(temp_filepath, "-a", adate)
      self._Touch(temp_filepath, "-m", mdate)

      stat = utils.Stat(temp_filepath, follow_symlink=False)
      self.assertEqual(stat.GetAccessTime(), self._EpochMillis(adate))
      self.assertEqual(stat.GetModificationTime(), self._EpochMillis(mdate))

  def testDirectory(self):
    with temp.AutoTempDirPath() as temp_dirpath:
      stat = utils.Stat(temp_dirpath, follow_symlink=False)
      self.assertTrue(stat.IsDirectory())
      self.assertFalse(stat.IsRegular())
      self.assertFalse(stat.IsSocket())
      self.assertFalse(stat.IsSymlink())

  def testRegular(self):
    with temp.AutoTempFilePath() as temp_filepath:
      stat = utils.Stat(temp_filepath, follow_symlink=False)
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

        stat = utils.Stat(temp_socketpath, follow_symlink=False)
        self.assertFalse(stat.IsDirectory())
        self.assertFalse(stat.IsRegular())
        self.assertTrue(stat.IsSocket())
        self.assertFalse(stat.IsSymlink())
      finally:
        sock.close()

  @unittest.skipIf(platform.system() == "Windows", "requires Unix-like system")
  def testSymlink(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath,\
         temp.AutoTempFilePath() as temp_filepath:
      with open(temp_filepath, "wb") as fd:
        fd.write("foobar")

      temp_linkpath = os.path.join(temp_dirpath, "foo")
      os.symlink(temp_filepath, temp_linkpath)

      stat = utils.Stat(temp_linkpath, follow_symlink=False)
      self.assertFalse(stat.IsDirectory())
      self.assertFalse(stat.IsRegular())
      self.assertFalse(stat.IsSocket())
      self.assertTrue(stat.IsSymlink())

      stat = utils.Stat(temp_linkpath, follow_symlink=True)
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
      client_test_lib.Chattr(temp_filepath, attrs=["+c", "+d"])

      stat = utils.Stat(temp_filepath, follow_symlink=False)
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
      client_test_lib.Chflags(temp_filepath, flags=["nodump", "hidden"])

      stat = utils.Stat(temp_filepath, follow_symlink=False)
      self.assertTrue(stat.IsRegular())
      self.assertTrue(stat.GetOsxFlags() & self.UF_NODUMP)
      self.assertTrue(stat.GetOsxFlags() & self.UF_HIDDEN)
      self.assertFalse(stat.GetOsxFlags() & self.UF_IMMUTABLE)
      self.assertEqual(stat.GetLinuxFlags(), 0)

  def testGetFlagsSymlink(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath,\
         temp.AutoTempFilePath() as temp_filepath:
      temp_linkpath = os.path.join(temp_dirpath, "foo")
      os.symlink(temp_filepath, temp_linkpath)

      stat = utils.Stat(temp_linkpath, follow_symlink=False)
      self.assertTrue(stat.IsSymlink())
      self.assertEqual(stat.GetLinuxFlags(), 0)
      self.assertEqual(stat.GetOsxFlags(), 0)

  def testGetFlagsSocket(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      temp_socketpath = os.path.join(temp_dirpath, "foo")

      sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      try:
        sock.bind(temp_socketpath)

        stat = utils.Stat(temp_socketpath, follow_symlink=False)
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
    self.temp_dir = temp.TempDirPath()

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

  def Path(self, *args):
    return os.path.join(self.temp_dir, *args)

  def testBasicUsage(self):
    with open(self.Path("foo"), "w") as fd:
      fd.write("123")
    with open(self.Path("bar"), "w") as fd:
      fd.write("123456")
    with open(self.Path("baz"), "w") as fd:
      fd.write("123456789")

    stat_cache = utils.StatCache()

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      foo_stat = stat_cache.Get(self.Path("foo"))
      self.assertEqual(foo_stat.GetSize(), 3)
      self.assertTrue(stat_mock.called)

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      bar_stat = stat_cache.Get(self.Path("bar"))
      self.assertEqual(bar_stat.GetSize(), 6)
      self.assertTrue(stat_mock.called)

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      other_foo_stat = stat_cache.Get(self.Path("foo"))
      self.assertEqual(other_foo_stat.GetSize(), 3)
      self.assertFalse(stat_mock.called)

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      other_bar_stat = stat_cache.Get(self.Path("bar"))
      self.assertEqual(other_bar_stat.GetSize(), 6)
      self.assertFalse(stat_mock.called)

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      baz_stat = stat_cache.Get(self.Path("baz"))
      self.assertEqual(baz_stat.GetSize(), 9)
      self.assertTrue(stat_mock.called)

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      other_baz_stat = stat_cache.Get(self.Path("baz"))
      self.assertEqual(other_baz_stat.GetSize(), 9)
      self.assertFalse(stat_mock.called)

  def testFollowSymlink(self):
    with open(self.Path("foo"), "w") as fd:
      fd.write("123456")
    os.symlink(self.Path("foo"), self.Path("bar"))

    stat_cache = utils.StatCache()

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      bar_stat = stat_cache.Get(self.Path("bar"), follow_symlink=False)
      self.assertTrue(bar_stat.IsSymlink())
      self.assertTrue(stat_mock.called)

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      foo_stat = stat_cache.Get(self.Path("bar"), follow_symlink=True)
      self.assertFalse(foo_stat.IsSymlink())
      self.assertEqual(foo_stat.GetSize(), 6)
      self.assertTrue(stat_mock.called)

  def testSmartSymlinkCache(self):
    with open(self.Path("foo"), "w") as fd:
      fd.write("12345")

    stat_cache = utils.StatCache()

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      foo_stat = stat_cache.Get(self.Path("foo"), follow_symlink=False)
      self.assertEqual(foo_stat.GetSize(), 5)
      self.assertTrue(stat_mock.called)

    with mock.patch.object(utils, "Stat", wraps=utils.Stat) as stat_mock:
      other_foo_stat = stat_cache.Get(self.Path("foo"), follow_symlink=True)
      self.assertEqual(other_foo_stat.GetSize(), 5)
      self.assertFalse(stat_mock.called)


class IterValuesInSortedKeysOrderTest(absltest.TestCase):

  def testYieldsSingleValueCorrectly(self):
    self.assertEqual([42], list(utils.IterValuesInSortedKeysOrder({"a": 42})))

  def testYieldsMultipleValuesInCorrectOrder(self):
    self.assertEqual([44, 42, 43],
                     list(
                         utils.IterValuesInSortedKeysOrder({
                             "a": 44,
                             "b": 42,
                             "c": 43
                         })))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
