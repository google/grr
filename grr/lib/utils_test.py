#!/usr/bin/env python
"""Tests for utility classes."""


import os
import StringIO
import tarfile
import threading
import zipfile


from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils

# Test method names dont conform with Google style
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
    self.assertEqual(results, range(0, 5))

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
        utils.FormatAsHexString(
            int(1e19), 5), "0x8ac7230489e80000")

  def testXor(self):
    test_str = "Hello World!!"
    for key in [1, 5, 123, 255]:
      xor_str = utils.Xor(test_str, key)
      self.assertNotEqual(xor_str, test_str)
      xor_str = utils.Xor(xor_str, key)
      self.assertEqual(xor_str, test_str)

  def testXorByteArray(self):
    test_arr = bytearray("Hello World!!")
    for key in [1, 5, 123, 255]:
      xor_arr = bytearray(test_arr)
      utils.XorByteArray(xor_arr, key)
      self.assertNotEqual(xor_arr, test_arr)
      utils.XorByteArray(xor_arr, key)
      self.assertEqual(xor_arr, test_arr)

  def LinkedListTest(self):

    l = utils.LinkedList()

    # Test empty list properties.
    self.assertEqual(len(l), 0)
    self.assertEqual(list(l), [])
    self.assertRaises(IndexError, l.Pop)
    self.assertRaises(IndexError, l.PopLeft)
    self.CheckList(l)

    # Just one element.
    l.Append(1)
    self.CheckList(l)
    self.assertEqual(len(l), 1)
    self.assertEqual(list(l), [1])

    # Pop it, check that list is empty again.
    self.assertEqual(l.Pop(), 1)
    self.CheckList(l)
    self.assertEqual(len(l), 0)
    self.assertEqual(list(l), [])
    self.assertRaises(IndexError, l.Pop)
    self.assertRaises(IndexError, l.PopLeft)

    # Simple popleft test.
    l.Append(1)
    self.assertEqual(len(l), 1)
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

    self.assertEqual(len(l), 7)
    self.assertEqual(list(l), [1, 2, 3, 4, 5, 6, 7])

    # Unlink a node in the middle.
    l.Unlink(node3)
    self.CheckList(l)

    self.assertEqual(len(l), 6)
    self.assertEqual(list(l), [1, 2, 4, 5, 6, 7])

    # Unlink head.
    l.Unlink(l.head)
    self.CheckList(l)

    self.assertEqual(len(l), 5)
    self.assertEqual(list(l), [2, 4, 5, 6, 7])

    # Unlink tail.
    l.Unlink(l.tail)
    self.CheckList(l)

    # Some more unlinks.
    self.assertEqual(len(l), 4)
    self.assertEqual(list(l), [2, 4, 5, 6])
    self.CheckList(l)

    self.assertEqual(l.PopLeft(), 2)
    self.assertEqual(len(l), 3)
    self.assertEqual(list(l), [4, 5, 6])
    self.CheckList(l)

    self.assertEqual(l.Pop(), 6)
    self.assertEqual(len(l), 2)
    self.assertEqual(list(l), [4, 5])
    self.CheckList(l)

    l.Append(6)
    self.assertEqual(l.Pop(), 6)
    self.assertEqual(len(l), 2)
    self.assertEqual(list(l), [4, 5])
    self.CheckList(l)

    self.assertEqual(l.Pop(), 5)
    self.assertEqual(len(l), 1)
    self.assertEqual(list(l), [4])
    self.CheckList(l)

    self.assertEqual(l.PopLeft(), 4)
    self.assertEqual(len(l), 0)
    self.CheckList(l)

    self.assertRaises(IndexError, l.Pop)
    self.assertRaises(IndexError, l.PopLeft)

    # Unlink the only element present.
    l = utils.LinkedList()
    n = l.Append(1)
    l.Unlink(n)
    self.assertEqual(len(l), 0)
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

  def testMemoize(self):

    class Concat(object):
      append_count = 0

      @utils.Memoize()
      def concat(self, prefix, suffix):
        Concat.append_count += 1
        return prefix + "," + suffix

    for _ in range(5):
      self.assertEqual(Concat().concat(prefix="a", suffix="b"), "a,b")
    self.assertEqual(Concat.append_count, 1)

    class Fibber(object):
      fib_count = 0

      @utils.Memoize()
      def fib(self, x):
        Fibber.fib_count += 1
        if x < 2:
          return x
        return self.fib(x - 1) + self.fib(x - 2)

    self.assertEqual(Fibber().fib(20), 6765)
    # Memoized fibbonaci runs once per value of x used, naive fibbonaci runs
    # proportionaly to the output value.
    self.assertEqual(Fibber.fib_count, 21)

  def testMemoizeFunction(self):

    @utils.MemoizeFunction()
    def concat(prefix, suffix):
      return prefix + "," + suffix

    self.assertEqual(concat(prefix="a", suffix="b"), "a,b")


