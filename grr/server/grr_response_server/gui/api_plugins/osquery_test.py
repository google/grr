#!/usr/bin/env python
# Lint as: python3
import unittest

from grr_response_server.gui.api_plugins import osquery as api_osquery
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery


class UtilsTest(unittest.TestCase):

  def testListToCSVBytes(self):
    csv_correct_bytes = "a,b,c,d\n".encode("utf-8")
    vals_list = ["a", "b", "c", "d"]

    received_bytes = api_osquery._ListToCsvBytes(vals_list)
    self.assertEqual(received_bytes, csv_correct_bytes)


  def testParseToCsvBytes(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="B"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="C"))

    table.rows.append(rdf_osquery.OsqueryRow(values=["1-A", "1-B", "1-C"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["2-A", "2-B", "2-C"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["3-A", "3-B", "3-C"]))

    result = rdf_osquery.OsqueryResult()
    result.table = table

    cols = ["A", "B", "C"]
    rows = [
      ["1-A", "1-B", "1-C"],
      ["2-A", "2-B", "2-C"],
      ["3-A", "3-B", "3-C"]]

    cols_bytes = (",".join(cols) + '\n').encode("utf-8")
    rows_bytes = [(",".join(row) + '\n').encode("utf-8") for row in rows]
    expected_bytes = [cols_bytes] + rows_bytes

    result_bytes = list(api_osquery._ParseToCsvBytes([result]))

    self.assertListEqual(expected_bytes, result_bytes)
