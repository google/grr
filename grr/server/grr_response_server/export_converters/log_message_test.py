#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import log_message


class LogMessageToExportedStringConverterTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testLogMessageConverter(self):
    log_message_pb = jobs_pb2.LogMessage(data="what it sounds like")

    converter = log_message.LogMessageToExportedStringConverter()
    results = list(converter.Convert(self.metadata_proto, log_message_pb))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedString)
    self.assertEqual(results[0].data, "what it sounds like")
    self.assertEqual(results[0].metadata, self.metadata_proto)


if __name__ == "__main__":
  absltest.main()
