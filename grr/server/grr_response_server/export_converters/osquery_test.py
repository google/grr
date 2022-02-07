#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for export converters."""

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
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


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
