#!/usr/bin/env python
from collections.abc import Sequence
import hashlib
import io
import json
import os
import sys
import time
from typing import Optional, Union
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_client.client_actions import osquery as osquery_action
from grr_response_core import config
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.util import temp
from grr_response_core.lib.util import text
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import osquery_pb2
from grr_response_proto import signed_commands_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import osquery as osquery_flow
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import osquery_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import skip
from grr.test_lib import test_lib
from grr.test_lib import testing_startup
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class GetColumnTest(absltest.TestCase):

  def testEmpty(self):
    table = osquery_pb2.OsqueryTable()
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="A"))
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="B"))
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="C"))

    self.assertEmpty(list(osquery_flow._GetColumn(table, "A")))
    self.assertEmpty(list(osquery_flow._GetColumn(table, "B")))
    self.assertEmpty(list(osquery_flow._GetColumn(table, "C")))

  def testValues(self):
    table = osquery_pb2.OsqueryTable()
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="A"))
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="B"))
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="C"))
    table.rows.append(osquery_pb2.OsqueryRow(values=["foo", "bar", "baz"]))
    table.rows.append(osquery_pb2.OsqueryRow(values=["quux", "norf", "thud"]))
    table.rows.append(osquery_pb2.OsqueryRow(values=["blarg", "shme", "ztesh"]))

    self.assertEqual(
        list(osquery_flow._GetColumn(table, "A")), ["foo", "quux", "blarg"]
    )
    self.assertEqual(
        list(osquery_flow._GetColumn(table, "B")), ["bar", "norf", "shme"]
    )
    self.assertEqual(
        list(osquery_flow._GetColumn(table, "C")), ["baz", "thud", "ztesh"]
    )

  def testIncorrect(self):
    table = osquery_pb2.OsqueryTable()
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="A"))
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="B"))
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="C"))

    with self.assertRaises(KeyError):
      list(osquery_flow._GetColumn(table, "D"))


class TruncateTest(absltest.TestCase):

  def testTruncation(self):
    table = osquery_pb2.OsqueryTable()
    table.header.columns.append(osquery_pb2.OsqueryColumn(name="A"))

    table.rows.append(osquery_pb2.OsqueryRow(values=["cell1"]))
    table.rows.append(osquery_pb2.OsqueryRow(values=["cell2"]))
    table.rows.append(osquery_pb2.OsqueryRow(values=["cell3"]))

    truncated = osquery_flow._Truncate(table, 1)
    column_values = list(osquery_flow._GetColumn(truncated, "A"))

    self.assertLen(truncated.rows, 1)
    self.assertEqual(column_values, ["cell1"])


@skip.Unless(
    lambda: config.CONFIG["Osquery.path"], "osquery path not specified"
)
class OsqueryFlowTest(flow_test_lib.FlowTestsBaseclass):

  # TODO - Add tests for headers. Currently headers are unordered
  # because they are determined from the JSON output. This is less than ideal
  # and they should be ordered the same way they are in the query.

  def setUp(self):
    super(OsqueryFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _RunFlow(
      self,
      query: str,
      configuration_content: Optional[str] = None,
  ) -> Sequence[osquery_pb2.OsqueryResult]:
    session_id = flow_test_lib.StartAndRunFlow(
        osquery_flow.OsqueryFlow,
        action_mocks.ActionMock(osquery_action.Osquery),
        client_id=self.client_id,
        creator=self.test_username,
        flow_args=osquery_pb2.OsqueryFlowArgs(
            query=query,
            configuration_content=configuration_content,
        ),
    )
    return flow_test_lib.GetUnpackedFlowResults(
        self.client_id,
        session_id,
        osquery_pb2.OsqueryResult,
    )

  def testTime(self):
    time_before = int(time.time())
    results = self._RunFlow(query="SELECT unix_time FROM time;")
    time_after = int(time.time())

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], osquery_pb2.OsqueryResult)

    table = results[0].table
    self.assertLen(table.rows, 1)

    time_result = int(list(osquery_flow._GetColumn(table, "unix_time"))[0])
    self.assertBetween(time_result, time_before, time_after)

  def testConfigurationContentNotJSONError(self):
    with self.assertRaises(RuntimeError):
      _ = self._RunFlow(
          "SELECT * FROM processes;", configuration_content="not json content"
      )

  def testConfigurationContent(self):
    configuration_content = json.dumps(
        {"views": {"bar": "SELECT * FROM processes;"}}
    )

    results = self._RunFlow(
        "SELECT * FROM bar where pid = {};".format(os.getpid()),
        configuration_content=configuration_content,
    )
    self.assertLen(results, 1)

    table = results[0].table
    self.assertEqual(
        list(osquery_flow._GetColumn(table, "pid")), [str(os.getpid())]
    )

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
      self.assertEqual(
          list(osquery_flow._GetColumn(table, "path")), [bar_path, baz_path]
      )
      self.assertEqual(list(osquery_flow._GetColumn(table, "size")), ["3", "3"])

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
      self.assertEqual(
          list(osquery_flow._GetColumn(table, "md5")), [MD5(content)]
      )
      self.assertEqual(
          list(osquery_flow._GetColumn(table, "sha256")), [SHA256(content)]
      )

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
            list(osquery_flow._GetColumn(table, "filename")),
            [
                "{:04}".format(2 * i),
                "{:04}".format(2 * i + 1),
            ],
        )

  def testFailure(self):
    with self.assertRaises(RuntimeError):
      self._RunFlow("UPDATE time SET day = -1;")


class FakeOsqueryFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(FakeOsqueryFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def _InitializeFlow(
      self,
      query: Optional[str] = None,
      check_flow_errors: bool = True,
      file_collection_columns: Optional[Sequence[str]] = None,
  ) -> str:
    query = query or "<<<FAKE OSQUERY FLOW QUERY PLACEHOLDER>>>"
    return flow_test_lib.StartAndRunFlow(
        osquery_flow.OsqueryFlow,
        action_mocks.OsqueryClientMock(),
        client_id=self.client_id,
        creator=self.test_username,
        flow_args=osquery_pb2.OsqueryFlowArgs(
            query=query,
            file_collection_columns=file_collection_columns,
        ),
        check_flow_errors=check_flow_errors,
    )

  def _RunFlow(
      self,
      query: Optional[str] = None,
      file_collection_columns: Optional[Sequence[str]] = None,
  ) -> Sequence[Union[osquery_pb2.OsqueryResult, jobs_pb2.StatEntry]]:
    flow_id = self._InitializeFlow(
        query=query, file_collection_columns=file_collection_columns
    )
    return flow_test_lib.GetUnpackedFlowResultsOfTypes(
        self.client_id,
        flow_id,
        [osquery_pb2.OsqueryResult, jobs_pb2.StatEntry],
    )

  def testSuccess(self):
    stdout = """
    [
      { "foo": "quux", "bar": "norf", "baz": "thud" },
      { "foo": "blargh", "bar": "plugh", "baz": "ztesch" }
    ]
    """
    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=""):
      results = self._RunFlow()

    self.assertLen(results, 1)

    res = results[0]
    assert isinstance(res, osquery_pb2.OsqueryResult)
    table = res.table
    self.assertLen(table.header.columns, 3)
    self.assertEqual(table.header.columns[0].name, "foo")
    self.assertEqual(table.header.columns[1].name, "bar")
    self.assertEqual(table.header.columns[2].name, "baz")
    self.assertEqual(
        list(osquery_flow._GetColumn(table, "foo")), ["quux", "blargh"]
    )
    self.assertEqual(
        list(osquery_flow._GetColumn(table, "bar")), ["norf", "plugh"]
    )
    self.assertEqual(
        list(osquery_flow._GetColumn(table, "baz")), ["thud", "ztesch"]
    )

  def testFailure(self):
    stderr = "Error: query syntax error"

    with osquery_test_lib.FakeOsqueryiOutput(stdout="", stderr=stderr):
      flow_id = flow_test_lib.StartFlow(
          flow_cls=osquery_flow.OsqueryFlow,
          client_id=self.client_id,
          creator=self.test_username,
          flow_args=osquery_pb2.OsqueryFlowArgs(
              query="<<<FAKE OSQUERY FLOW QUERY PLACEHOLDER>>>"
          ),
      )

      with self.assertRaises(RuntimeError):
        flow_test_lib.RunFlow(
            client_id=self.client_id,
            flow_id=flow_id,
            client_mock=action_mocks.OsqueryClientMock(),
        )

    flow = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn(stderr, flow.error_message)

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
        flow_id = self._InitializeFlow()
        progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

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
        flow_id = self._InitializeFlow()
        progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

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
          flow_id = self._InitializeFlow()
          progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

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
        flow_id = self._InitializeFlow()
        progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

    self.assertEqual(progress.total_row_count, row_count)

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
        results = self._RunFlow(file_collection_columns=["collect_column"])

    self.assertLen(results, 2)
    self.assertIsInstance(results[0], osquery_pb2.OsqueryResult)
    self.assertIsInstance(results[1], jobs_pb2.StatEntry)

    res1 = results[1]
    assert isinstance(res1, jobs_pb2.StatEntry)
    pathspec = res1.pathspec
    client_path = db.ClientPath.FromPathSpec(
        self.client_id, mig_paths.ToRDFPathSpec(pathspec)
    )
    fd_rel_db = file_store.OpenFile(client_path)
    file_text = fd_rel_db.read().decode("utf-8")
    self.assertEqual(file_text, "Just sample text to put in the file.")

  def testFlowDoesntFailWhenCollectingFilesFromEmptyResult(self):
    empty_table = """
    [

    ]
    """

    with osquery_test_lib.FakeOsqueryiOutput(stdout=empty_table, stderr=""):
      results = self._RunFlow(file_collection_columns=["collect_column"])

    self.assertEmpty(results)

  def testFlowFailsWhenCollectingFileAboveSingleLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_SINGLE_FILE_BYTES",
          less_than_necessary_bytes,
      ):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          with self.assertRaises(RuntimeError):
            self._RunFlow(file_collection_columns=["collect_column"])

  def testFlowReportsErrorWhenCollectingFileAboveSingleLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_SINGLE_FILE_BYTES",
          less_than_necessary_bytes,
      ):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          flow_id = self._InitializeFlow(
              file_collection_columns=["collect_column"],
              check_flow_errors=False,
          )
          progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

      self.assertEqual(
          f"File with path {temp_file_path} is too big: "
          f"{target_bytes} bytes when the limit is "
          f"{less_than_necessary_bytes} bytes.",
          progress.error_message,
      )

  def testFlowDoesntCollectSingleFileAboveTotalLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_TOTAL_BYTES",
          less_than_necessary_bytes,
      ):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          with self.assertRaises(RuntimeError):
            self._RunFlow(file_collection_columns=["collect_column"])

  def testFlowReportsErrorWhenCollectingSingleFileAboveTotalLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      target_bytes = 2**20  # 1 MiB
      less_than_necessary_bytes = target_bytes // 2

      with io.open(temp_file_path, "wb") as fd:
        fd.write(b"1" * target_bytes)

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with mock.patch.object(
          osquery_flow,
          "FILE_COLLECTION_MAX_TOTAL_BYTES",
          less_than_necessary_bytes,
      ):
        with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
          flow_id = self._InitializeFlow(
              file_collection_columns=["collect_column"],
              check_flow_errors=False,
          )
          progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

    self.assertEqual(
        "Files for collection exceed the total size limit of "
        f"{less_than_necessary_bytes} bytes.",
        progress.error_message,
    )

  def testFlowDoesntCollectWhenColumnsAboveLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      with mock.patch.object(osquery_flow, "FILE_COLLECTION_MAX_COLUMNS", 1):
        # Should raise immediately, no need to fake Osquery output
        with self.assertRaises(RuntimeError):
          self._RunFlow(file_collection_columns=["collect1", "collect2"])

  def testFlowReportsErrorWhenCollectingColumnsAboveLimit(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      with mock.patch.object(osquery_flow, "FILE_COLLECTION_MAX_COLUMNS", 1):
        flow_id = self._InitializeFlow(
            file_collection_columns=["collect1", "collect2"],
            check_flow_errors=False,
        )
        progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

    self.assertEqual(
        "Requested file collection for 2 columns, but the limit is 1 columns.",
        progress.error_message,
    )

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
            self._RunFlow(file_collection_columns=["collect_column"])

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
              file_collection_columns=["collect_column"],
              check_flow_errors=False,
          )
          progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

    self.assertEqual(
        "Requested file collection on a table with 2 rows, "
        "but the limit is 1 rows.",
        progress.error_message,
    )

  def testFlowFailsWhenCollectingUnexistingColumn(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
        with self.assertRaises(RuntimeError):
          self._RunFlow(file_collection_columns=["non_existent_column"])

  def testFlowReportsErrorWhenCollectingUnexistingColumn(self):
    with temp.AutoTempFilePath() as temp_file_path:
      with io.open(temp_file_path, mode="w", encoding="utf-8") as fd:
        fd.write("Just sample text to put in the file.")

      table = f"""
      [
        {{ "collect_column": "{temp_file_path}" }}
      ]
      """

      with osquery_test_lib.FakeOsqueryiOutput(stdout=table, stderr=""):
        flow_id = self._InitializeFlow(
            file_collection_columns=["non_existent_column"],
            check_flow_errors=False,
        )
        progress = flow_test_lib.GetFlowProgressProto(self.client_id, flow_id)

    self.assertEqual(
        "No such column 'non_existent_column' to collect files from.",
        progress.error_message,
    )

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
        flow_id = self._InitializeFlow(
            file_collection_columns=["collect_column"]
        )

    flow = flow_base.FlowBase.CreateFlowInstance(
        data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    )
    results = data_store.REL_DB.ReadFlowResults(
        self.client_id, flow_id, offset=0, count=sys.maxsize
    )

    mappings = list(flow.GetFilesArchiveMappings(iter(results)))
    self.assertCountEqual(
        mappings,
        [
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(
                    self.client_id, temp_file_path1.split("/")[1:]
                ),
                f"osquery_collected_files{temp_file_path1}",
            ),
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(
                    self.client_id, temp_file_path2.split("/")[1:]
                ),
                f"osquery_collected_files{temp_file_path2}",
            ),
        ],
    )

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
        flow_id = self._InitializeFlow(
            file_collection_columns=["collect_column"]
        )

    flow = flow_base.FlowBase.CreateFlowInstance(
        data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    )
    results = list(
        data_store.REL_DB.ReadFlowResults(
            self.client_id, flow_id, offset=0, count=sys.maxsize
        )
    )

    # This is how we emulate duplicate filenames in the results
    duplicated_results = results + results + results

    mappings = list(flow.GetFilesArchiveMappings(iter(duplicated_results)))
    self.assertCountEqual(
        mappings,
        [
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(self.client_id, temp_file_path.split("/")[1:]),
                f"osquery_collected_files{temp_file_path}",
            ),
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(self.client_id, temp_file_path.split("/")[1:]),
                f"osquery_collected_files{temp_file_path}-1",
            ),
            flow_base.ClientPathArchiveMapping(
                db.ClientPath.OS(self.client_id, temp_file_path.split("/")[1:]),
                f"osquery_collected_files{temp_file_path}-2",
            ),
        ],
    )

  def testSkipEmptyTable(self):
    with osquery_test_lib.FakeOsqueryiOutput(stdout="[]", stderr=""):
      results = self._RunFlow()

    self.assertEmpty(results)


