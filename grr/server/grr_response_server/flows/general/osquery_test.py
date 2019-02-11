#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii
import datetime
import hashlib
import io
import os
import unittest

from grr_response_client.client_actions import osquery as osquery_action
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.util import temp
from grr_response_server.flows.general import osquery as osquery_flow
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class OsqueryFlowTest(flow_test_lib.FlowTestsBaseclass):

  # TODO: Add tests for headers. Currently headers are unordered
  # because they are determined from the JSON output. This is less than ideal
  # and they should be ordered the same way they are in the query.

  @classmethod
  def setUpClass(cls):
    if not config.CONFIG["Osquery.path"]:
      raise unittest.SkipTest("`Osquery.path` not specified")

    # TODO: `skipTest` has to execute before `setUpClass`.
    super(OsqueryFlowTest, cls).setUpClass()

  def setUp(self):
    super(OsqueryFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _RunQueries(self, queries):
    session_id = flow_test_lib.TestFlowHelper(
        osquery_flow.OsqueryFlow.__name__,
        action_mocks.ActionMock(osquery_action.Osquery),
        client_id=self.client_id,
        token=self.token,
        queries=queries)
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def _RunQuery(self, query):
    return self._RunQueries([query])

  def testTime(self):
    date_before = datetime.date.today()
    results = self._RunQuery("SELECT day, month, year FROM time;")
    date_after = datetime.date.today()

    self.assertLen(results, 1)
    self.assertLen(results[0].tables, 1)

    table = results[0].tables[0]

    self.assertLen(table.rows, 1)

    date_result = datetime.date(
        year=int(list(table.Column("year"))[0]),
        month=int(list(table.Column("month"))[0]),
        day=int(list(table.Column("day"))[0]))
    self.assertBetween(date_result, date_before, date_after)

  def testFiles(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      bar_path = os.path.join(dirpath, "bar")
      bar_content = b"BAR"
      with io.open(bar_path, "wb") as filedesc:
        filedesc.write(bar_content)

      baz_path = os.path.join(dirpath, "baz")
      baz_content = b"BAZ"
      with io.open(baz_path, "wb") as filedesc:
        filedesc.write(baz_content)

      file_query = """
        SELECT * FROM file
        WHERE directory = "{}"
        ORDER BY path;
      """.format(dirpath)

      results = self._RunQueries([
          file_query,
          "SELECT md5, sha256 FROM hash WHERE path = \"{}\";".format(bar_path),
          "SELECT md5, sha256 FROM hash WHERE path = \"{}\";".format(baz_path),
      ])

      self.assertLen(results, 1)
      self.assertLen(results[0].tables, 3)

      file_table = results[0].tables[0]
      self.assertEqual(list(file_table.Column("path")), [bar_path, baz_path])
      self.assertEqual(list(file_table.Column("size")), ["3", "3"])

      md5 = lambda data: binascii.hexlify(hashlib.md5(data).digest())
      sha256 = lambda data: binascii.hexlify(hashlib.sha256(data).digest())

      bar_hash_table = results[0].tables[1]
      self.assertLen(bar_hash_table.rows, 1)
      self.assertEqual(list(bar_hash_table.Column("md5")), [md5(bar_content)])
      self.assertEqual(
          list(bar_hash_table.Column("sha256")), [sha256(bar_content)])

      baz_hash_table = results[0].tables[2]
      self.assertLen(baz_hash_table.rows, 1)
      self.assertEqual(list(baz_hash_table.Column("md5")), [md5(baz_content)])
      self.assertEqual(
          list(baz_hash_table.Column("sha256")), [sha256(baz_content)])

  def testFailure(self):
    with self.assertRaises(RuntimeError):
      self._RunQuery("UPDATE time SET day = -1;")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