class RollingMemoryStreamTest(test_lib.GRRBaseTest):
  """Tests for RollingMemoryStream."""

  def setUp(self):
    super(RollingMemoryStreamTest, self).setUp()
    self.stream = utils.RollingMemoryStream()

  def testGetValueAndResetReturnsSingleWrittenValue(self):
    self.stream.write("blah")
    self.assertEqual(self.stream.GetValueAndReset(), "blah")

  def testSecondCallToGetValueAndResetReturnsEmptyValue(self):
    self.stream.write("blah")
    self.stream.GetValueAndReset()
    self.assertEqual(self.stream.GetValueAndReset(), "")

  def testGetValueAndResetReturnsLastValueSincePreviousReset(self):
    self.stream.write("foo")
    self.stream.GetValueAndReset()
    self.stream.write("bar")
    self.assertEqual(self.stream.GetValueAndReset(), "bar")

  def testWriteAfterCloseRaises(self):
    self.stream.close()
    with self.assertRaises(utils.ArchiveAlreadyClosedError):
      self.stream.write("blah")


class StreamingZipWriterTest(test_lib.GRRBaseTest):
  """Tests for StreamingZipWriter."""

  def testZipFileWithOneFile(self):
    """Test the zipfile implementation."""
    compressions = [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED]
    for compression in compressions:
      outfd = StringIO.StringIO()

      # Write the zip into a file like object.
      infd = StringIO.StringIO("this is a test string")
      with utils.StreamingZipWriter(outfd, compression=compression) as writer:
        writer.WriteFromFD(infd, "test.txt")

      test_zip = zipfile.ZipFile(outfd, "r")
      test_zip.testzip()

      self.assertEqual(test_zip.namelist(), ["test.txt"])
      self.assertEqual(test_zip.read("test.txt"), infd.getvalue())

  def testZipFileWithMultipleFiles(self):
    """Test the zipfile implementation."""
    compressions = [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED]
    for compression in compressions:
      outfd = StringIO.StringIO()

      # Write the zip into a file like object.
      infd1 = StringIO.StringIO("this is a test string")
      infd2 = StringIO.StringIO("this is another test string")
      with utils.StreamingZipWriter(outfd, compression=compression) as writer:
        writer.WriteFromFD(infd1, "test1.txt")
        writer.WriteFromFD(infd2, "test2.txt")

      test_zip = zipfile.ZipFile(outfd, "r")
      test_zip.testzip()

      self.assertEqual(sorted(test_zip.namelist()), ["test1.txt", "test2.txt"])
      self.assertEqual(test_zip.read("test1.txt"), infd1.getvalue())

      self.assertEqual(sorted(test_zip.namelist()), ["test1.txt", "test2.txt"])
      self.assertEqual(test_zip.read("test2.txt"), infd2.getvalue())

  def testZipFileWithSymlink(self):
    """Test that symlinks are preserved when unpacking generated zips."""

    compressions = [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED]
    for compression in compressions:
      outfd = StringIO.StringIO()

      infd1 = StringIO.StringIO("this is a test string")
      infd2 = StringIO.StringIO("this is another test string")
      with utils.StreamingZipWriter(outfd, compression=compression) as writer:
        writer.WriteFromFD(infd1, "test1.txt")
        writer.WriteFromFD(infd2, "subdir/test2.txt")

        writer.WriteSymlink("test1.txt", "test1.txt.link")
        writer.WriteSymlink("subdir/test2.txt", "test2.txt.link")

      with utils.TempDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "archive.zip")
        with open(zip_path, "w") as fd:
          fd.write(outfd.getvalue())

        zip_fd = zipfile.ZipFile(outfd, "r")

        link_info = zip_fd.getinfo("test1.txt.link")
        self.assertEqual(link_info.external_attr, (0644 | 0120000) << 16)
        self.assertEqual(link_info.create_system, 3)

        link_contents = zip_fd.read("test1.txt.link")
        self.assertEqual(link_contents, "test1.txt")

        link_info = zip_fd.getinfo("test2.txt.link")
        self.assertEqual(link_info.external_attr, (0644 | 0120000) << 16)
        self.assertEqual(link_info.create_system, 3)

        link_contents = zip_fd.read("test2.txt.link")
        self.assertEqual(link_contents, "subdir/test2.txt")


