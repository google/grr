#!/usr/bin/env python
import io
import struct

from absl.testing import absltest

from google.protobuf import empty_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import type_pb2
from google.protobuf import wrappers_pb2
from grr_api_client import utils


class MessageToFlatDictTest(absltest.TestCase):

  def testEmpty(self):
    dct = utils.MessageToFlatDict(empty_pb2.Empty(), lambda _, value: value)
    self.assertEmpty(dct)

  def testSingleField(self):
    string = wrappers_pb2.StringValue()
    string.value = "foo"

    dct = utils.MessageToFlatDict(string, lambda _, value: value)
    self.assertEqual(dct, {"value": "foo"})

  def testMultipleFields(self):
    timestamp = timestamp_pb2.Timestamp()
    timestamp.seconds = 1337
    timestamp.nanos = 42

    dct = utils.MessageToFlatDict(timestamp, lambda _, value: value)
    self.assertEqual(dct, {"seconds": 1337, "nanos": 42})

  def testNestedMessages(self):
    option = type_pb2.Option()
    option.name = "foo"
    option.value.type_url = "bar.baz.quux"
    option.value.value = b"quux"

    dct = utils.MessageToFlatDict(option, lambda _, value: value)
    self.assertEqual(
        dct,
        {
            "name": "foo",
            "value.type_url": "bar.baz.quux",
            "value.value": b"quux",
        },
    )

  def testTransform(self):
    i32 = wrappers_pb2.Int32Value()
    i32.value = 1337

    dct = utils.MessageToFlatDict(i32, lambda _, value: value * 2)
    self.assertEqual(dct, {"value": 1337 * 2})


class GetCrowdstrikeDecodedBlobTest(absltest.TestCase):

  def _CrowdstrikeEncode(self, data) -> bytes:
    buf = io.BytesIO()
    buf.write(b"CSQD")
    buf.write(struct.pack("<Q", len(data)))
    buf.write(utils.Xor(data, 0x7E))
    return buf.getvalue()

  def testDecodeSingleChunk(self):
    content = b"foobarbaz"
    iterator_content = iter((self._CrowdstrikeEncode(content),))
    encoded_content = utils.BinaryChunkIterator(iterator_content)

    decoded = encoded_content.DecodeCrowdStrikeQuarantineEncoding()
    self.assertIsInstance(decoded, utils.BinaryChunkIterator)
    self.assertEqual(b"".join(decoded), content)

  def testDecode_RaisesIfCrowdstrikeIdentifierBytesMissing(self):
    content = b"foobarbazbang"
    iterator_content = iter((content,))
    encoded_content = utils.BinaryChunkIterator(iterator_content)

    with self.assertRaises(ValueError):
      list(encoded_content.DecodeCrowdStrikeQuarantineEncoding())

  def testDecodeSeveralChunks(self):
    content = b"ABC" * 1024
    encoded_content = self._CrowdstrikeEncode(content)
    first_chunk = encoded_content[0:1024]
    second_chunk = encoded_content[1024:2048]
    third_chunk = encoded_content[2048:]
    encoded_content = utils.BinaryChunkIterator(
        iter((first_chunk, second_chunk, third_chunk))
    )

    decoded = encoded_content.DecodeCrowdStrikeQuarantineEncoding()
    self.assertEqual(b"".join(decoded), content)


if __name__ == "__main__":
  absltest.main()
