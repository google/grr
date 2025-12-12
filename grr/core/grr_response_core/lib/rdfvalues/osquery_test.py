#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery


class OsqueryTableTest(absltest.TestCase):

  def testColumnEmpty(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="B"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="C"))

    self.assertEmpty(list(table.Column("A")))
    self.assertEmpty(list(table.Column("B")))
    self.assertEmpty(list(table.Column("C")))

  def testColumnValues(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="B"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="C"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["foo", "bar", "baz"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["quux", "norf", "thud"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["blarg", "shme", "ztesh"]))

    self.assertEqual(list(table.Column("A")), ["foo", "quux", "blarg"])
    self.assertEqual(list(table.Column("B")), ["bar", "norf", "shme"])
    self.assertEqual(list(table.Column("C")), ["baz", "thud", "ztesh"])

  def testColumnIncorrect(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="B"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="C"))

    with self.assertRaises(KeyError):
      list(table.Column("D"))


class OsqueryResultTest(absltest.TestCase):

  def testGetTableColumns(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="B"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="C"))

    result = rdf_osquery.OsqueryResult()
    result.table = table

    cols = list(result.GetTableColumns())
    self.assertEqual(["A", "B", "C"], cols)

  def testGetTableRows(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))

    table.rows.append(rdf_osquery.OsqueryRow(values=["cell1"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["cell2"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["cell3"]))

    result = rdf_osquery.OsqueryResult()
    result.table = table

    rows = list(result.GetTableRows())
    self.assertEqual([["cell1"], ["cell2"], ["cell3"]], rows)


if __name__ == "__main__":
  absltest.main()
