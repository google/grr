#!/usr/bin/env python
"""A module with flow class calling the osquery client action."""

from collections.abc import Iterable, Iterator
import json

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import mig_osquery
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import osquery_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import osquery as rdf_server_osquery


TRUNCATED_ROW_COUNT = 10

FILE_COLLECTION_MAX_COLUMNS = 5
FILE_COLLECTION_MAX_ROWS = 1000
FILE_COLLECTION_MAX_SINGLE_FILE_BYTES = 2**30 // 2  # 1/2 GiB
FILE_COLLECTION_MAX_TOTAL_BYTES = 2**30  # 1 GiB


def _GetTotalRowCount(responses: Iterable[osquery_pb2.OsqueryResult]) -> int:
  get_row_lengths = lambda response: len(response.table.rows)
  row_lengths = map(get_row_lengths, responses)
  return sum(row_lengths)


def _GetColumn(
    table: osquery_pb2.OsqueryTable, column_name: str
) -> Iterator[str]:
  """Iterates over values of a given column.

  Args:
    table: An OsqueryTable to iterate over.
    column_name: A name of the column to retrieve the values for.

  Yields:
    Values of the specified column.

  Raises:
    KeyError: If given column is not present in the table.
  """
  column_idx = None
  for idx, column in enumerate(table.header.columns):
    if column.name == column_name:
      column_idx = idx
      break

  if column_idx is None:
    raise KeyError("Column '{}' not found".format(column_name))

  for row in table.rows:
    yield row.values[column_idx]


def _Truncate(
    table: osquery_pb2.OsqueryTable, row_count: int
) -> osquery_pb2.OsqueryTable:
  """Returns a fresh table with the first few rows of the original one.

  Truncate doesn't modify the original table.

  Args:
    table: The table to truncate.
    row_count: The number of rows to keep in the truncated table

  Returns:
    New OsqueryTable object with maximum row_count rows.
  """
  result = osquery_pb2.OsqueryTable()

  result.query = table.query
  result.header.CopyFrom(table.header)
  result.rows.extend(table.rows[:row_count])

  return result


def _GetTruncatedTable(
    responses: list[osquery_pb2.OsqueryResult],
) -> osquery_pb2.OsqueryTable:
  """Constructs a truncated OsqueryTable.

  Constructs an OsqueryTable by extracting the first TRUNCATED_ROW_COUNT rows
  from the tables contained in the given OsqueryResult list.

  Args:
    responses: List of OsqueryResult elements from which to construct the
      truncated table.

  Returns:
    A truncated OsqueryTable.
  """
  # TODO(hanuszczak): This whole function looks very suspicious and looks like
  # a good candidate for refactoring.
  if not responses:
    return osquery_pb2.OsqueryTable()

  tables = [response.table for response in responses]

  result = _Truncate(tables[0], TRUNCATED_ROW_COUNT)

  for table in tables[1:]:
    to_add = TRUNCATED_ROW_COUNT - len(result.rows)
    if to_add == 0:
      break

    result.rows.extend(table.rows[:to_add])
  return result


def _ExtractFileInfo(
    result: rdf_flow_objects.FlowResult,
) -> rdf_server_osquery.OsqueryCollectedFile:
  if not isinstance(result.payload, rdf_client_fs.StatEntry):
    raise _ResultNotRelevantError

  stat_entry = result.payload
  return rdf_server_osquery.OsqueryCollectedFile(stat_entry=stat_entry)


class _ResultNotRelevantError(ValueError):
  pass


class FileCollectionLimitsExceeded(flow_base.FlowError):
  pass


class _UniquePathGenerator:
  """Ensures no duplicate paths are generated for the archive."""

  def __init__(self):
    self.path_to_count = {}

  def GeneratePath(self, pathspec: rdf_paths.PathSpec) -> str:
    target_path = "osquery_collected_files/"
    target_path += self._GetClientPath(pathspec)
    return target_path + self._GetUniqueSuffix(target_path)

  def _GetUniqueSuffix(self, path: str) -> str:
    times_used_before = self.path_to_count.get(path, 0)
    self.path_to_count[path] = times_used_before + 1

    if times_used_before > 0:
      return f"-{times_used_before}"
    else:
      return ""

  @staticmethod
  def _GetClientPath(pathspec: rdf_paths.PathSpec) -> str:
    path_info = rdf_objects.PathInfo.FromPathSpec(pathspec)
    return "/".join(path_info.components)


