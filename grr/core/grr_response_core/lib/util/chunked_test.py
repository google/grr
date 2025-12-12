#!/usr/bin/env python
import io

from absl.testing import absltest

from grr_response_core.lib.util import chunked


class ReadWriteTest(absltest.TestCase):

  def testSingleChunk(self):
    buf = io.BytesIO()
    chunked.Write(buf, b"foo")

    buf.seek(0, io.SEEK_SET)
    self.assertEqual(chunked.Read(buf), b"foo")
    self.assertIsNone(chunked.Read(buf))

  def testMultipleChunks(self):
    buf = io.BytesIO()
    chunked.Write(buf, b"foo")
    chunked.Write(buf, b"bar")
    chunked.Write(buf, b"baz")

    buf.seek(0, io.SEEK_SET)
    self.assertEqual(chunked.Read(buf), b"foo")
    self.assertEqual(chunked.Read(buf), b"bar")
    self.assertEqual(chunked.Read(buf), b"baz")
    self.assertIsNone(chunked.Read(buf))

  def testSingleEmptyChunk(self):
    buf = io.BytesIO()
    chunked.Write(buf, b"")

    buf.seek(0, io.SEEK_SET)
    self.assertEqual(chunked.Read(buf), b"")
    self.assertIsNone(chunked.Read(buf))

  def testMultipleEmptyChunks(self):
    buf = io.BytesIO()
    chunked.Write(buf, b"")
    chunked.Write(buf, b"")
    chunked.Write(buf, b"")

    buf.seek(0, io.SEEK_SET)
    self.assertEqual(chunked.Read(buf), b"")
    self.assertEqual(chunked.Read(buf), b"")
    self.assertEqual(chunked.Read(buf), b"")
    self.assertIsNone(chunked.Read(buf))


class ReadTest(absltest.TestCase):

  def testEmptyBuffer(self):
    buf = io.BytesIO()
    self.assertIsNone(chunked.Read(buf))

  def testIncorrectSizeTag(self):
    buf = io.BytesIO(b"\x00\xff\xee")
    with self.assertRaises(chunked.IncorrectSizeTagError):
      chunked.Read(buf)

  def testMalformedInpuWithMaxChunkSizeSet(self):
    buf = io.BytesIO(b"\xff" * 1024)

    with self.assertRaises(chunked.ChunkSizeTooBigError):
      chunked.Read(buf, max_chunk_size=1024)

  def testMalformedInputWithoutMaxChunkSizeSet(self):
    buf1 = io.BytesIO()
    chunked.Write(buf1, b"foobarbaz")

    buf2 = io.BytesIO(buf1.getvalue()[:-2])
    with self.assertRaises(chunked.ChunkTruncatedError):
      chunked.Read(buf2)


class ReadAllTest(absltest.TestCase):

  def testEmpty(self):
    buf = io.BytesIO()
    self.assertEmpty(list(chunked.ReadAll(buf)))

  def testSingle(self):
    buf = io.BytesIO()
    chunked.Write(buf, b"foo")

    buf.seek(0, io.SEEK_SET)
    self.assertEqual(list(chunked.ReadAll(buf)), [b"foo"])

  def testMultiple(self):
    buf = io.BytesIO()
    chunked.Write(buf, b"foo")
    chunked.Write(buf, b"bar")
    chunked.Write(buf, b"quux")

    buf.seek(0, io.SEEK_SET)
    self.assertEqual(list(chunked.ReadAll(buf)), [b"foo", b"bar", b"quux"])


class EncodeTest(absltest.TestCase):

  def testEmpty(self):
    chunks = [b""]

    buf = io.BytesIO(b"".join(map(chunked.Encode, chunks)))
    self.assertEqual(chunked.Read(buf), b"")
    self.assertIsNone(chunked.Read(buf))

  def testSingle(self):
    chunks = [b"foo"]

    buf = io.BytesIO(b"".join(map(chunked.Encode, chunks)))
    self.assertEqual(chunked.Read(buf), b"foo")
    self.assertIsNone(chunked.Read(buf))

  def testMultiple(self):
    chunks = [b"foo", b"bar", b"baz"]

    buf = io.BytesIO(b"".join(map(chunked.Encode, chunks)))
    self.assertEqual(chunked.Read(buf), b"foo")
    self.assertEqual(chunked.Read(buf), b"bar")
    self.assertEqual(chunked.Read(buf), b"baz")
    self.assertIsNone(chunked.Read(buf))


if __name__ == "__main__":
  absltest.main()
