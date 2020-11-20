#!/usr/bin/env python
# Lint as: python3
import unittest

from grr_response_server.gui.api_plugins import osquery as api_osquery
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery


class UtilsTest(unittest.TestCase):

  def testListToCSVBytes(self):
    received_bytes = api_osquery._LineToCsvBytes(["a", "b", "c", "d"])

    csv_correct_bytes = "a,b,c,d\r\n".encode("utf-8")
    self.assertEqual(received_bytes, csv_correct_bytes)


  def testSomeTextToCsvBytes(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="A"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="B"))

    table.rows.append(rdf_osquery.OsqueryRow(values=["1-A", "1-B"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["2-A", "2-B"]))

    result = rdf_osquery.OsqueryResult()
    result.table = table

    result_bytes = list(api_osquery._ParseToCsvBytes([result]))

    expected_bytes = [
      "A,B\r\n".encode("utf-8"),
      "1-A,1-B\r\n".encode("utf-8"),
      "2-A,2-B\r\n".encode("utf-8")]
    self.assertListEqual(expected_bytes, result_bytes)

  def testTextWithCommasToCsvBytes(self):
    table = rdf_osquery.OsqueryTable()
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="c,o,l,u,m,n"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["c,e,l,l"]))

    result = rdf_osquery.OsqueryResult()
    result.table = table

    result_bytes = list(api_osquery._ParseToCsvBytes([result]))

    expected_bytes = [
      "\"c,o,l,u,m,n\"\r\n".encode("utf-8"),
      "\"c,e,l,l\"\r\n".encode("utf-8")]
    self.assertListEqual(expected_bytes, result_bytes)
