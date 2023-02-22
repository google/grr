#!/usr/bin/env python
"""A module with flow class calling the osquery client action."""

from typing import Any, Iterable, Iterator, List

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.rdfvalues import paths as rdf_paths
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


def _GetTotalRowCount(responses: Iterable[rdf_osquery.OsqueryResult]) -> int:
  get_row_lengths = lambda response: len(response.table.rows)
  row_lengths = map(get_row_lengths, responses)
  return sum(row_lengths)


def _GetTruncatedTable(
    responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
) -> rdf_osquery.OsqueryTable:
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
    return rdf_osquery.OsqueryTable()

  tables = [response.table for response in responses]

  result = tables[0].Truncated(TRUNCATED_ROW_COUNT)

  for table in tables[1:]:
    to_add = TRUNCATED_ROW_COUNT - len(result.rows)
    if to_add == 0:
      break

    result.rows.Extend(table.rows[:to_add])
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


class OsqueryFlow(transfer.MultiGetFileLogic, flow_base.FlowBase):
  """A flow mixin wrapping the osquery client action."""

  friendly_name = "Osquery"
  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_server_osquery.OsqueryFlowArgs
  progress_type = rdf_osquery.OsqueryProgress
  result_types = (rdf_osquery.OsqueryResult,)

  def _UpdateProgressWithError(self, error_message: str) -> None:
    self.state.progress.error_message = error_message
    self.state.progress.partial_table = None
    self.state.progress.total_row_count = None

  def _UpdateProgress(
      self,
      responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
  ) -> None:
    self.state.progress.error_message = None
    self.state.progress.partial_table = _GetTruncatedTable(responses)
    self.state.progress.total_row_count = _GetTotalRowCount(responses)

  def _GetPathSpecsToCollect(
      self,
      responses: Iterable[rdf_osquery.OsqueryResult],
  ) -> List[rdf_paths.PathSpec]:
    if not self.args.file_collection_columns:
      return []

    total_row_count = _GetTotalRowCount(responses)
    if total_row_count == 0:
      return []
    if total_row_count > FILE_COLLECTION_MAX_ROWS:
      message = (f"Requested file collection on a table with {total_row_count} "
                 f"rows, but the limit is {FILE_COLLECTION_MAX_ROWS} rows.")
      self._UpdateProgressWithError(message)
      raise FileCollectionLimitsExceeded(message)

    file_names = []
    for osquery_result in responses:
      for column in self.args.file_collection_columns:
        try:
          file_names.extend(osquery_result.table.Column(column))
        except KeyError:
          self._UpdateProgressWithError(
              f"No such column '{column}' to collect files from.")
          raise

    return [rdf_paths.PathSpec.OS(path=file_name) for file_name in file_names]

  def _FileCollectionFromColumns(
      self,
      responses: Iterable[rdf_osquery.OsqueryResult],
  ) -> None:
    pathspecs = self._GetPathSpecsToCollect(responses)

    stub = server_stubs.GetFileStat
    for pathspec in pathspecs:
      request = rdf_client_action.GetFileStatRequest(pathspec=pathspec)
      self.CallClient(
          stub, request, next_state=self._StatForFileArrived.__name__)

  def _StatForFileArrived(
      self,
      responses: flow_responses.Responses[rdf_client_fs.StatEntry],
  ) -> None:
    if not responses.success:
      # TODO(user): Take note of this and report to the user with other
      # flow results, instead of failing the flow.
      raise flow_base.FlowError(
          f"Error when attempted to stat file: {responses.status}.")

    if len(responses) != 1:
      raise ValueError(
          f"Response from stat has length {len(responses)}, instead of 1.")

    stat_entry = list(responses)[0]

    if stat_entry.st_size > FILE_COLLECTION_MAX_SINGLE_FILE_BYTES:
      # TODO(user): Report to the user with other flow results instead of
      # failing the flow.
      file_path = stat_entry.pathspec.CollapsePath()
      message = (
          f"File with path {file_path} is too big: {stat_entry.st_size} "
          f"bytes when the limit is {FILE_COLLECTION_MAX_SINGLE_FILE_BYTES} "
          "bytes.")
      self._UpdateProgressWithError(message)
      raise flow_base.FlowError(message)

    next_total_size = self.state.total_collected_bytes + stat_entry.st_size
    if next_total_size > FILE_COLLECTION_MAX_TOTAL_BYTES:
      # TODO(user): Consider reporting to the user and giving the
      # collected files so far and the other results.
      message = ("Files for collection exceed the total size "
                 f"limit of {FILE_COLLECTION_MAX_TOTAL_BYTES} bytes.")
      self._UpdateProgressWithError(message)
      raise flow_base.FlowError(message)

    self.StartFileFetch(stat_entry.pathspec)

  def Start(self):
    super(OsqueryFlow,
          self).Start(file_size=FILE_COLLECTION_MAX_SINGLE_FILE_BYTES)
    self.state.progress = rdf_osquery.OsqueryProgress()

    if len(self.args.file_collection_columns) > FILE_COLLECTION_MAX_COLUMNS:
      message = ("Requested file collection for "
                 f"{len(self.args.file_collection_columns)} columns, "
                 f"but the limit is {FILE_COLLECTION_MAX_COLUMNS} columns.")
      self._UpdateProgressWithError(message)
      raise FileCollectionLimitsExceeded(message)

    self.state.path_to_count = {}
    self.state.total_collected_bytes = 0

    action_args = rdf_osquery.OsqueryArgs(
        query=self.args.query, timeout_millis=self.args.timeout_millis)
    self.CallClient(
        server_stubs.Osquery,
        request=action_args,
        next_state=self.Process.__name__)

  def Process(
      self,
      responses: flow_responses.Responses[rdf_osquery.OsqueryResult],
  ) -> None:
    if not responses.success:
      status = responses.status

      message = f"{status.error_message}: {status.backtrace}"
      self._UpdateProgressWithError(message)

      raise flow_base.FlowError(status)

    self._UpdateProgress(responses)

    for response in responses:
      # Older agent versions might still send empty tables, so we simply ignore
      # such.
      if not response.table.rows:
        continue

      self.SendReply(response)

    self._FileCollectionFromColumns(responses)

  def GetProgress(self) -> rdf_osquery.OsqueryProgress:
    return self.state.progress

  def ReceiveFetchedFile(self,
                         stat_entry: rdf_client_fs.StatEntry,
                         file_hash: rdf_crypto.Hash,
                         request_data: Any = None,
                         is_duplicate=False) -> None:
    del file_hash, request_data, is_duplicate  # Unused
    self.SendReply(stat_entry)

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

      client_path = db.ClientPath.FromPathSpec(self.client_id,
                                               osquery_file.stat_entry.pathspec)
      target_path = target_path_generator.GeneratePath(
          osquery_file.stat_entry.pathspec)

      yield flow_base.ClientPathArchiveMapping(
          client_path=client_path, archive_path=target_path)
