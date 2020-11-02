#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import io
import os
import time

from typing import List
from collections import OrderedDict
import json

from absl import app

from grr_response_client.client_actions import osquery as osquery_action
from grr_response_core import config
from grr_response_core.lib.util import temp
from grr_response_core.lib.util import text
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_server.flows.general import osquery as osquery_flow
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import osquery_test_lib
from grr.test_lib import skip
from grr.test_lib import test_lib


@skip.Unless(lambda: config.CONFIG["Osquery.path"],
             "osquery path not specified")
class OsqueryFlowTest(flow_test_lib.FlowTestsBaseclass):

  # TODO: Add tests for headers. Currently headers are unordered
  # because they are determined from the JSON output. This is less than ideal
  # and they should be ordered the same way they are in the query.

  def setUp(self):
    super(OsqueryFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _RunQuery(self, query):
    session_id = flow_test_lib.TestFlowHelper(
        osquery_flow.OsqueryFlow.__name__,
        action_mocks.ActionMock(osquery_action.Osquery),
        client_id=self.client_id,
        token=self.token,
        query=query)
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def testTime(self):
    time_before = int(time.time())
    results = self._RunQuery("SELECT unix_time FROM time;")
    time_after = int(time.time())

    self.assertLen(results, 1)

    table = results[0].table
    self.assertLen(table.rows, 1)

    time_result = int(list(table.Column("unix_time"))[0])
    self.assertBetween(time_result, time_before, time_after)

  def testFile(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      bar_path = os.path.join(dirpath, "bar")
      with io.open(bar_path, "wb") as filedesc:
        filedesc.write(b"BAR")

      baz_path = os.path.join(dirpath, "baz")
      with io.open(baz_path, "wb") as filedesc:
        filedesc.write(b"BAZ")

      results = self._RunQuery("""
        SELECT * FROM file
        WHERE directory = "{}"
        ORDER BY path;
      """.format(dirpath))

      self.assertLen(results, 1)

      table = results[0].table
      self.assertEqual(list(table.Column("path")), [bar_path, baz_path])
      self.assertEqual(list(table.Column("size")), ["3", "3"])

  def testHash(self):

    def MD5(data):
      return text.Hexify(hashlib.md5(data).digest())

    def SHA256(data):
      return text.Hexify(hashlib.sha256(data).digest())

    with temp.AutoTempFilePath() as filepath:
      content = b"FOOBARBAZ"

      with io.open(filepath, "wb") as filedesc:
        filedesc.write(content)

      results = self._RunQuery("""
        SELECT md5, sha256 FROM hash
        WHERE path = "{}";
      """.format(filepath))

      self.assertLen(results, 1)

      table = results[0].table
      self.assertLen(table.rows, 1)
      self.assertEqual(list(table.Column("md5")), [MD5(content)])
      self.assertEqual(list(table.Column("sha256")), [SHA256(content)])

  def testMultipleResults(self):
    row_count = 100

    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      for i in range(row_count):
        filepath = os.path.join(dirpath, "{:04}".format(i))
        with io.open(filepath, "wb") as filedesc:
          del filedesc  # Unused.

      query = """
        SELECT filename FROM file
        WHERE directory = "{}"
        ORDER BY filename;
      """.format(dirpath)

      # Size limit is set so that each chunk should contain 2 rows.
      with test_lib.ConfigOverrider({"Osquery.max_chunk_size": 10}):
        results = self._RunQuery(query)

      # Since each chunk is expected to have 2 rows, number of rows should be
      # equal to twice the amount of chunks.
      self.assertEqual(2 * len(results), row_count)

      for i, result in enumerate(results):
        table = result.table
        self.assertEqual(table.query, query)

        self.assertLen(table.header.columns, 1)
        self.assertEqual(table.header.columns[0].name, "filename")

        self.assertLen(table.rows, 2)
        self.assertEqual(
            list(table.Column("filename")), [
                "{:04}".format(2 * i),
                "{:04}".format(2 * i + 1),
            ])

  def testFailure(self):
    with self.assertRaises(RuntimeError):
      self._RunQuery("UPDATE time SET day = -1;")


def _CreateDictTable(column_number, row_number) -> List[OrderedDict]:
  def CellValue(col_number, row_number):
    return (f"col-{col_number}", f"col-{col_number}, row-{row_number}")

  return [
    OrderedDict(
      CellValue(col_number, row_number) for col_number in range(column_number)
    ) for row_number in range(row_number)
  ]


class FakeOsqueryFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(FakeOsqueryFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _NewTestFlowStartAndRun(self, query):
    session_id = flow_test_lib.TestFlowHelper(
        osquery_flow.OsqueryFlow.__name__,
        action_mocks.ActionMock(osquery_action.Osquery),
        client_id=self.client_id,
        token=self.token,
        query=query)
    return session_id

  def _RunQuery(self, query):
    session_id = self._NewTestFlowStartAndRun(query)
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def _AssertTablesMatch(
    self,
    table: rdf_osquery.OsqueryTable,
    expected: List[OrderedDict],
  ) -> None:
    first_row = expected[0]
    expected_columns = list(first_row.keys())

    self.assertLen(table.header.columns, len(expected_columns))

    column_pairs = zip(table.header.columns, expected_columns)
    for table_col, expected_col_name in column_pairs:
      self.assertEqual(table_col.name, expected_col_name)

    for col_name in expected_columns:
      table_col_values = list(table.Column(col_name))
      expected_col_vlues = [row[col_name] for row in expected]

      self.assertEqual(table_col_values, expected_col_vlues)

  def testSuccess(self):
    test_table = [
      OrderedDict([ ("foo", "quux"), ("bar", "norf"), ("baz", "thud") ]),
      OrderedDict([ ("foo", "blargh"), ("bar", "plugh"), ("baz", "ztesch") ]),
    ]
    stdout = json.dumps(test_table)
  
    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=""):
      results = self._RunQuery("SELECT foo, bar, baz FROM foobarbaz;")

    self.assertLen(results, 1)

    table = results[0].table
    self._AssertTablesMatch(table, test_table)

  def testFailure(self):
    stderr = "Error: near '*': syntax error"
    with osquery_test_lib.FakeOsqueryiOutput(stdout="", stderr=stderr):
      with self.assertRaises(RuntimeError):
        self._RunQuery("SELECT * FROM *;")

  def testProgressDoesntTruncate10Rows(self):
    query = "doesn't matter"
    column_number = 5
    row_number = 10

    test_table = _CreateDictTable(column_number, row_number)
    test_table_json = json.dumps(test_table)

    with osquery_test_lib.FakeOsqueryiOutput(stdout=test_table_json, stderr=""):
      flow_id = self._NewTestFlowStartAndRun(query)
      progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(progress.total_row_count, row_number)
    self.assertEqual(progress.partial_table.query, query)
    self._AssertTablesMatch(progress.partial_table, test_table)

  def testProgressTruncates20RowsTo10(self):
    query = "doesn't matter"
    column_number = 5
    row_number = 20

    test_table = _CreateDictTable(column_number, row_number)
    test_table_json = json.dumps(test_table)

    with osquery_test_lib.FakeOsqueryiOutput(stdout=test_table_json, stderr=""):
      flow_id = self._NewTestFlowStartAndRun(query)
      progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(progress.total_row_count, row_number)
    self.assertEqual(progress.partial_table.query, query)
    self._AssertTablesMatch(progress.partial_table, test_table[:10])

  def testTotalRowCountIncludesAllChunks(self):
    row_count = 100
    split_pieces = 10

    # Not using _CreateDictTable here in order to control the exact size of the
    # test table in bytes, and thus control the number of chunks
    cell_value = 'fixed'
    table = [{'column1': cell_value} for _ in range(row_count)]
    table_json = json.dumps(table)

    table_bytes = row_count * len(cell_value.encode('utf-8'))
    chunk_bytes = table_bytes // split_pieces

    with test_lib.ConfigOverrider({"Osquery.max_chunk_size": chunk_bytes}):
      with osquery_test_lib.FakeOsqueryiOutput(stdout=table_json, stderr=""):
        flow_id = self._NewTestFlowStartAndRun("doesn't matter")
        progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(progress.total_row_count, row_count)


if __name__ == "__main__":
  app.run(test_lib.main)
