#!/usr/bin/env python
from unittest import mock

from absl.testing import absltest

from grr_response_server import sinks
from grr_response_server.sinks import test_lib
from grr_response_proto import rrg_pb2


class AcceptTest(absltest.TestCase):

  def testUnknownSink(self):
    with mock.patch.object(sinks, "REGISTRY", {}):
      parcel = rrg_pb2.Parcel()
      parcel.sink = 1337

      with self.assertRaises(sinks.UnknownSinkError) as context:
        sinks.Accept("C.012345679ABCDEF", parcel)

      self.assertEqual(context.exception.sink, 1337)

  def testFakeSinks(self):
    client_id = "C.012345679ABCDEF"

    startup_sink = test_lib.FakeSink()
    blob_sink = test_lib.FakeSink()

    fake_registry = {
        rrg_pb2.Sink.STARTUP: startup_sink,
        rrg_pb2.Sink.BLOB: blob_sink,
    }

    with mock.patch.object(sinks, "REGISTRY", fake_registry):
      parcel = rrg_pb2.Parcel()
      parcel.sink = rrg_pb2.Sink.STARTUP
      parcel.payload.value = b"STARTUP0"
      sinks.Accept(client_id, parcel)

      parcel = rrg_pb2.Parcel()
      parcel.sink = rrg_pb2.Sink.BLOB
      parcel.payload.value = b"BLOB0"
      sinks.Accept(client_id, parcel)

      parcel = rrg_pb2.Parcel()
      parcel.sink = rrg_pb2.Sink.BLOB
      parcel.payload.value = b"BLOB1"
      sinks.Accept(client_id, parcel)

      parcel = rrg_pb2.Parcel()
      parcel.sink = rrg_pb2.Sink.STARTUP
      parcel.payload.value = b"STARTUP1"
      sinks.Accept(client_id, parcel)

    startups = startup_sink.Parcels(client_id)
    self.assertLen(startups, 2)
    self.assertEqual(startups[0].payload.value, b"STARTUP0")
    self.assertEqual(startups[1].payload.value, b"STARTUP1")

    blobs = blob_sink.Parcels(client_id)
    self.assertLen(blobs, 2)
    self.assertEqual(blobs[0].payload.value, b"BLOB0")
    self.assertEqual(blobs[1].payload.value, b"BLOB1")


if __name__ == "__main__":
  absltest.main()
