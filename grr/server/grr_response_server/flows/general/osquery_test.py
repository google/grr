#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii
import datetime
import hashlib
import io
import os

from absl import app
from future.builtins import range

from grr_response_client.client_actions import osquery as osquery_action
from grr_response_core import config
from grr_response_core.lib.util import temp
from grr_response_server.flows.general import osquery as osquery_flow
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import osquery_test_lib
from grr.test_lib import skip
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
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
    date_before = datetime.date.today()
    results = self._RunQuery("SELECT day, month, year FROM time;")
    date_after = datetime.date.today()

    self.assertLen(results, 1)

    table = results[0].table
    self.assertLen(table.rows, 1)

    date_result = datetime.date(
        year=int(list(table.Column("year"))[0]),
        month=int(list(table.Column("month"))[0]),
        day=int(list(table.Column("day"))[0]))
    self.assertBetween(date_result, date_before, date_after)

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
    md5 = lambda data: binascii.hexlify(hashlib.md5(data).digest())
    sha256 = lambda data: binascii.hexlify(hashlib.sha256(data).digest())

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
      self.assertEqual(list(table.Column("md5")), [md5(content)])
      self.assertEqual(list(table.Column("sha256")), [sha256(content)])

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
      with test_lib.ConfigOverrider({"Osquery.max_chunk_size": 6}):
        results = self._RunQuery(query)

      # Since each chunk is expected to have 2 rows, number of chunks should be
      # equal to twice the amount of rows.
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


@db_test_lib.DualDBTest
class FakeOsqueryFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(FakeOsqueryFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _RunQuery(self, query):
    session_id = flow_test_lib.TestFlowHelper(
        osquery_flow.OsqueryFlow.__name__,
        action_mocks.ActionMock(osquery_action.Osquery),
        client_id=self.client_id,
        token=self.token,
        query=query)
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def testSuccess(self):
    stdout = """
    [
      { "foo": "quux", "bar": "norf", "baz": "thud" },
      { "foo": "blargh", "bar": "plugh", "baz": "ztesch" }
    ]
    """
    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=""):
      results = self._RunQuery("SELECT foo, bar, baz FROM foobarbaz;")

    self.assertLen(results, 1)

    table = results[0].table
    self.assertLen(table.header.columns, 3)
    self.assertEqual(table.header.columns[0].name, "foo")
    self.assertEqual(table.header.columns[1].name, "bar")
    self.assertEqual(table.header.columns[2].name, "baz")
    self.assertEqual(list(table.Column("foo")), ["quux", "blargh"])
    self.assertEqual(list(table.Column("bar")), ["norf", "plugh"])
    self.assertEqual(list(table.Column("baz")), ["thud", "ztesch"])

  def testFailure(self):
    stderr = "Error: near '*': syntax error"
    with osquery_test_lib.FakeOsqueryiOutput(stdout="", stderr=stderr):
      with self.assertRaises(RuntimeError):
        self._RunQuery("SELECT * FROM *;")


if __name__ == "__main__":
  app.run(test_lib.main)
