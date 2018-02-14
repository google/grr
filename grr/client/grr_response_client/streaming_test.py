#!/usr/bin/env python
"""Tests for the streaming utility classes."""

import os

import unittest
from grr_response_client import streaming
from grr_response_client.client_actions.file_finder_utils import conditions
from grr.lib import flags
from grr.test_lib import test_lib


class FileStreamerTest(unittest.TestCase):

  def setUp(self):
    self.temp_filepath = test_lib.TempFilePath()

  def tearDown(self):
    os.remove(self.temp_filepath)

  def testNoOverlap(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("abcdefgh")

    streamer = streaming.FileStreamer(chunk_size=3, overlap_size=0)
    chunks = list(streamer.StreamFilePath(self.temp_filepath, amount=8))

    self.assertEqual(len(chunks), 3)
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
    with open(self.temp_filepath, "wb") as fd:
      fd.write("abcdef")

    streamer = streaming.FileStreamer(chunk_size=3, overlap_size=1)
    chunks = list(streamer.StreamFilePath(self.temp_filepath, amount=8))

    self.assertEqual(len(chunks), 3)
    self.assertEqual(chunks[0].data, "abc")
    self.assertEqual(chunks[1].data, "cde")
    self.assertEqual(chunks[2].data, "ef")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 2)
    self.assertEqual(chunks[2].offset, 4)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 1)
    self.assertEqual(chunks[2].overlap, 1)

  def testSmallAmount(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("abc")

    streamer = streaming.FileStreamer(chunk_size=1, overlap_size=0)
    chunks = list(streamer.StreamFilePath(self.temp_filepath, amount=2))

    self.assertEqual(len(chunks), 2)
    self.assertEqual(chunks[0].data, "a")
    self.assertEqual(chunks[1].data, "b")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 1)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 0)

  def testSingleChunk(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("abcdef")

    streamer = streaming.FileStreamer(chunk_size=8, overlap_size=2)
    chunks = list(streamer.StreamFilePath(self.temp_filepath, amount=7))

    self.assertEqual(len(chunks), 1)
    self.assertEqual(chunks[0].data, "abcdef")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].overlap, 0)

  def testNoData(self):
    streamer = streaming.FileStreamer(chunk_size=3, overlap_size=1)
    chunks = list(streamer.StreamFilePath(self.temp_filepath, amount=5))

    self.assertEqual(len(chunks), 0)

  def testOffset(self):
    with open(self.temp_filepath, "wb") as fd:
      fd.write("abcdefghi")

    streamer = streaming.FileStreamer(chunk_size=3, overlap_size=2)
    stream = streamer.StreamFilePath(self.temp_filepath, offset=4, amount=108)
    chunks = list(stream)

    self.assertEqual(len(chunks), 3)
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
    with open(self.temp_filepath, "wb") as fd:
      fd.write("abcdefg")

    streamer = streaming.FileStreamer(chunk_size=4, overlap_size=2)
    chunks = list(streamer.StreamFilePath(self.temp_filepath, amount=1024))

    self.assertEqual(len(chunks), 3)
    self.assertEqual(chunks[0].data, "abcd")
    self.assertEqual(chunks[1].data, "cdef")
    self.assertEqual(chunks[2].data, "efg")
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[1].offset, 2)
    self.assertEqual(chunks[2].offset, 4)
    self.assertEqual(chunks[0].overlap, 0)
    self.assertEqual(chunks[1].overlap, 2)
    self.assertEqual(chunks[2].overlap, 2)


