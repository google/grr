#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import gzip
import io
import os
import struct

from absl.testing import absltest

from grr_response_core.lib.util import gzchunked


class SerializeTest(absltest.TestCase):

  def testEmpty(self):
    serialized = list(gzchunked.Serialize(iter([])))
    self.assertEmpty(serialized)

  def testSingleEntry(self):
    data = [b"foo"]

    serialized = list(gzchunked.Serialize(iter(data), chunk_size=1024))
    self.assertLen(serialized, 1)

  def testMultipleSmallEntries(self):
    data = [b"foo", b"bar", b"baz", b"quux"]

    serialized = list(gzchunked.Serialize(iter(data), chunk_size=1024))
    self.assertLen(serialized, 1)

  def testMultipleBigEntries(self):
    data = [os.urandom(1024 * 1024) for _ in range(8)]

    serialized = list(gzchunked.Serialize(iter(data), chunk_size=(1024 * 1024)))
    self.assertGreater(len(serialized), 1)
    self.assertLessEqual(len(serialized), len(data))


class DeserializeTest(absltest.TestCase):

  def testIncorrectSize(self):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as filedesc:
      filedesc.write(struct.pack("!I", 42))

    with self.assertRaises(ValueError):
      list(gzchunked.Deserialize(iter([buf.getvalue()])))

  def testIncorrectData(self):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as filedesc:
      filedesc.write(struct.pack("!Q", 8))
      filedesc.write(b"quux")

    with self.assertRaises(ValueError):
      list(gzchunked.Deserialize(iter([buf.getvalue()])))

  def testEmpty(self):
    serialized = list(gzchunked.Serialize(iter([])))
    deserialized = list(gzchunked.Deserialize(iter(serialized)))

    self.assertEqual(deserialized, [])

  def testSingleEntry(self):
    data = [b"foo"]

    serialized = list(gzchunked.Serialize(iter(data)))
    deserialized = list(gzchunked.Deserialize(iter(serialized)))

    self.assertEqual(deserialized, data)

  def testMultipleEntries(self):
    data = [b"foo", b"bar", b"baz", b"quux", b"norf", b"thud"]

    serialized = list(gzchunked.Serialize(iter(data)))
    deserialized = list(gzchunked.Deserialize(iter(serialized)))

    self.assertEqual(deserialized, data)

  def testEmptyData(self):
    data = [b"", b"", b""]

    serialized = list(gzchunked.Serialize(iter(data)))
    deserialized = list(gzchunked.Deserialize(iter(serialized)))

    self.assertEqual(deserialized, data)

  def testNoChunks(self):
    deserialized = list(gzchunked.Deserialize(iter([])))
    self.assertEmpty(deserialized)

  def testMultipleChunks(self):
    data = [os.urandom(1024 * 1024) for _ in range(8)]

    serialized = list(gzchunked.Serialize(iter(data), chunk_size=(1024 * 1024)))
    self.assertGreater(len(serialized), 1)

    deserialized = list(gzchunked.Deserialize(iter(serialized)))
    self.assertEqual(deserialized, data)


if __name__ == "__main__":
  absltest.main()
