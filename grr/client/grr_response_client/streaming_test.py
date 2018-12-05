#!/usr/bin/env python
"""Tests for the streaming utility classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import functools
import os


from absl.testing import absltest
from future.utils import with_metaclass

from grr_response_client import streaming
from grr_response_client.client_actions.file_finder_utils import conditions
from grr_response_core.lib import flags
from grr.test_lib import temp
from grr.test_lib import test_lib


class StreamerTestMixin(with_metaclass(abc.ABCMeta, object)):

  @abc.abstractmethod
  def Stream(self, streamer, data):
    pass

  def testNoOverlap(self):
    streamer = streaming.Streamer(chunk_size=3, overlap_size=0)
    method = self.Stream(streamer, "abcdefgh")
    chunks = list(method(amount=8))

    self.assertLen(chunks, 3)
    self.assertEqual(chunks[0].data, "abc")
    self.assertEqual(chunks[1].data, "def")
    self.assertEqual(chunks[2].data, "gh")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 3)
    self.assertEqual(chunks[2].offset, 6)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 0)
    self.assertEqual(chunks[2].overlap, 0)

  def testOneByteOverlap(self):
    streamer = streaming.Streamer(chunk_size=3, overlap_size=1)
    method = self.Stream(streamer, "abcdef")
    chunks = list(method(amount=8))

    self.assertLen(chunks, 3)
    self.assertEqual(chunks[0].data, "abc")
    self.assertEqual(chunks[1].data, "cde")
    self.assertEqual(chunks[2].data, "ef")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 2)
    self.assertEqual(chunks[2].offset, 4)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 1)
    self.assertEqual(chunks[2].overlap, 1)

  def testZeroAmount(self):
    streamer = streaming.Streamer(chunk_size=3, overlap_size=0)
    method = self.Stream(streamer, "abcdef")
    chunks = list(method(amount=0))

    self.assertEmpty(chunks)

  def testSmallAmount(self):
    streamer = streaming.Streamer(chunk_size=1, overlap_size=0)
    method = self.Stream(streamer, "abc")
    chunks = list(method(amount=2))

    self.assertLen(chunks, 2)
    self.assertEqual(chunks[0].data, "a")
    self.assertEqual(chunks[1].data, "b")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 1)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 0)

  def testSingleChunk(self):
    streamer = streaming.Streamer(chunk_size=8, overlap_size=2)
    method = self.Stream(streamer, "abcdef")
    chunks = list(method(amount=7))

    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].data, "abcdef")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].overlap, 0)

  def testNoData(self):
    streamer = streaming.Streamer(chunk_size=3, overlap_size=1)
    method = self.Stream(streamer, "")
    chunks = list(method(amount=5))

    self.assertEmpty(chunks)

  def testOffset(self):
    streamer = streaming.Streamer(chunk_size=3, overlap_size=2)
    method = self.Stream(streamer, "abcdefghi")
    chunks = list(method(offset=4, amount=108))

    self.assertLen(chunks, 3)
    self.assertEqual(chunks[0].data, "efg")
    self.assertEqual(chunks[1].data, "fgh")
    self.assertEqual(chunks[2].data, "ghi")
    self.assertEqual(chunks[0].offset, 4)
    self.assertEqual(chunks[1].offset, 5)
    self.assertEqual(chunks[2].offset, 6)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 2)
    self.assertEqual(chunks[2].overlap, 2)

  def testShorterOverlap(self):
    streamer = streaming.Streamer(chunk_size=4, overlap_size=2)
    method = self.Stream(streamer, "abcdefg")
    chunks = list(method(amount=1024))

    self.assertLen(chunks, 3)
    self.assertEqual(chunks[0].data, "abcd")
    self.assertEqual(chunks[1].data, "cdef")
    self.assertEqual(chunks[2].data, "efg")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 2)
    self.assertEqual(chunks[2].offset, 4)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 2)
    self.assertEqual(chunks[2].overlap, 2)

  def testUnbound(self):
    streamer = streaming.Streamer(chunk_size=9, overlap_size=2)
    method = self.Stream(streamer, "abcdefghijklmnopqrstuvwxyz")
    chunks = list(method())

    self.assertLen(chunks, 4)
    self.assertEqual(chunks[0].data, "abcdefghi")
    self.assertEqual(chunks[1].data, "hijklmnop")
    self.assertEqual(chunks[2].data, "opqrstuvw")
    self.assertEqual(chunks[3].data, "vwxyz")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 7)
    self.assertEqual(chunks[2].offset, 14)
    self.assertEqual(chunks[3].offset, 21)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 2)
    self.assertEqual(chunks[2].overlap, 2)
    self.assertEqual(chunks[3].overlap, 2)


class StreamFilePathTest(StreamerTestMixin, absltest.TestCase):

  def setUp(self):
    super(StreamFilePathTest, self).setUp()
    self.temp_filepath = temp.TempFilePath()

  def tearDown(self):
    super(StreamFilePathTest, self).tearDown()
    os.remove(self.temp_filepath)

  def Stream(self, streamer, data):
    with open(self.temp_filepath, "wb") as filedesc:
      filedesc.write(data)

    return functools.partial(streamer.StreamFilePath, self.temp_filepath)


class StreamMemoryTest(StreamerTestMixin, absltest.TestCase):

  def Stream(self, streamer, data):
    process = StubProcess(data)
    return functools.partial(streamer.StreamMemory, process)


class ReaderTestMixin(with_metaclass(abc.ABCMeta, object)):

  @abc.abstractmethod
  def Prepare(self, data, callback, offset=0):
    pass

  def testReadNormal(self):
    data = "foobarbaz"

    def Assertions(reader):
      self.assertEqual(reader.offset, 0)
      self.assertEqual(reader.Read(1), "f")
      self.assertEqual(reader.offset, 1)
      self.assertEqual(reader.Read(2), "oo")
      self.assertEqual(reader.offset, 3)
      self.assertEqual(reader.Read(3), "bar")
      self.assertEqual(reader.offset, 6)
      self.assertEqual(reader.Read(3), "baz")
      self.assertEqual(reader.offset, 9)

    self.Prepare(data, Assertions)

  def testReadTruncated(self):
    data = "foobar"

    def Assertions(reader):
      self.assertEqual(reader.offset, 0)
      self.assertEqual(reader.Read(3), "foo")
      self.assertEqual(reader.offset, 3)
      self.assertEqual(reader.Read(6), "bar")
      self.assertEqual(reader.offset, 6)

    self.Prepare(data, Assertions)

  def testOffset(self):
    data = "foobar"

    def Assertions(reader):
      self.assertEqual(reader.offset, 3)
      self.assertEqual(reader.Read(3), "bar")
      self.assertEqual(reader.offset, 6)

    self.Prepare(data, Assertions, offset=3)


class FileReaderTest(ReaderTestMixin, absltest.TestCase):

  def setUp(self):
    super(FileReaderTest, self).setUp()
    self.temp_filepath = temp.TempFilePath()

  def tearDown(self):
    super(FileReaderTest, self).tearDown()
    os.remove(self.temp_filepath)

  def Prepare(self, data, callback, offset=0):
    with open(self.temp_filepath, "w") as filedesc:
      filedesc.write(data)

    with open(self.temp_filepath, "r") as filedesc:
      reader = streaming.FileReader(filedesc, offset=offset)
      callback(reader)


class MemoryReaderTest(ReaderTestMixin, absltest.TestCase):

  def Prepare(self, data, callback, offset=0):
    process = StubProcess(data)
    reader = streaming.MemoryReader(process, offset=offset)
    callback(reader)


class StubProcess(object):

  def __init__(self, memory):
    self.memory = memory

  def ReadBytes(self, address, num_bytes):
    return self.memory[address:address + num_bytes]


class ChunkTest(absltest.TestCase):

  Span = conditions.Matcher.Span  # pylint: disable=invalid-name

  def testScanSingleHit(self):
    data = "foobarbaz"
    chunk = streaming.Chunk(offset=0, data=data)
    spans = list(chunk.Scan(conditions.LiteralMatcher("bar")))

    self.assertLen(spans, 1)
    self.assertEqual(spans[0], self.Span(begin=3, end=6))

  def testScanMultiHit(self):
    data = "foobarfoo"
    chunk = streaming.Chunk(offset=0, data=data)
    spans = list(chunk.Scan(conditions.LiteralMatcher("foo")))

    self.assertLen(spans, 2)
    self.assertEqual(spans[0], self.Span(begin=0, end=3))
    self.assertEqual(spans[1], self.Span(begin=6, end=9))

  def testScanOverlappedHits(self):
    data = "xoxoxoxo"
    chunk = streaming.Chunk(offset=0, data=data)
    spans = list(chunk.Scan(conditions.LiteralMatcher("xoxo")))

    self.assertLen(spans, 2)
    self.assertEqual(spans[0], self.Span(begin=0, end=4))
    self.assertEqual(spans[1], self.Span(begin=4, end=8))

  def testScanWithOverlap(self):
    data = "foofoobarfoofoo"
    chunk = streaming.Chunk(offset=0, data=data, overlap=8)
    spans = list(chunk.Scan(conditions.LiteralMatcher("foo")))

    self.assertLen(spans, 2)
    self.assertEqual(spans[0], self.Span(begin=9, end=12))
    self.assertEqual(spans[1], self.Span(begin=12, end=15))

  def testScanWithOverlapOverlapping(self):
    data = "oooooo"
    chunk = streaming.Chunk(offset=0, data=data, overlap=3)
    spans = list(chunk.Scan(conditions.LiteralMatcher("oo")))

    self.assertLen(spans, 2)
    self.assertEqual(spans[0], self.Span(begin=2, end=4))
    self.assertEqual(spans[1], self.Span(begin=4, end=6))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