class ChunkTest(unittest.TestCase):

  Span = conditions.Matcher.Span  # pylint: disable=invalid-name

  def testScanSingleHit(self):
    data = "foobarbaz"
    chunk = streaming.Chunk(offset=0, data=data)
    spans = list(chunk.Scan(conditions.LiteralMatcher("bar")))

    self.assertEqual(len(spans), 1)
    self.assertEqual(spans[0], self.Span(begin=3, end=6))

  def testScanMultiHit(self):
    data = "foobarfoo"
    chunk = streaming.Chunk(offset=0, data=data)
    spans = list(chunk.Scan(conditions.LiteralMatcher("foo")))

    self.assertEqual(len(spans), 2)
    self.assertEqual(spans[0], self.Span(begin=0, end=3))
    self.assertEqual(spans[1], self.Span(begin=6, end=9))

  def testScanOverlappedHits(self):
    data = "xoxoxoxo"
    chunk = streaming.Chunk(offset=0, data=data)
    spans = list(chunk.Scan(conditions.LiteralMatcher("xoxo")))

    self.assertEqual(len(spans), 2)
    self.assertEqual(spans[0], self.Span(begin=0, end=4))
    self.assertEqual(spans[1], self.Span(begin=4, end=8))

  def testScanWithOverlap(self):
    data = "foofoobarfoofoo"
    chunk = streaming.Chunk(offset=0, data=data, overlap=8)
    spans = list(chunk.Scan(conditions.LiteralMatcher("foo")))

    self.assertEqual(len(spans), 2)
    self.assertEqual(spans[0], self.Span(begin=9, end=12))
    self.assertEqual(spans[1], self.Span(begin=12, end=15))

  def testScanWithOverlapOverlapping(self):
    data = "oooooo"
    chunk = streaming.Chunk(offset=0, data=data, overlap=3)
    spans = list(chunk.Scan(conditions.LiteralMatcher("oo")))

    self.assertEqual(len(spans), 2)
    self.assertEqual(spans[0], self.Span(begin=2, end=4))
    self.assertEqual(spans[1], self.Span(begin=4, end=6))


class MockProcess(object):

  def __init__(self, data):
    self.data = data

  def ReadBytes(self, offset, length):
    return self.data[offset:offset + length]


class MemoryStreamerTest(unittest.TestCase):

  def testStreaming(self):
    data = "foofoobarfoofoo"
    p = MockProcess(data)

    s = streaming.MemoryStreamer(p, chunk_size=1000, overlap_size=0)

    res = [chunk.data for chunk in s.Stream(0, 100)]
    self.assertEqual("".join(res), data)

    res = []
    res.extend(chunk.data for chunk in s.Stream(0, 6))
    res.extend(chunk.data for chunk in s.Stream(6, 100))
    self.assertEqual("".join(res), data)

  def testChunking(self):
    data = "foofoobarfoofoo"
    p = MockProcess(data)

    s = streaming.MemoryStreamer(p, chunk_size=2, overlap_size=0)

    res = [chunk.data for chunk in s.Stream(0, 100)]
    self.assertEqual("".join(res), data)

    res = []
    res.extend(chunk.data for chunk in s.Stream(0, 6))
    res.extend(chunk.data for chunk in s.Stream(6, 100))
    self.assertEqual("".join(res), data)

  def testOddChunkSize(self):
    data = "foofoobarfoofoo"
    p = MockProcess(data)

    s = streaming.MemoryStreamer(p, chunk_size=2, overlap_size=0)

    res = [len(chunk.data) for chunk in s.Stream(0, 100)]
    self.assertEqual(res, [2, 2, 2, 2, 2, 2, 2, 1])

  def testOverlap(self):
    data = "foofoobarfoofoo"

    p = MockProcess(data)
    s = streaming.MemoryStreamer(p, chunk_size=5, overlap_size=2)
    res = [chunk.data for chunk in s.Stream(0, 100)]

    # Original data is length 15, we get 5 chars in the first chunk + 3 more in
    # each additional one. The last chunk is short (2 overlap+ 1 data).
    self.assertEqual(len(res), 5)
    self.assertEqual(map(len, res), [5, 5, 5, 5, 3])
    for i in range(len(res) - 1):
      self.assertEqual(res[i][-2:], res[i + 1][:2])

    self.assertEqual([chunk.offset for chunk in s.Stream(0, 100)],
                     [0, 3, 6, 9, 12])
    self.assertEqual([chunk.overlap for chunk in s.Stream(0, 100)],
                     [0, 2, 2, 2, 2])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
