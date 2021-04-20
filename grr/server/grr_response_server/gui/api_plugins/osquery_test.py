#!/usr/bin/env python
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_server.gui.api_plugins import osquery as api_osquery


class UtilsTest(absltest.TestCase):
  """Test for osquery utils."""

  def testListToCSVBytes(self):
    output_bytes = api_osquery._LineToCsvBytes(["a", "b", "c", "d"])
    output_text = output_bytes.decode("utf-8")

    self.assertEqual("a,b,c,d\r\n", output_text)

  def testSomeTextToCsvBytes(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="B"))

    table.rows.append(rdf_osquery.OsqueryRow(values=["1-A", "1-B"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["2-A", "2-B"]))

    result = rdf_osquery.OsqueryResult()
    result.table = table

    output_bytes = api_osquery._ParseToCsvBytes([result])
    output_text = list(map(lambda b: b.decode("utf-8"), output_bytes))

    self.assertListEqual(["A,B\r\n", "1-A,1-B\r\n", "2-A,2-B\r\n"], output_text)

  def testTextWithCommasToCsvBytes(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="c,o,l,u,m,n"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["c,e,l,l"]))

    result = rdf_osquery.OsqueryResult()
    result.table = table

    output_bytes = api_osquery._ParseToCsvBytes([result])
    output_text = list(map(lambda b: b.decode("utf-8"), output_bytes))

    self.assertListEqual(["\"c,o,l,u,m,n\"\r\n", "\"c,e,l,l\"\r\n"],
                         output_text)


if __name__ == "__main__":
  absltest.main()
