#!/usr/bin/env python
"""Tests for export converters."""

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_proto import export_pb2
from grr_response_proto import osquery_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import osquery
from grr.test_lib import test_lib


class OsqueryExportConverterTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.converter = osquery.OsqueryExportConverter()
    self.metadata = base.ExportedMetadata(client_urn="C.48515162342ABCDE")

  def _Convert(self, table):
    return list(self.converter.Convert(self.metadata, table))

  def testNoRows(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT bar, baz FROM foo;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="baz"))

    self.assertEqual(self._Convert(table), [])

  def testSomeRows(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT foo, bar, quux FROM norf;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="quux"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["thud", "🐺", "42"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["plugh", "🦊", "108"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["blargh", "🦍", "1337"]))

    results = self._Convert(table)
    self.assertLen(results, 3)
    self.assertEqual(results[0].metadata, self.metadata)
    self.assertEqual(results[0].foo, "thud")
    self.assertEqual(results[0].bar, "🐺")
    self.assertEqual(results[0].quux, "42")
    self.assertEqual(results[1].metadata, self.metadata)
    self.assertEqual(results[1].foo, "plugh")
    self.assertEqual(results[1].bar, "🦊")
    self.assertEqual(results[1].quux, "108")
    self.assertEqual(results[2].metadata, self.metadata)
    self.assertEqual(results[2].foo, "blargh")
    self.assertEqual(results[2].bar, "🦍")
    self.assertEqual(results[2].quux, "1337")

  def testMetadataColumn(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT metadata FROM foo;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="metadata"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["bar"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["baz"]))

    results = self._Convert(table)
    self.assertLen(results, 2)
    self.assertEqual(results[0].metadata, self.metadata)
    self.assertEqual(results[0].__metadata__, "bar")
    self.assertEqual(results[1].metadata, self.metadata)
    self.assertEqual(results[1].__metadata__, "baz")

  def testQueryMetadata(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "   SELECT foo FROM quux;          "
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["norf"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["thud"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["blargh"]))

    results = self._Convert(table)
    self.assertLen(results, 3)
    self.assertEqual(results[0].__query__, "SELECT foo FROM quux;")
    self.assertEqual(results[0].foo, "norf")
    self.assertEqual(results[1].__query__, "SELECT foo FROM quux;")
    self.assertEqual(results[1].foo, "thud")
    self.assertEqual(results[2].__query__, "SELECT foo FROM quux;")
    self.assertEqual(results[2].foo, "blargh")


class OsqueryTableExportConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testNoRows(self):
    table = osquery_pb2.OsqueryTable(
        query="SELECT bar, baz FROM foo;",
        header=osquery_pb2.OsqueryHeader(
            columns=[
                osquery_pb2.OsqueryColumn(name="bar"),
                osquery_pb2.OsqueryColumn(name="baz"),
            ]
        ),
    )

    converter = osquery.OsqueryTableExportConverterProto()
    results = list(converter.Convert(self.metadata_proto, table))

    self.assertEmpty(results)

  def testSomeRows(self):
    table = osquery_pb2.OsqueryTable(
        query="SELECT foo, bar, quux FROM norf;",
        header=osquery_pb2.OsqueryHeader(
            columns=[
                osquery_pb2.OsqueryColumn(name="foo"),
                osquery_pb2.OsqueryColumn(name="bar"),
                osquery_pb2.OsqueryColumn(name="quux"),
            ]
        ),
        rows=[
            osquery_pb2.OsqueryRow(values=["thud", "🐺", "42"]),
            osquery_pb2.OsqueryRow(values=["plugh", "🦊", "108"]),
            osquery_pb2.OsqueryRow(values=["blargh", "🦍", "1337"]),
        ],
    )

    converter = osquery.OsqueryTableExportConverterProto()
    results = list(converter.Convert(self.metadata_proto, table))

    self.assertLen(results, 9)
    for result in results:
      self.assertEqual(result.metadata, self.metadata_proto)
      self.assertEqual(result.query, "SELECT foo, bar, quux FROM norf;")

    self.assertEqual(results[0].row_number, 0)
    self.assertEqual(results[0].column_name, "foo")
    self.assertEqual(results[0].value, "thud")
    self.assertEqual(results[1].row_number, 0)
    self.assertEqual(results[1].column_name, "bar")
    self.assertEqual(results[1].value, "🐺")
    self.assertEqual(results[2].row_number, 0)
    self.assertEqual(results[2].column_name, "quux")
    self.assertEqual(results[2].value, "42")

    self.assertEqual(results[3].row_number, 1)
    self.assertEqual(results[3].column_name, "foo")
    self.assertEqual(results[3].value, "plugh")
    self.assertEqual(results[4].row_number, 1)
    self.assertEqual(results[4].column_name, "bar")
    self.assertEqual(results[4].value, "🦊")
    self.assertEqual(results[5].row_number, 1)
    self.assertEqual(results[5].column_name, "quux")
    self.assertEqual(results[5].value, "108")

    self.assertEqual(results[6].row_number, 2)
    self.assertEqual(results[6].column_name, "foo")
    self.assertEqual(results[6].value, "blargh")
    self.assertEqual(results[7].row_number, 2)
    self.assertEqual(results[7].column_name, "bar")
    self.assertEqual(results[7].value, "🦍")
    self.assertEqual(results[8].row_number, 2)
    self.assertEqual(results[8].column_name, "quux")
    self.assertEqual(results[8].value, "1337")


class OsqueryResultExportConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testNoRows(self):
    table = osquery_pb2.OsqueryTable(
        query="SELECT bar, baz FROM foo;",
        header=osquery_pb2.OsqueryHeader(
            columns=[
                osquery_pb2.OsqueryColumn(name="bar"),
                osquery_pb2.OsqueryColumn(name="baz"),
            ]
        ),
    )
    result = osquery_pb2.OsqueryResult(table=table)

    converter = osquery.OsqueryResultExportConverterProto()
    results = list(converter.Convert(self.metadata_proto, result))

    self.assertEmpty(results)

  def testSomeRows(self):
    table = osquery_pb2.OsqueryTable(
        query="SELECT foo, bar, quux FROM norf;",
        header=osquery_pb2.OsqueryHeader(
            columns=[
                osquery_pb2.OsqueryColumn(name="foo"),
                osquery_pb2.OsqueryColumn(name="bar"),
                osquery_pb2.OsqueryColumn(name="quux"),
            ]
        ),
        rows=[
            osquery_pb2.OsqueryRow(values=["thud", "🐺", "42"]),
            osquery_pb2.OsqueryRow(values=["plugh", "🦊", "108"]),
            osquery_pb2.OsqueryRow(values=["blargh", "🦍", "1337"]),
        ],
    )
    result = osquery_pb2.OsqueryResult(table=table)

    converter = osquery.OsqueryResultExportConverterProto()
    results = list(converter.Convert(self.metadata_proto, result))

    self.assertLen(results, 9)
    for result in results:
      self.assertEqual(result.metadata, self.metadata_proto)
      self.assertEqual(result.query, "SELECT foo, bar, quux FROM norf;")

    self.assertEqual(results[0].row_number, 0)
    self.assertEqual(results[0].column_name, "foo")
    self.assertEqual(results[0].value, "thud")
    self.assertEqual(results[1].row_number, 0)
    self.assertEqual(results[1].column_name, "bar")
    self.assertEqual(results[1].value, "🐺")
    self.assertEqual(results[2].row_number, 0)
    self.assertEqual(results[2].column_name, "quux")
    self.assertEqual(results[2].value, "42")

    self.assertEqual(results[3].row_number, 1)
    self.assertEqual(results[3].column_name, "foo")
    self.assertEqual(results[3].value, "plugh")
    self.assertEqual(results[4].row_number, 1)
    self.assertEqual(results[4].column_name, "bar")
    self.assertEqual(results[4].value, "🦊")
    self.assertEqual(results[5].row_number, 1)
    self.assertEqual(results[5].column_name, "quux")
    self.assertEqual(results[5].value, "108")

    self.assertEqual(results[6].row_number, 2)
    self.assertEqual(results[6].column_name, "foo")
    self.assertEqual(results[6].value, "blargh")
    self.assertEqual(results[7].row_number, 2)
    self.assertEqual(results[7].column_name, "bar")
    self.assertEqual(results[7].value, "🦍")
    self.assertEqual(results[8].row_number, 2)
    self.assertEqual(results[8].column_name, "quux")
    self.assertEqual(results[8].value, "1337")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
