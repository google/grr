#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server.sinks import test_lib
from grr_response_proto import rrg_pb2


class FakeSinkTest(absltest.TestCase):

  def testParcelsEmptyByDefault(self):
    sink = test_lib.FakeSink()
    self.assertEmpty(sink.Parcels("C.0123456789ABCDEF"))

  def testParcelsSingleClient(self):
    client_id = "C.0123456789ABCDEF"
    sink = test_lib.FakeSink()

    parcel = rrg_pb2.Parcel()
    parcel.payload.value = b"FOO"
    sink.Accept(client_id, parcel)

    parcel = rrg_pb2.Parcel()
    parcel.payload.value = b"BAR"
    sink.Accept(client_id, parcel)

    parcels = sink.Parcels(client_id)
    self.assertLen(parcels, 2)
    self.assertEqual(parcels[0].payload.value, b"FOO")
    self.assertEqual(parcels[1].payload.value, b"BAR")

  def testParcelsMultipleClients(self):
    client_id_1 = "C.0123456789ABCDEF"
    client_id_2 = "C.ABCDEF0123456789"
    sink = test_lib.FakeSink()

    parcel = rrg_pb2.Parcel()
    parcel.payload.value = b"FOO"
    sink.Accept(client_id_1, parcel)

    parcel = rrg_pb2.Parcel()
    parcel.payload.value = b"BAR"
    sink.Accept(client_id_2, parcel)

    parcels_1 = sink.Parcels(client_id_1)
    self.assertLen(parcels_1, 1)
    self.assertEqual(parcels_1[0].payload.value, b"FOO")

    parcels_2 = sink.Parcels(client_id_2)
    self.assertLen(parcels_2, 1)
    self.assertEqual(parcels_2[0].payload.value, b"BAR")


if __name__ == "__main__":
  absltest.main()
