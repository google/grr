#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for utility classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import threading
import zipfile

from absl import app
from absl.testing import absltest

from future.builtins import int
from future.builtins import range

import mock

from grr_response_core.lib import utils
from grr_response_core.lib.util import compatibility
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


class RunOnceTest(absltest.TestCase):

  def testDecoratedFunctionIsCalledAtLeastOnce(self):
    mock_fn = mock.Mock()
    mock_fn.__name__ = compatibility.NativeStr("MockFunction")
    fn = utils.RunOnce(mock_fn)
    mock_fn.assert_not_called()
    fn()
    mock_fn.assert_called_once()

  def testDecoratedFunctionIsCalledAtMostOnce(self):
    mock_fn = mock.Mock(side_effect=[None, AssertionError()])
    mock_fn.__name__ = compatibility.NativeStr("MockFunction")
    fn = utils.RunOnce(mock_fn)
    fn()
    fn()
    fn()
    mock_fn.assert_called_once()

  def testArgumentsArePassedThrough(self):
    mock_fn = mock.Mock()
    mock_fn.__name__ = compatibility.NativeStr("MockFunction")
    fn = utils.RunOnce(mock_fn)
    fn(1, 2, foo="bar")
    mock_fn.assert_called_once_with(1, 2, foo="bar")

  def testReturnValueIsPassedThrough(self):
    mock_fn = mock.Mock(return_value="bar")
    mock_fn.__name__ = compatibility.NativeStr("MockFunction")
    fn = utils.RunOnce(mock_fn)
    self.assertEqual("bar", fn())

  def testReturnValueForFollowingCallsIsCached(self):
    result = object()
    mock_fn = mock.Mock(side_effect=[result])
    mock_fn.__name__ = compatibility.NativeStr("MockFunction")
    fn = utils.RunOnce(mock_fn)
    self.assertIs(fn(), result)
    self.assertIs(fn(), result)

  def testExceptionsArePassedThrough(self):
    mock_fn = mock.Mock(side_effect=ValueError())
    mock_fn.__name__ = compatibility.NativeStr("MockFunction")
    fn = utils.RunOnce(mock_fn)
    with self.assertRaises(ValueError):
      fn()
    with self.assertRaises(ValueError):
      fn()

  def testWrapsFunctionProperly(self):
    mock_fn = mock.Mock()
    mock_fn.__name__ = compatibility.NativeStr("MockFunction")
    fn = utils.RunOnce(mock_fn)
    self.assertEqual(fn.__name__, compatibility.NativeStr("MockFunction"))


class StreamingZipGeneratorTest(absltest.TestCase):

  def testSingleFile(self):
    archiver = utils.StreamingZipGenerator()
    output = io.BytesIO()

    output.write(archiver.WriteFileHeader("foo"))
    output.write(archiver.WriteFileChunk(b"bar"))
    output.write(archiver.WriteFileChunk(b"baz"))
    output.write(archiver.WriteFileFooter())

    output.write(archiver.Close())

    with zipfile.ZipFile(output, mode="r") as zipdesc:
      self.assertEqual(zipdesc.read("foo"), b"barbaz")

  def testMultipleFiles(self):
    archiver = utils.StreamingZipGenerator()
    output = io.BytesIO()

    output.write(archiver.WriteFileHeader("foo"))
    output.write(archiver.WriteFileChunk(b"quux"))
    output.write(archiver.WriteFileFooter())

    output.write(archiver.WriteFileHeader("bar"))
    output.write(archiver.WriteFileChunk(b"norf"))
    output.write(archiver.WriteFileFooter())

    output.write(archiver.Close())

    with zipfile.ZipFile(output, mode="r") as zipdesc:
      self.assertEqual(zipdesc.read("foo"), b"quux")
      self.assertEqual(zipdesc.read("bar"), b"norf")

  def testHierarchy(self):
    archiver = utils.StreamingZipGenerator()
    output = io.BytesIO()

    output.write(archiver.WriteFileHeader("foo/bar/baz"))
    output.write(archiver.WriteFileChunk(b"quux"))
    output.write(archiver.WriteFileFooter())

    output.write(archiver.Close())

    with zipfile.ZipFile(output, mode="r") as zipdesc:
      self.assertEqual(zipdesc.read("foo/bar/baz"), b"quux")

  def testCompression(self):
    archiver = utils.StreamingZipGenerator(zipfile.ZIP_DEFLATED)
    output = io.BytesIO()

    output.write(archiver.WriteFileHeader("foo"))
    output.write(archiver.WriteFileChunk(b"quux"))
    output.write(archiver.WriteFileChunk(b"norf"))
    output.write(archiver.WriteFileFooter())

    output.write(archiver.Close())

    with zipfile.ZipFile(output, mode="r") as zipdesc:
      self.assertEqual(zipdesc.read("foo"), b"quuxnorf")

  def testWriteFromFD(self):
    filedesc = io.BytesIO(b"foobarbaz" * 1024 * 1024)

    archiver = utils.StreamingZipGenerator()
    output = io.BytesIO()

    for chunk in archiver.WriteFromFD(filedesc, "quux"):
      output.write(chunk)

    output.write(archiver.Close())

    with zipfile.ZipFile(output, mode="r") as zipdesc:
      self.assertEqual(zipdesc.read("quux"), filedesc.getvalue())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