class StreamingTarWriterTest(test_lib.GRRBaseTest):
  """Tests for StreamingTarWriter."""

  def testTarFileWithOneFile(self):
    infd = StringIO.StringIO("this is a test string")
    st = os.stat_result((0644, 0, 0, 0, 0, 0, len(infd.getvalue()), 0, 0, 0))

    # Write the tar into a file like object.
    outfd = StringIO.StringIO()
    with utils.StreamingTarWriter(outfd, mode="w:gz") as writer:
      writer.WriteFromFD(infd, "test.txt", st=st)

    test_tar = tarfile.open(fileobj=StringIO.StringIO(outfd.getvalue()),
                            mode="r")
    tinfos = list(test_tar.getmembers())

    self.assertEqual(len(tinfos), 1)
    self.assertEqual(tinfos[0].name, "test.txt")

    fd = test_tar.extractfile(tinfos[0])
    self.assertEqual(fd.read(1024), infd.getvalue())

  def testTarFileWithMultipleFiles(self):
    outfd = StringIO.StringIO()

    infd1 = StringIO.StringIO("this is a test string")
    st1 = os.stat_result((0644, 0, 0, 0, 0, 0, len(infd1.getvalue()), 0, 0, 0))

    infd2 = StringIO.StringIO("this is another test string")
    st2 = os.stat_result((0644, 0, 0, 0, 0, 0, len(infd2.getvalue()), 0, 0, 0))

    # Write the tar into a file like object.
    with utils.StreamingTarWriter(outfd, mode="w:gz") as writer:
      writer.WriteFromFD(infd1, "test1.txt", st=st1)
      writer.WriteFromFD(infd2, "subdir/test2.txt", st=st2)

    test_tar = tarfile.open(fileobj=StringIO.StringIO(outfd.getvalue()),
                            mode="r")
    tinfos = sorted(test_tar.getmembers(), key=lambda tinfo: tinfo.name)

    self.assertEqual(len(tinfos), 2)
    self.assertEqual(tinfos[0].name, "subdir/test2.txt")
    self.assertEqual(tinfos[1].name, "test1.txt")

    fd = test_tar.extractfile(tinfos[0])
    self.assertEqual(fd.read(1024), infd2.getvalue())

    fd = test_tar.extractfile(tinfos[1])
    self.assertEqual(fd.read(1024), infd1.getvalue())

  def testTarFileWithSymlink(self):
    outfd = StringIO.StringIO()

    infd1 = StringIO.StringIO("this is a test string")
    st1 = os.stat_result((0644, 0, 0, 0, 0, 0, len(infd1.getvalue()), 0, 0, 0))

    infd2 = StringIO.StringIO("this is another test string")
    st2 = os.stat_result((0644, 0, 0, 0, 0, 0, len(infd2.getvalue()), 0, 0, 0))

    # Write the zip into a file like object.
    with utils.StreamingTarWriter(outfd, mode="w:gz") as writer:
      writer.WriteFromFD(infd1, "test1.txt", st=st1)
      writer.WriteFromFD(infd2, "subdir/test2.txt", st=st2)

      writer.WriteSymlink("test1.txt", "test1.txt.link")
      writer.WriteSymlink("subdir/test2.txt", "test2.txt.link")

    with tarfile.open(fileobj=StringIO.StringIO(outfd.getvalue()),
                      mode="r") as test_fd:
      test_fd.extractall(self.temp_dir)

      link_path = os.path.join(self.temp_dir, "test1.txt.link")
      self.assertTrue(os.path.islink(link_path))
      self.assertEqual(os.readlink(link_path), "test1.txt")

      link_path = os.path.join(self.temp_dir, "test2.txt.link")
      self.assertTrue(os.path.islink(link_path))
      self.assertEqual(os.readlink(link_path), "subdir/test2.txt")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
