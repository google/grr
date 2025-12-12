#!/usr/bin/env python
from absl.testing import absltest

from google.protobuf import wrappers_pb2
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import export_pb2
from grr_response_server.export_converters import proto_wrappers


class StringValueToExportedStringConverterTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testStringValueConverter(self):
    string_value = wrappers_pb2.StringValue(value="foobar")

    converter = proto_wrappers.StringValueToExportedStringConverter()
    results = list(converter.Convert(self.metadata_proto, string_value))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedString)
    self.assertEqual(results[0].data, "foobar")
    self.assertEqual(results[0].metadata, self.metadata_proto)


class BytesValueToExportedBytesConverterTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testBytesValueConverter(self):
    bytes_value = wrappers_pb2.BytesValue(value=b"foobar")

    converter = proto_wrappers.BytesValueToExportedBytesConverter()
    results = list(converter.Convert(self.metadata_proto, bytes_value))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedBytes)
    self.assertEqual(results[0].data, b"foobar")
    self.assertEqual(results[0].length, 6)
    self.assertEqual(results[0].metadata, self.metadata_proto)


if __name__ == "__main__":
  absltest.main()
