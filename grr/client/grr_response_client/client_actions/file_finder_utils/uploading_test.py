#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import hashlib
import io
from unittest import mock
import zlib

from absl.testing import absltest

from grr_response_client.client_actions.file_finder_utils import uploading
from grr_response_core.lib.util import temp


class UploaderTest(absltest.TestCase):

  def testEmpty(self):
    action = FakeAction()
    uploader = uploading.TransferStoreUploader(action, chunk_size=3)

    with temp.AutoTempFilePath() as temp_filepath:
      blobdesc = uploader.UploadFilePath(temp_filepath)

      self.assertEqual(action.charged_bytes, 0)
      self.assertEmpty(action.messages)

      self.assertEmpty(blobdesc.chunks)
      self.assertEqual(blobdesc.chunk_size, 3)

  def testSingleChunk(self):
    action = FakeAction()
    uploader = uploading.TransferStoreUploader(action, chunk_size=6)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, "wb") as temp_file:
        temp_file.write(b"foobar")

      blobdesc = uploader.UploadFilePath(temp_filepath)

      self.assertEqual(action.charged_bytes, 6)
      self.assertLen(action.messages, 1)
      self.assertEqual(action.messages[0].item.data, zlib.compress(b"foobar"))

      self.assertLen(blobdesc.chunks, 1)
      self.assertEqual(blobdesc.chunk_size, 6)
      self.assertEqual(blobdesc.chunks[0].offset, 0)
      self.assertEqual(blobdesc.chunks[0].length, 6)
      self.assertEqual(blobdesc.chunks[0].digest, Sha256(b"foobar"))

  def testManyChunks(self):
    action = FakeAction()
    uploader = uploading.TransferStoreUploader(action, chunk_size=3)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, "wb") as temp_file:
        temp_file.write(b"1234567890")

      blobdesc = uploader.UploadFilePath(temp_filepath)

      self.assertEqual(action.charged_bytes, 10)
      self.assertLen(action.messages, 4)
      self.assertEqual(action.messages[0].item.data, zlib.compress(b"123"))
      self.assertEqual(action.messages[1].item.data, zlib.compress(b"456"))
      self.assertEqual(action.messages[2].item.data, zlib.compress(b"789"))
      self.assertEqual(action.messages[3].item.data, zlib.compress(b"0"))

      self.assertLen(blobdesc.chunks, 4)
      self.assertEqual(blobdesc.chunk_size, 3)
      self.assertEqual(blobdesc.chunks[0].offset, 0)
      self.assertEqual(blobdesc.chunks[0].length, 3)
      self.assertEqual(blobdesc.chunks[0].digest, Sha256(b"123"))
      self.assertEqual(blobdesc.chunks[1].offset, 3)
      self.assertEqual(blobdesc.chunks[1].length, 3)
      self.assertEqual(blobdesc.chunks[1].digest, Sha256(b"456"))
      self.assertEqual(blobdesc.chunks[2].offset, 6)
      self.assertEqual(blobdesc.chunks[2].length, 3)
      self.assertEqual(blobdesc.chunks[2].digest, Sha256(b"789"))
      self.assertEqual(blobdesc.chunks[3].offset, 9)
      self.assertEqual(blobdesc.chunks[3].length, 1)
      self.assertEqual(blobdesc.chunks[3].digest, Sha256(b"0"))

  def testLimitedAmount(self):
    action = FakeAction()
    uploader = uploading.TransferStoreUploader(action, chunk_size=3)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, "wb") as temp_file:
        temp_file.write(b"1234567890")

      blobdesc = uploader.UploadFilePath(temp_filepath, amount=5)

      self.assertEqual(action.charged_bytes, 5)
      self.assertLen(action.messages, 2)
      self.assertEqual(action.messages[0].item.data, zlib.compress(b"123"))
      self.assertEqual(action.messages[1].item.data, zlib.compress(b"45"))

      self.assertLen(blobdesc.chunks, 2)
      self.assertEqual(blobdesc.chunk_size, 3)
      self.assertEqual(blobdesc.chunks[0].offset, 0)
      self.assertEqual(blobdesc.chunks[0].length, 3)
      self.assertEqual(blobdesc.chunks[0].digest, Sha256(b"123"))
      self.assertEqual(blobdesc.chunks[1].offset, 3)
      self.assertEqual(blobdesc.chunks[1].length, 2)
      self.assertEqual(blobdesc.chunks[1].digest, Sha256(b"45"))

  def testCustomOffset(self):
    action = FakeAction()
    uploader = uploading.TransferStoreUploader(action, chunk_size=2)

    with temp.AutoTempFilePath() as temp_filepath:
      with io.open(temp_filepath, "wb") as temp_file:
        temp_file.write(b"0123456")

      blobdesc = uploader.UploadFilePath(temp_filepath, offset=2)

      self.assertEqual(action.charged_bytes, 5)
      self.assertLen(action.messages, 3)
      self.assertEqual(action.messages[0].item.data, zlib.compress(b"23"))
      self.assertEqual(action.messages[1].item.data, zlib.compress(b"45"))
      self.assertEqual(action.messages[2].item.data, zlib.compress(b"6"))

      self.assertLen(blobdesc.chunks, 3)
      self.assertEqual(blobdesc.chunk_size, 2)
      self.assertEqual(blobdesc.chunks[0].offset, 2)
      self.assertEqual(blobdesc.chunks[0].length, 2)
      self.assertEqual(blobdesc.chunks[0].digest, Sha256(b"23"))
      self.assertEqual(blobdesc.chunks[1].offset, 4)
      self.assertEqual(blobdesc.chunks[1].length, 2)
      self.assertEqual(blobdesc.chunks[1].digest, Sha256(b"45"))
      self.assertEqual(blobdesc.chunks[2].offset, 6)
      self.assertEqual(blobdesc.chunks[2].length, 1)
      self.assertEqual(blobdesc.chunks[2].digest, Sha256(b"6"))

  def testIncorrectFile(self):
    action = FakeAction()
    uploader = uploading.TransferStoreUploader(action, chunk_size=10)

    with self.assertRaises(IOError):
      uploader.UploadFilePath("/foo/bar/baz")


def Sha256(data):
  return hashlib.sha256(data).digest()


class FakeAction(mock.MagicMock):

  Message = collections.namedtuple("Message", ("item", "session_id"))  # pylint: disable=invalid-name

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.charged_bytes = 0
    self.messages = []

  def ChargeBytesToSession(self, amount):
    self.charged_bytes += amount

  def SendReply(self, item, session_id):
    self.messages.append(self.Message(item=item, session_id=session_id))


if __name__ == "__main__":
  absltest.main()
