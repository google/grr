#!/usr/bin/env python
import io
import itertools
from absl.testing import absltest

from grr_response_core.lib.util import io as ioutil


class ChunkTest(absltest.TestCase):

  def testSizeZero(self):
    with self.assertRaises(ValueError):
      list(ioutil.Chunk(io.BytesIO(b"foobar"), size=0))

  def testSizeNegative(self):
    with self.assertRaises(ValueError):
      list(ioutil.Chunk(io.BytesIO(b"foobar"), size=-42))

  def testEmpty(self):
    chunks = list(ioutil.Chunk(io.BytesIO(b""), size=3))
    self.assertEmpty(chunks)

  def testSingleChunk(self):
    chunks = list(ioutil.Chunk(io.BytesIO(b"foobar"), size=6))
    self.assertEqual(chunks, [b"foobar"])

  def testManyEvenChunks(self):
    chunks = list(ioutil.Chunk(io.BytesIO(b"foobar"), size=2))
    self.assertEqual(chunks, [b"fo", b"ob", b"ar"])

  def testManyUnevenChunks(self):
    chunks = list(ioutil.Chunk(io.BytesIO(b"foobarbaz"), size=2))
    self.assertEqual(chunks, [b"fo", b"ob", b"ar", b"ba", b"z"])


class UnchunkedTest(absltest.TestCase):

  def testEmpty(self):
    stream = ioutil.Unchunk(iter([]))
    self.assertEqual(stream.read(), b"")

  def testSingleChunkReadWhole(self):
    stream = ioutil.Unchunk(iter([b"foobar"]))
    self.assertEqual(stream.read(), b"foobar")

  def testSingleChunkReadByByte(self):
    stream = ioutil.Unchunk(iter([b"foo"]))
    self.assertEqual(stream.read(1), b"f")
    self.assertEqual(stream.read(1), b"o")
    self.assertEqual(stream.read(1), b"o")
    self.assertEqual(stream.read(1), b"")

  def testMultiChunkReadByByte(self):
    stream = ioutil.Unchunk(iter([b"foo", b"bar", b"baz"]))
    self.assertEqual(stream.read(1), b"f")
    self.assertEqual(stream.read(1), b"o")
    self.assertEqual(stream.read(1), b"o")
    self.assertEqual(stream.read(1), b"b")
    self.assertEqual(stream.read(1), b"a")
    self.assertEqual(stream.read(1), b"r")
    self.assertEqual(stream.read(1), b"b")
    self.assertEqual(stream.read(1), b"a")
    self.assertEqual(stream.read(1), b"z")
    self.assertEqual(stream.read(1), b"")

  def testMultiChunkReadWhole(self):
    stream = ioutil.Unchunk(iter([b"foo", b"bar", b"baz"]))
    self.assertEqual(stream.read(), b"foobarbaz")

  def testMultiChunkReadLarge(self):
    stream = ioutil.Unchunk(itertools.cycle([b"\x42" * 1021]))
    self.assertEqual(stream.read(16777259), b"\x42" * 16777259)


if __name__ == "__main__":
  absltest.main()
