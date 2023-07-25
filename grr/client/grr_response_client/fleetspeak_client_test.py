#!/usr/bin/env python
import logging
from unittest import mock
import zlib

from absl import app
from absl.testing import absltest

from grr_response_client import comms
from grr_response_client import fleetspeak_client
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.test_lib import test_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from fleetspeak.client_connector import connector as fs_client


def _DecompressMessageList(
    packed_message_list: rdf_flows.PackedMessageList,
) -> rdf_flows.MessageList:
  """Decompress the message data from packed_message_list."""
  compression = packed_message_list.compression
  if compression == rdf_flows.PackedMessageList.CompressionType.UNCOMPRESSED:
    data = packed_message_list.message_list

  elif compression == rdf_flows.PackedMessageList.CompressionType.ZCOMPRESSION:
    try:
      data = zlib.decompress(packed_message_list.message_list)
    except zlib.error as e:
      raise RuntimeError("Failed to decompress: %s" % e) from e
  else:
    raise RuntimeError("Compression scheme not supported")

  try:
    result = rdf_flows.MessageList.FromSerializedBytes(data)
  except rdfvalue.DecodeError as e:
    raise RuntimeError("RDFValue parsing failed.") from e

  return result


class FleetspeakClientTest(absltest.TestCase):

  @mock.patch.object(fs_client, "FleetspeakConnection")
  @mock.patch.object(comms, "GRRClientWorker")
  @mock.patch.object(fleetspeak_client, "_MAX_ANNOTATIONS_BYTES", 500)
  def testSendMessagesWithAnnotations(self, mock_worker_class, mock_conn_class):
    # We stub out the worker class since it starts threads in its
    # __init__ method.
    del mock_worker_class  # Unused

    mock_conn = mock.Mock()
    mock_conn.Send.return_value = 123
    mock_conn_class.return_value = mock_conn
    client_id = "C.0123456789abcdef"
    flow_id = "01234567"
    client = fleetspeak_client.GRRFleetspeakClient()
    grr_messages = []
    expected_annotations = fs_common_pb2.Annotations()

    # 500 bytes translates to ~19 annotations.
    while expected_annotations.ByteSize() < 500:
      grr_message = rdf_flows.GrrMessage(
          session_id="%s/%s" % (client_id, flow_id),
          name="TestClientAction",
          request_id=2,
          response_id=len(grr_messages) + 1)
      annotation = expected_annotations.entries.add()
      annotation.key = fleetspeak_client._DATA_IDS_ANNOTATION_KEY
      annotation.value = "%s:2:%d" % (flow_id, len(grr_messages) + 1)
      grr_messages.append(grr_message)
      client._sender_queue.put(grr_message)

    # Add an extra GrrMessage whose annotation will not be captured.
    extra_message = rdf_flows.GrrMessage(
        session_id="%s/%s" % (client_id, flow_id),
        name="TestClientAction",
        request_id=3,
        response_id=1)
    grr_messages.append(extra_message)
    client._sender_queue.put(extra_message)

    self.assertLess(
        len(grr_messages), fleetspeak_client._MAX_MSG_LIST_MSG_COUNT)
    self.assertLess(
        sum(len(x.SerializeToBytes()) for x in grr_messages),
        fleetspeak_client._MAX_MSG_LIST_BYTES)

    client._SendOp()

    mock_conn.Send.assert_called_once()
    send_args, _ = mock_conn.Send.call_args
    fs_message = send_args[0]
    packed_message_list = rdf_flows.PackedMessageList.protobuf()
    fs_message.data.Unpack(packed_message_list)
    message_list = _DecompressMessageList(
        rdf_flows.PackedMessageList.FromSerializedBytes(
            packed_message_list.SerializeToString()
        )
    )
    self.assertListEqual(list(message_list.job), grr_messages)
    self.assertEqual(fs_message.annotations, expected_annotations)

  @mock.patch.object(fs_client, "FleetspeakConnection")
  @mock.patch.object(comms, "GRRClientWorker")
  def testBrokenFSConnection(self, mock_worker_class, mock_con_class):
    # We stub out the worker class since it starts threads in its
    # __init__ method.

    del mock_worker_class  # Unused

    mock_conn = mock.Mock()
    mock_conn.Recv.side_effect = IOError("Broken FS Connection")
    mock_con_class.return_value = mock_conn

    with mock.patch.object(logging, "critical") as l:
      client = fleetspeak_client.GRRFleetspeakClient()
      try:
        client._RunInLoop(client._ReceiveOp)
      except fleetspeak_client.BrokenFSConnectionError:
        pass

      self.assertEqual(l.call_count, 1)
      self.assertIn("Broken local Fleetspeak connection", l.call_args[0][0])


if __name__ == "__main__":
  app.run(test_lib.main)
