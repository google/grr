#!/usr/bin/env python
# Lint as: python3
import unittest
from unittest import mock
from grr_response_server.gui.api_plugins import osquery as api_osquery
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery

class UtilsTest(unittest.TestCase):
  def testListToCSVBytes(self):
    csv_correct_bytes = "a,b,c,d\n".encode("utf-8")
    vals_list = ["a", "b", "c", "d"]

    received_bytes = api_osquery._ListToCSVBytes(vals_list)
    self.assertEqual(received_bytes, csv_correct_bytes)


class OsqueryResultFetcherProxyTest(unittest.TestCase):

  @mock.patch("grr_response_server.gui.api_plugins.osquery.data_store")
  def testNoResultsRaiseStopIteration(self, data_store_mock):
    data_store_mock.REL_DB.ReadFlowResults.return_value = []

    fetcher = api_osquery.OsqueryResultFetcherProxy(0, 0)

    with self.assertRaises(StopIteration):
      next(fetcher)


  # @mock.patch("grr_response_server.gui.api_plugins.osquery.data_store")
  # def testEndOfResultsRaiseStopIteration(self, data_store_mock):
  #   data_store_mock.REL_DB.ReadFlowResults.return_value = []


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

    rows = [
      ["1-A", "1-B", "1-C"], ["2-A", "2-B", "2-C"], ["3-A", "3-B", "3-C"]]
    cols = ["A", "B", "C"]

    cols_bytes = (",".join(cols) + '\n').encode("utf-8")
    rows_bytes = [(",".join(row) + '\n').encode("utf-8") for row in rows]
    expected_bytes = [cols_bytes] + rows_bytes

    result_bytes = list(api_osquery._ParseToCsvBytes([result]))

    self.assertListEqual(expected_bytes, result_bytes)
