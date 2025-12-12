#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import buffer_reference
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class BufferReferenceToExportedMatchConverterTest(
    export_test_lib.ExportTestBase
):

  def testBasicConversion(self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS
    )
    buffer = rdf_client.BufferReference(
        length=123,
        offset=456,
        data=b"somedata",
        pathspec=pathspec,
    )

    converter = buffer_reference.BufferReferenceToExportedMatchConverter()
    results = list(converter.Convert(self.metadata, buffer))

    self.assertLen(results, 1)
    self.assertEqual(results[0].length, 123)
    self.assertEqual(results[0].offset, 456)
    self.assertEqual(results[0].data, b"somedata")


class BufferReferenceToExportedMatchConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testBasicConversion(self):
    buffer = jobs_pb2.BufferReference(
        length=123,
        offset=456,
        data=b"somedata",
        pathspec=jobs_pb2.PathSpec(
            path="/some/path", pathtype=jobs_pb2.PathSpec.PathType.OS
        ),
    )

    converter = buffer_reference.BufferReferenceToExportedMatchConverterProto()
    results = list(converter.Convert(self.metadata_proto, buffer))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedMatch)
    self.assertEqual(results[0].length, 123)
    self.assertEqual(results[0].offset, 456)
    self.assertEqual(results[0].data, b"somedata")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
