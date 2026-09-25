#!/usr/bin/env python
"""Tests for client snapshot export converters."""

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import export_pb2
from grr_response_proto import objects_pb2
from grr_response_server.export_converters import client_snapshot
from grr.test_lib import test_lib


class ClientSnapshotToExportedClientConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testClientSnapshotToExportedClientConverter(self):
    unused_snapshot = objects_pb2.ClientSnapshot()

    converter = client_snapshot.ClientSnapshotToExportedClientConverterProto()
    results = list(converter.Convert(self.metadata_proto, unused_snapshot))

    self.assertLen(results, 1)
    self.assertEqual(results[0].metadata, self.metadata_proto)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