class OsqueryFlow(
    flow_base.FlowBase[
        osquery_pb2.OsqueryFlowArgs,
        osquery_pb2.OsqueryStore,
        osquery_pb2.OsqueryProgress,
    ]
):
  """A flow mixin wrapping the osquery client action."""

  friendly_name = "Osquery"
  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_server_osquery.OsqueryFlowArgs
  progress_type = rdf_osquery.OsqueryProgress
  result_types = (rdf_osquery.OsqueryResult,)

  proto_args_type = osquery_pb2.OsqueryFlowArgs
  proto_result_types = (osquery_pb2.OsqueryResult, jobs_pb2.StatEntry)
  proto_progress_type = osquery_pb2.OsqueryProgress
  proto_store_type = osquery_pb2.OsqueryStore

  only_protos_allowed = True

  def _UpdateProgressWithError(self, error_message: str) -> None:
    self.progress.error_message = error_message
    self.progress.ClearField("partial_table")
    self.progress.ClearField("total_row_count")

  def _UpdateProgress(
      self,
      responses: list[osquery_pb2.OsqueryResult],
  ) -> None:
    self.progress.ClearField("error_message")
    self.progress.partial_table.CopyFrom(_GetTruncatedTable(responses))
    self.progress.total_row_count = _GetTotalRowCount(responses)

  def _GetPathSpecsToCollect(
      self,
      responses: list[osquery_pb2.OsqueryResult],
  ) -> list[jobs_pb2.PathSpec]:
    if not self.proto_args.file_collection_columns:
      return []

    total_row_count = _GetTotalRowCount(responses)
    if total_row_count == 0:
      return []
    if total_row_count > FILE_COLLECTION_MAX_ROWS:
      message = (
          f"Requested file collection on a table with {total_row_count} "
          f"rows, but the limit is {FILE_COLLECTION_MAX_ROWS} rows."
      )
      self._UpdateProgressWithError(message)
      raise FileCollectionLimitsExceeded(message)

    file_names = []
    for osquery_result in responses:
      for column in self.proto_args.file_collection_columns:
        try:
          file_names.extend(_GetColumn(osquery_result.table, column))
        except KeyError:
          self._UpdateProgressWithError(
              f"No such column '{column}' to collect files from."
          )
          raise

    return [
        jobs_pb2.PathSpec(
            path=file_name, pathtype=jobs_pb2.PathSpec.PathType.OS
        )
        for file_name in file_names
    ]

  def _FileCollectionFromColumns(
      self,
      responses: list[osquery_pb2.OsqueryResult],
  ) -> None:
    pathspecs = self._GetPathSpecsToCollect(responses)

    for pathspec in pathspecs:
      request = jobs_pb2.GetFileStatRequest(pathspec=pathspec)
      self.CallClientProto(
          server_stubs.GetFileStat,
          request,
          next_state=self._StatForFileArrived.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def _StatForFileArrived(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      # TODO(user): Take note of this and report to the user with other
      # flow results, instead of failing the flow.
      raise flow_base.FlowError(
          f"Error when attempted to stat file: {responses.status}."
      )

    if len(responses) != 1:
      raise ValueError(
          f"Response from stat has length {len(responses)}, instead of 1."
      )

    stat_entry_any = list(responses)[0]
    stat_entry = jobs_pb2.StatEntry()
    stat_entry.ParseFromString(stat_entry_any.value)

    if stat_entry.st_size > FILE_COLLECTION_MAX_SINGLE_FILE_BYTES:
      # TODO(user): Report to the user with other flow results instead of
      # failing the flow.
      file_path = stat_entry.pathspec.path
      message = (
          f"File with path {file_path} is too big: {stat_entry.st_size} "
          f"bytes when the limit is {FILE_COLLECTION_MAX_SINGLE_FILE_BYTES} "
          "bytes."
      )
      self._UpdateProgressWithError(message)
      raise flow_base.FlowError(message)

    next_total_size = self.store.total_collected_bytes + stat_entry.st_size
    if next_total_size > FILE_COLLECTION_MAX_TOTAL_BYTES:
      # TODO(user): Consider reporting to the user and giving the
      # collected files so far and the other results.
      message = (
          "Files for collection exceed the total size "
          f"limit of {FILE_COLLECTION_MAX_TOTAL_BYTES} bytes."
      )
      self._UpdateProgressWithError(message)
      raise flow_base.FlowError(message)

    self.CallFlowProto(
        transfer.MultiGetFile.__name__,
        flow_args=flows_pb2.MultiGetFileArgs(pathspecs=[stat_entry.pathspec]),
        next_state=self.ProcessCollectedFile.__name__,
    )

  def Start(self):
    if (
        len(self.proto_args.file_collection_columns)
        > FILE_COLLECTION_MAX_COLUMNS
    ):
      message = (
          "Requested file collection for "
          f"{len(self.proto_args.file_collection_columns)} columns, "
          f"but the limit is {FILE_COLLECTION_MAX_COLUMNS} columns."
      )
      self._UpdateProgressWithError(message)
      raise FileCollectionLimitsExceeded(message)

    if (
        self.proto_args.configuration_path
        and self.proto_args.configuration_content
    ):
      raise ValueError(
          "Configuration path and configuration content are mutually exclusive."
      )

    if self.proto_args.configuration_content:
      try:
        _ = json.loads(self.proto_args.configuration_content)
      except json.JSONDecodeError as json_error:
        raise ValueError(
            "Configuration content is not valid JSON"
        ) from json_error

    action_args = osquery_pb2.OsqueryArgs(
        query=self.proto_args.query,
        timeout_millis=self.proto_args.timeout_millis,
        configuration_path=self.proto_args.configuration_path,
        configuration_content=self.proto_args.configuration_content,
    )

    self.CallClientProto(
        server_stubs.Osquery,
        action_args,
        next_state=self.Process.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def Process(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      status = responses.status
      assert status is not None, "Failed response status must be set."

      message = f"{status.error_message}: {status.backtrace}"
      self._UpdateProgressWithError(message)

      raise flow_base.FlowError(status)

    unpacked_responses = []
    for response_any in responses:
      response = osquery_pb2.OsqueryResult()
      response.ParseFromString(response_any.value)
      unpacked_responses.append(response)

    self._UpdateProgress(unpacked_responses)

    for response in unpacked_responses:
      # Older agent versions might still send empty tables, so we simply ignore
      # such.
      if not response.table.rows:
        continue

      self.SendReplyProto(response)

    self._FileCollectionFromColumns(unpacked_responses)

  def GetProgress(self) -> rdf_osquery.OsqueryProgress:
    return mig_osquery.ToRDFOsqueryProgress(self.progress)

  def GetProgressProto(self) -> osquery_pb2.OsqueryProgress:
    return self.progress

  @flow_base.UseProto2AnyResponses
  def ProcessCollectedFile(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    stat_entry_any = responses.First()
    if stat_entry_any:
      stat_entry = jobs_pb2.StatEntry()
      stat_entry.ParseFromString(stat_entry_any.value)
      self.SendReplyProto(stat_entry)

  def GetFilesArchiveMappings(
      self,
      flow_results: Iterator[rdf_flow_objects.FlowResult],
  ) -> Iterator[flow_base.ClientPathArchiveMapping]:
    target_path_generator = _UniquePathGenerator()

    for result in flow_results:
      try:
        osquery_file = _ExtractFileInfo(result)
      except _ResultNotRelevantError:
        continue

      client_path = db.ClientPath.FromPathSpec(
          self.client_id, osquery_file.stat_entry.pathspec
      )
      target_path = target_path_generator.GeneratePath(
          osquery_file.stat_entry.pathspec
      )

      yield flow_base.ClientPathArchiveMapping(
          client_path=client_path, archive_path=target_path
      )
