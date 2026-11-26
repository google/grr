#!/usr/bin/env python
from absl.testing import absltest

from google.protobuf import wrappers_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import communicator


class CommunicatorTest(absltest.TestCase):

  def testPackUnpackMessageList_Empty(self):
    msgs = jobs_pb2.MessageList()

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)
    msgs_unpacked = communicator.UnpackMessageList(msgs_packed)

    self.assertEqual(msgs, msgs_unpacked)

  def testPackUnpackMessageList_Single(self):
    msgs = jobs_pb2.MessageList()

    msg = msgs.job.add()
    msg.request_id = 42
    msg.payload_any.Pack(wrappers_pb2.BytesValue(value=b"foobar"))

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)
    msgs_unpacked = communicator.UnpackMessageList(msgs_packed)

    self.assertEqual(msgs, msgs_unpacked)

  def testPackUnpackMessageList_Multiple(self):
    msgs = jobs_pb2.MessageList()

    msg_1 = msgs.job.add()
    msg_1.request_id = 1
    msg_1.payload_any.Pack(wrappers_pb2.BytesValue(value=b"foo"))

    msg_2 = msgs.job.add()
    msg_2.request_id = 1
    msg_2.payload_any.Pack(wrappers_pb2.BytesValue(value=b"bar"))

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)
    msgs_unpacked = communicator.UnpackMessageList(msgs_packed)

    self.assertEqual(msgs, msgs_unpacked)

  def testPackUnpackMessageList_CompressionWithinLimit(self):
    msgs = jobs_pb2.MessageList()

    msg = msgs.job.add()
    msg.request_id = 1
    msg.payload_any.Pack(wrappers_pb2.BytesValue(value=b"\x00" * 1024 * 1024))

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)
    msgs_unpacked = communicator.UnpackMessageList(msgs_packed)

    self.assertEqual(msgs, msgs_unpacked)

  def testPackUnpackMessageList_CompressionLargeUncompressed(self):
    msgs = jobs_pb2.MessageList()

    msg = msgs.job.add()
    msg.payload_any.Pack(
        wrappers_pb2.BytesValue(value=b"\x00" * (24 * 1024 * 1024)),
    )

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)

    # A message full of zeros should compress extremely well to something less
    # than 1 MiB.
    self.assertLess(len(msgs_packed.SerializeToString()), 1 * 1024 * 1024)

    # ... and so unpacking it should fail.
    with self.assertRaises(communicator.UnpackError) as context:
      communicator.UnpackMessageList(msgs_packed)

    error = context.exception
    self.assertIn("Uncompressed message size limit reached", str(error))

  def testPackUnpackMessageList_CompressionEmpty(self):
    msgs = jobs_pb2.MessageList()

    msg = msgs.job.add()
    msg.payload_any.Pack(wrappers_pb2.BytesValue(value=b"\x00" * 64 * 1024))

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)

    msgs_packed.message_list = b""

    with self.assertRaises(communicator.UnpackError) as context:
      communicator.UnpackMessageList(msgs_packed)

    self.assertEqual("Incomplete message list", str(context.exception))

  def testPackUnpackMessageList_CompressionTruncated(self):
    msgs = jobs_pb2.MessageList()

    msg = msgs.job.add()
    msg.payload_any.Pack(wrappers_pb2.BytesValue(value=b"\x00" * 64 * 1024))

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)

    msgs_packed.message_list = msgs_packed.message_list[:-2]

    with self.assertRaises(communicator.UnpackError) as context:
      communicator.UnpackMessageList(msgs_packed)

    self.assertEqual("Incomplete message list", str(context.exception))

  def testPackUnpackMessageList_CompressionCorrupted(self):
    msgs = jobs_pb2.MessageList()

    msg = msgs.job.add()
    msg.payload_any.Pack(wrappers_pb2.BytesValue(value=b"\x00" * 64 * 1024))

    msgs_packed = jobs_pb2.PackedMessageList()
    communicator.PackMessageList(msgs, msgs_packed)

    msgs_packed.message_list = b"I AM NOT A VALID ZCOMPRESSED BYTE SEQUENCE"

    with self.assertRaises(communicator.UnpackError) as context:
      communicator.UnpackMessageList(msgs_packed)

    self.assertEqual("Failed to decompress", str(context.exception))


if __name__ == "__main__":
  absltest.main()