class OsqueryFlowTestRRG(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  @db_test_lib.WithDatabase
  def testProcesses(self, rel_db: db.Database):
    # TODO - Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/bin/osqueryd".encode("utf-8")
    command.args.add().signed = "--S"
    command.args.add().signed = "--json"
    command.unsigned_stdin_allowed = True

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "osquery"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.LINUX
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    rel_db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    flow_args = osquery_pb2.OsqueryFlowArgs()
    flow_args.query = "SELECT cmdline, uid, gid FROM processes WHERE pid = 1;"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=osquery_flow.OsqueryFlow,
        flow_args=flow_args,
        handlers=rrg_test_lib.FakeOsqueryHandlers({
            # pyformat: disable
            "SELECT cmdline, uid, gid FROM processes WHERE pid = 1;": """
[
  {"cmdline":"/sbin/init splash","gid":"0","uid":"0"}
]
            """,
            # pyformat: enable
        }),
    )

    flow_obj = rel_db.ReadFlowObject(
        client_id=client_id,
        flow_id=flow_id,
    )
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=osquery_pb2.OsqueryResult,
    )
    self.assertLen(flow_results, 1)

    flow_result = flow_results[0]
    self.assertLen(flow_result.table.header.columns, 3)
    self.assertEqual(flow_result.table.header.columns[0].name, "cmdline")
    self.assertEqual(flow_result.table.header.columns[1].name, "gid")
    self.assertEqual(flow_result.table.header.columns[2].name, "uid")
    self.assertLen(flow_result.table.rows, 1)
    self.assertEqual(flow_result.table.rows[0].values[0], "/sbin/init splash")
    self.assertEqual(flow_result.table.rows[0].values[1], "0")
    self.assertEqual(flow_result.table.rows[0].values[2], "0")

  @db_test_lib.WithDatabase
  def testConfigPath(self, rel_db: db.Database):
    # TODO - Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/bin/osqueryd".encode("utf-8")
    command.args.add().signed = "--S"
    command.args.add().signed = "--json"
    command.args.add().signed = "--config-path"
    command.args.add().filestore_file_sha256_allowed = True
    command.unsigned_stdin_allowed = True

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "osquery_with_config"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.LINUX
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    rel_db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    flow_args = osquery_pb2.OsqueryFlowArgs()
    flow_args.query = "SELECT cmdline, uid, gid FROM processes WHERE pid = 1;"
    flow_args.configuration_content = """
    {
      "options": {
        "logger_plugin": "filesystem",
        "logger_path": "/var/log/osquery",
        "verbose": "true"
      }
    }
    """

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=osquery_flow.OsqueryFlow,
        flow_args=flow_args,
        # pyformat: disable
        handlers=rrg_test_lib.FakeOsqueryHandlers({
            "SELECT cmdline, uid, gid FROM processes WHERE pid = 1;": """
[
  {"cmdline":"/sbin/init splash","gid":"0","uid":"0"}
]
            """,
        }, rrg_test_lib.Filestore()),
        # pyformat: enable
    )

    flow_obj = rel_db.ReadFlowObject(
        client_id=client_id,
        flow_id=flow_id,
    )
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = flow_test_lib.GetUnpackedFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        result_type=osquery_pb2.OsqueryResult,
    )
    self.assertLen(flow_results, 1)

    flow_result = flow_results[0]
    self.assertLen(flow_result.table.header.columns, 3)
    self.assertEqual(flow_result.table.header.columns[0].name, "cmdline")
    self.assertEqual(flow_result.table.header.columns[1].name, "gid")
    self.assertEqual(flow_result.table.header.columns[2].name, "uid")
    self.assertLen(flow_result.table.rows, 1)
    self.assertEqual(flow_result.table.rows[0].values[0], "/sbin/init splash")
    self.assertEqual(flow_result.table.rows[0].values[1], "0")
    self.assertEqual(flow_result.table.rows[0].values[2], "0")

  @db_test_lib.WithDatabase
  def testFileCollection(self, rel_db: db.Database):
    # TODO - Load signed commands from the `.textproto` file to
    # ensure integrity.
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/usr/bin/osqueryd".encode("utf-8")
    command.args.add().signed = "--S"
    command.args.add().signed = "--json"
    command.unsigned_stdin_allowed = True

    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "osquery"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.LINUX
    signed_command.command = command.SerializeToString()
    signed_command.ed25519_signature = b"\x00" * 64
    rel_db.WriteSignedCommand(signed_command)

    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    flow_args = osquery_pb2.OsqueryFlowArgs()
    flow_args.query = "SELECT path FROM file WHERE path LIKE '/usr/bin/%';"
    flow_args.file_collection_columns.append("path")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=osquery_flow.OsqueryFlow,
        flow_args=flow_args,
        # pyformat: disable
        handlers=dict(rrg_test_lib.FakeOsqueryHandlers({
            "SELECT path FROM file WHERE path LIKE '/usr/bin/%';": """
[
  {"path":"/usr/bin/cat"},
  {"path":"/usr/bin/ls"}
]
            """,
        })) | dict(rrg_test_lib.FakePosixFileHandlers({
            "/usr/bin/cat": b"ELF\x00CAT",
            "/usr/bin/ls": b"ELF\x00LS",
        })),
        # pyformat: enable
    )

    flow_obj = rel_db.ReadFlowObject(
        client_id=client_id,
        flow_id=flow_id,
    )
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = flow_test_lib.GetUnpackedFlowResultsOfTypes(
        client_id,
        flow_id,
        [osquery_pb2.OsqueryResult, jobs_pb2.StatEntry],
    )

    osquery_results = []
    stat_entries_by_path = {}
    for flow_result in flow_results:
      if isinstance(flow_result, osquery_pb2.OsqueryResult):
        osquery_results.append(flow_result)
      elif isinstance(flow_result, jobs_pb2.StatEntry):
        stat_entry = flow_result
        stat_entries_by_path[stat_entry.pathspec.path] = stat_entry
      else:
        raise ValueError(f"Unexpected flow result: {flow_result}")

    self.assertLen(osquery_results, 1)
    osquery_result = osquery_results[0]

    self.assertLen(osquery_result.table.header.columns, 1)
    self.assertEqual(osquery_result.table.header.columns[0].name, "path")
    self.assertLen(osquery_result.table.rows, 2)
    self.assertEqual(osquery_result.table.rows[0].values[0], "/usr/bin/cat")
    self.assertEqual(osquery_result.table.rows[1].values[0], "/usr/bin/ls")

    self.assertLen(stat_entries_by_path, 2)
    self.assertEqual(  # pylint: disable=g-generic-assert
        stat_entries_by_path["/usr/bin/cat"].st_size,
        len(b"ELF\x00CAT"),
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        stat_entries_by_path["/usr/bin/ls"].st_size,
        len(b"ELF\x00LS"),
    )

    file_cat = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("usr", "bin", "cat"),
        ),
    )
    self.assertEqual(file_cat.read(), b"ELF\x00CAT")

    file_ls = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("usr", "bin", "ls"),
        ),
    )
    self.assertEqual(file_ls.read(), b"ELF\x00LS")


if __name__ == "__main__":
  app.run(test_lib.main)
