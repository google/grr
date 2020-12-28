#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import io
import json
import os
import time
from typing import List

from absl import app
import mock

from grr_response_client.client_actions import osquery as osquery_action
from grr_response_core import config
from grr_response_core.lib.util import temp
from grr_response_core.lib.util import text
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_server.flows.general import osquery as osquery_flow
from grr_response_server.databases import db
from grr_response_server import file_store
from grr_response_server import flow_base
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

  def _RunFlow(self, query):
    session_id = flow_test_lib.TestFlowHelper(
        osquery_flow.OsqueryFlow.__name__,
        action_mocks.ActionMock(osquery_action.Osquery),
        client_id=self.client_id,
        token=self.token,
        query=query)
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def testTime(self):
    time_before = int(time.time())
    results = self._RunFlow("SELECT unix_time FROM time;")
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

      results = self._RunFlow("""
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

      results = self._RunFlow("""
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
        results = self._RunFlow(query)

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
      self._RunFlow("UPDATE time SET day = -1;")


class FakeOsqueryFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(FakeOsqueryFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _InitializeFlow(
      self,
      query: str,
      file_collection_columns: List[str],
      **kwargs,
  ) -> None:
    session_id = flow_test_lib.TestFlowHelper(
        osquery_flow.OsqueryFlow.__name__,
        action_mocks.OsqueryClientMock(),
        client_id=self.client_id,
        token=self.token,
        query=query,
        file_collection_columns=file_collection_columns,
        **kwargs)
    return session_id

  def _RunFlow(self, query: str, file_collection_columns: List[str]) -> None:
    session_id = self._InitializeFlow(query, file_collection_columns)
    return flow_test_lib.GetFlowResults(self.client_id, session_id)

  def testSuccess(self):
    stdout = """
    [
      { "foo": "quux", "bar": "norf", "baz": "thud" },
      { "foo": "blargh", "bar": "plugh", "baz": "ztesch" }
    ]
    """
    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=""):
      results = self._RunFlow("SELECT foo, bar, baz FROM foobarbaz;", [])

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
        self._RunFlow("SELECT * FROM *;", [])

  def testSmallerTruncationLimit(self):
    two_row_table = """
    [
      { "col1": "cell-1-1", "col2": "cell-1-2", "col3": "cell-1-3" },
      { "col1": "cell-2-1", "col2": "cell-2-2", "col3": "cell-2-3" }
    ]
    """
    max_rows = 1

    with osquery_test_lib.FakeOsqueryiOutput(stdout=two_row_table, stderr=""):
      with mock.patch.object(osquery_flow, "TRUNCATED_ROW_COUNT", max_rows):
        flow_id = self._InitializeFlow("query doesn't matter", [])
        progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(len(progress.partial_table.rows), max_rows)

  def testBiggerTruncationLimit(self):
    three_row_table = """
    [
      { "col1": "cell-1-1", "col2": "cell-1-2", "col3": "cell-1-3" },
      { "col1": "cell-2-1", "col2": "cell-2-2", "col3": "cell-2-3" },
      { "col1": "cell-3-1", "col2": "cell-3-2", "col3": "cell-3-3" }
    ]
    """
    max_rows = 5

    with osquery_test_lib.FakeOsqueryiOutput(stdout=three_row_table, stderr=""):
      with mock.patch.object(osquery_flow, "TRUNCATED_ROW_COUNT", max_rows):
        flow_id = self._InitializeFlow("query doesn't matter", [])
        progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(len(progress.partial_table.rows), 3)

  def testChunksSmallerThanTruncation(self):
    row_count = 100
    max_rows = 70
    split_pieces = 10

    cell_value = "fixed"
    table = [{"column1": cell_value}] * row_count
    table_json = json.dumps(table)

    table_bytes = row_count * len(cell_value.encode("utf-8"))
    chunk_bytes = table_bytes // split_pieces

    with test_lib.ConfigOverrider({"Osquery.max_chunk_size": chunk_bytes}):
      with osquery_test_lib.FakeOsqueryiOutput(stdout=table_json, stderr=""):
        with mock.patch.object(osquery_flow, "TRUNCATED_ROW_COUNT", max_rows):
          flow_id = self._InitializeFlow("doesn't matter", [])
          progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(len(progress.partial_table.rows), max_rows)

  def testTotalRowCountIncludesAllChunks(self):
    row_count = 100
    split_pieces = 10

    cell_value = "fixed"
    table = [{"column1": cell_value}] * row_count
    table_json = json.dumps(table)

    table_bytes = row_count * len(cell_value.encode("utf-8"))
    chunk_bytes = table_bytes // split_pieces

    with test_lib.ConfigOverrider({"Osquery.max_chunk_size": chunk_bytes}):
      with osquery_test_lib.FakeOsqueryiOutput(stdout=table_json, stderr=""):
        flow_id = self._InitializeFlow("doesn't matter", [])
        progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(progress.total_row_count, row_count)

  def testFlowFailsWhenCollectingFileAboveSingleLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_collumn": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_SINGLE_FILE_BYTES",
          less_than_necessary_bytes):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          with self.assertRaises(RuntimeError):
            self._RunFlow("Doesn't matter", ["collect_collumn"])

  def testFlowReportsErrorWhenCollectingFileAboveSingleLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_collumn": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_SINGLE_FILE_BYTES",
          less_than_necessary_bytes):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          flow_id = self._InitializeFlow(
              "Doesn't matter", ["collect_collumn"], check_flow_errors=False)
          progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

      self.assertEqual(f"File with path {temp_file_path} is too big: "
          f"{target_bytes} bytes when the limit is "
          f"{less_than_necessary_bytes} bytes.", progress.error_message)

  def testFlowDoesntCollectSingleFileAboveTotalLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_collumn": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_TOTAL_BYTES",
          less_than_necessary_bytes):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          with self.assertRaises(RuntimeError):
            self._RunFlow("Doesn't matter", ["collect_collumn"])

  def testFlowReportsErrorWhenCollectingSingleFileAboveTotalLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_collumn": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_TOTAL_BYTES",
          less_than_necessary_bytes):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          flow_id = self._InitializeFlow(
              "Doesn't matter", ["collect_collumn"], check_flow_errors=False)
          progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(
        "Files for collection exceed the total size limit of "
        f"{less_than_necessary_bytes} bytes.", progress.error_message)

  def testFlowCollectFile(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
        results = self._RunFlow("Doesn't matter", ["collect_column"])
      
    self.assertLen(results, 2)
    self.assertEqual(type(results[0]), rdf_osquery.OsqueryResult)
    self.assertEqual(type(results[1]), rdf_client_fs.StatEntry)

    pathspec = results[1].pathspec
    client_path = db.ClientPath.FromPathSpec(self.client_id, pathspec)
    fd_rel_db = file_store.OpenFile(client_path)
    file_text = fd_rel_db.read().decode("utf-8")
    self.assertEqual(file_text, "Just sample text to put in the file.")

  def testFlowDoesntCollectWhenColumnsAboveLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      with mock.patch.object(osquery_flow, "FILE_COLLECTION_MAX_COLUMNS", 1):
        # Should raise immediately, no need to fake Osquery output
        with self.assertRaises(RuntimeError):
          self._RunFlow("Doesn't matter", ["collect1", "collect2"])

  def testFlowReportsErrorWhenCollectingColumnsAboveLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      with mock.patch.object(osquery_flow, "FILE_COLLECTION_MAX_COLUMNS", 1):
        flow_id = self._InitializeFlow(
            "Doesn't matter", ["collect1", "collect2"], check_flow_errors=False)
        progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(
      "Requested file collection for 2 columns, but the limit is 1 columns.",
      progress.error_message)

  def testFlowDoesntCollectWhenRowsAboveLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}"}},
        {{ "collect_column": "{temp_file_path}"}}
      ]
      """

      with mock.patch.object(osquery_flow, "FILE_COLLECTION_MAX_ROWS", 1):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          with self.assertRaises(RuntimeError):
            self._RunFlow("Doesn't matter", ["collect_collumn"])

  def testFlowReportsErrorWhenCollectingRowsAboveLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}"}},
        {{ "collect_column": "{temp_file_path}"}}
      ]
      """

      with mock.patch.object(osquery_flow, "FILE_COLLECTION_MAX_ROWS", 1):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          flow_id = self._InitializeFlow(
              "Doesn't matter", ["collect_collumn"], check_flow_errors=False)
          progress = flow_test_lib.GetFlowProgress(self.client_id, flow_id)

    self.assertEqual(
        "Requested file collection on a table with 2 rows, "
        "but the limit is 1 rows.", progress.error_message)

  def testArchiveMappingsForMultipleFiles(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dir_path:
      temp_file_path1 = os.path.join(temp_dir_path, "foo")
      temp_file_path2 = os.path.join(temp_dir_path, "bar")

      with io.open(temp_file_path1, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file 1.")
      with io.open(temp_file_path2, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file 2.")

      table = f"""
      [
        {{ "collect_column": "{temp_file_path1}" }},
        {{ "collect_column": "{temp_file_path2}" }}
      ]
      """

      with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
        flow_id = self._InitializeFlow("Doesn't matter", ["collect_column"])

    flow = flow_base.FlowBase.CreateFlowInstance(
        flow_test_lib.GetFlowObj(self.client_id, flow_id))
    results = flow_test_lib.GetRawFlowResults(self.client_id, flow_id)

    mappings = list(flow.GetFilesArchiveMappings(results))
    self.assertCountEqual(mappings, [
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             temp_file_path1.split("/")[1:]),
            f"osquery_collected_files{temp_file_path1}",
        ),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             temp_file_path2.split("/")[1:]),
            f"osquery_collected_files{temp_file_path2}",
        ),
    ])

  def testArchiveMappingsForDuplicateFilesInResult(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
        flow_id = self._InitializeFlow("Doesn't matter", ["collect_column"])

    flow = flow_base.FlowBase.CreateFlowInstance(
        flow_test_lib.GetFlowObj(self.client_id, flow_id))
    results = flow_test_lib.GetRawFlowResults(self.client_id, flow_id)

    # This is how we emulate duplicate filenames in the results
    duplicated_results = results + results + results

    mappings = list(flow.GetFilesArchiveMappings(duplicated_results))
    self.assertCountEqual(mappings, [
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             temp_file_path.split("/")[1:]),
            f"osquery_collected_files{temp_file_path}",
        ),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             temp_file_path.split("/")[1:]),
            f"osquery_collected_files{temp_file_path}-1",
        ),
        flow_base.ClientPathArchiveMapping(
            db.ClientPath.OS(self.client_id,
                             temp_file_path.split("/")[1:]),
            f"osquery_collected_files{temp_file_path}-2",
        ),
    ])


if __name__ == "__main__":
  app.run(test_lib.main)
