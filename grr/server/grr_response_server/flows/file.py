#!/usr/bin/env python
"""Flows to collect file contents and metadata."""

from collections.abc import Iterable
from typing import Optional

from google.protobuf import any_pb2
from grr_response_core import config
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server.databases import db
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer


def _CollectionLevelToStopAt(
    collection_level: flows_pb2.CollectFilesByKnownPathArgs.CollectionLevel,
) -> transfer.MultiGetFileArgs.StopAt:
  """Converts a CollectionLevel to an equivalent StopAt enum."""
  if (
      collection_level
      == flows_pb2.CollectFilesByKnownPathArgs.CollectionLevel.STAT
  ):
    return transfer.MultiGetFileArgs.StopAt.STAT
  elif (
      collection_level
      == flows_pb2.CollectFilesByKnownPathArgs.CollectionLevel.HASH
  ):
    return transfer.MultiGetFileArgs.StopAt.HASH
  else:
    return transfer.MultiGetFileArgs.StopAt.NOTHING


class CollectFilesByKnownPath(
    flow_base.FlowBase[
        flows_pb2.CollectFilesByKnownPathArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.CollectFilesByKnownPathProgress,
    ]
):
  """Fetches specified absolute path file contents."""

  friendly_name = "File contents by exact path"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  args_type = rdf_file_finder.CollectFilesByKnownPathArgs
  result_types = (rdf_file_finder.CollectFilesByKnownPathResult,)
  progress_type = rdf_file_finder.CollectFilesByKnownPathProgress

  proto_args_type = flows_pb2.CollectFilesByKnownPathArgs
  proto_result_types = (flows_pb2.CollectFilesByKnownPathResult,)
  proto_progress_type = flows_pb2.CollectFilesByKnownPathProgress

  only_protos_allowed = True

  def GetProgress(self) -> rdf_file_finder.CollectFilesByKnownPathProgress:
    return mig_file_finder.ToRDFCollectFilesByKnownPathProgress(self.progress)

  def GetProgressProto(self) -> flows_pb2.CollectFilesByKnownPathProgress:
    return self.progress

  def _NextStateForCollectionLevel(
      self,
      collection_level: flows_pb2.CollectFilesByKnownPathArgs.CollectionLevel,
  ) -> str:
    if (
        collection_level
        == flows_pb2.CollectFilesByKnownPathArgs.CollectionLevel.STAT
    ):
      return self.ReceiveFetchedFileStats.__name__
    elif (
        collection_level
        == flows_pb2.CollectFilesByKnownPathArgs.CollectionLevel.HASH
    ):
      return self.ReceiveFetchedFileHashes.__name__
    else:
      return self.ReceiveFetchedFileContents.__name__

  def _ReportProgress(
      self, paths: Iterable[str], pathtype: jobs_pb2.PathSpec.PathType
  ) -> None:
    for path in paths:
      result = flows_pb2.CollectFilesByKnownPathResult(
          stat=jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(path=path, pathtype=pathtype)
          ),
          status=flows_pb2.CollectFilesByKnownPathResult.Status.IN_PROGRESS,
      )
      self.SendReplyProto(result)

  def Start(self):
    stop_at = _CollectionLevelToStopAt(self.proto_args.collection_level)
    unique_paths = set(list(path for path in self.proto_args.paths))
    mgf_args = flows_pb2.MultiGetFileArgs(
        pathspecs=[
            jobs_pb2.PathSpec(path=path, pathtype=jobs_pb2.PathSpec.PathType.OS)
            for path in unique_paths
        ],
        stop_at=stop_at,
    )
    self.progress.num_in_progress = len(unique_paths)
    self._ReportProgress(unique_paths, jobs_pb2.PathSpec.PathType.OS)

    self.CallFlowProto(
        transfer.MultiGetFile.__name__,
        flow_args=mgf_args,
        next_state=self._NextStateForCollectionLevel(
            self.proto_args.collection_level
        ),
        request_data={"requested_paths": unique_paths},
    )

  def _IsRetryable(self, is_fallback: bool) -> bool:
    return bool(self.client_os == "Windows" and not is_fallback)

  def _RetryPaths(
      self,
      paths: Iterable[str],
  ) -> None:
    fallback_type = config.CONFIG["Server.raw_filesystem_access_pathtype"]
    mgf_args = flows_pb2.MultiGetFileArgs(
        pathspecs=[
            jobs_pb2.PathSpec(path=path, pathtype=fallback_type)
            for path in paths
        ],
        stop_at=_CollectionLevelToStopAt(self.proto_args.collection_level),
    )
    self._ReportProgress(paths, fallback_type)
    self.CallFlowProto(
        transfer.MultiGetFile.__name__,
        flow_args=mgf_args,
        next_state=self._NextStateForCollectionLevel(
            self.proto_args.collection_level
        ),
        request_data={
            "requested_paths": paths,
            "is_fallback": True,
        },
    )

  @flow_base.UseProto2AnyResponses
  def ReceiveFetchedFileStats(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ):
    """This method will be called after MultiGetFile has fetched file stats."""
    if not responses.success:
      if responses.status and responses.status.error_message:
        details = responses.status.error_message
      else:
        details = responses.status
      self.Log(f"Failed to fetch file stats: {details}")

    remaining_paths = set(responses.request_data["requested_paths"])

    for response_any in responses:
      response = jobs_pb2.StatEntry()
      response.ParseFromString(response_any.value)

      remaining_paths.remove(response.pathspec.path)
      self.progress.num_in_progress -= 1
      self.progress.num_collected += 1
      result = flows_pb2.CollectFilesByKnownPathResult(
          stat=response,
          status=flows_pb2.CollectFilesByKnownPathResult.Status.COLLECTED,
      )
      self.SendReplyProto(result)

    requested_paths = responses.request_data["requested_paths"]
    if len(requested_paths) == len(list(responses)):
      return  # All paths succeeded.

    # Some paths failed.
    is_fallback = bool("is_fallback" in responses.request_data)
    if self._IsRetryable(is_fallback):
      self.progress.num_raw_fs_access_retries += len(remaining_paths)
      self._RetryPaths(remaining_paths)
    else:
      for path in remaining_paths:
        self.progress.num_in_progress -= 1
        self.progress.num_failed += 1

        result = flows_pb2.CollectFilesByKnownPathResult()
        result.status = flows_pb2.CollectFilesByKnownPathResult.Status.FAILED
        result.stat.pathspec.path = path
        if is_fallback:
          result.stat.pathspec.pathtype = config.CONFIG[
              "Server.raw_filesystem_access_pathtype"
          ]
        else:
          result.stat.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

        self.SendReplyProto(result)

  def _GetHashFromFilestore(
      self, pathspec: jobs_pb2.PathSpec
  ) -> Optional[jobs_pb2.Hash]:
    client_path = db.ClientPath.FromPathSpec(
        self.client_id, mig_paths.ToRDFPathSpec(pathspec)
    )
    # First we need to check if the filestore has the hash, before reporting
    # the success. That is stored in the VFS and not reported by
    # `MultiGetFile`. FlowIDs are not stored in the VFS, so we can't use
    # that to grab the specific version of the file we want. So, for now, we
    # just grab the latest version available.
    # TODO: Once we have a way to grab the flow-specific
    # version of the file, we should use that instead of the latest version.
    history = data_store.REL_DB.ReadPathInfoHistory(
        self.client_id, client_path.path_type, client_path.components
    )
    if not history:
      return None
    latest_path_info = history[-1]
    return latest_path_info.hash_entry

  @flow_base.UseProto2AnyResponses
  def ReceiveFetchedFileHashes(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ):
    """This method will be called after MultiGetFile has fetched file hashes."""
    if not responses.success:
      if responses.status and responses.status.error_message:
        details = responses.status.error_message
      else:
        details = responses.status
      self.Log(f"Failed to fetch file hashes: {details}")

    remaining_paths = set(responses.request_data["requested_paths"])

    for response_any in responses:
      response = jobs_pb2.StatEntry()
      response.ParseFromString(response_any.value)

      # MultiGetFile doesn't return the hash directly, but rather saves it
      # in the filestore. So, we need to check there to see if we have the
      # hash before reporting the success.
      hash_entry = self._GetHashFromFilestore(response.pathspec)
      if hash_entry:
        remaining_paths.remove(response.pathspec.path)
        self.progress.num_in_progress -= 1
        self.progress.num_collected += 1
        result = flows_pb2.CollectFilesByKnownPathResult(
            stat=response,
            hash=hash_entry,
            status=flows_pb2.CollectFilesByKnownPathResult.Status.COLLECTED,
        )
        self.SendReplyProto(result)

    requested_paths = responses.request_data["requested_paths"]
    if len(requested_paths) == len(list(responses)):
      return  # All paths succeeded.

    # Remaining paths weren't successfully fetched.
    is_fallback = "is_fallback" in responses.request_data
    if self._IsRetryable(is_fallback):
      self.progress.num_raw_fs_access_retries += len(remaining_paths)
      self._RetryPaths(remaining_paths)
    else:
      for path in remaining_paths:
        self.progress.num_in_progress -= 1
        self.progress.num_failed += 1

        result = flows_pb2.CollectFilesByKnownPathResult()
        result.status = flows_pb2.CollectFilesByKnownPathResult.Status.FAILED
        result.stat.pathspec.path = path
        if is_fallback:
          result.stat.pathspec.pathtype = config.CONFIG[
              "Server.raw_filesystem_access_pathtype"
          ]
        else:
          result.stat.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

        self.SendReplyProto(result)

  def _HasFileContents(self, pathspec: jobs_pb2.PathSpec) -> bool:
    client_path = db.ClientPath.FromPathSpec(
        self.client_id, mig_paths.ToRDFPathSpec(pathspec)
    )
    try:
      file_store.OpenFile(client_path)
      return True
    except file_store.FileHasNoContentError:
      return False

  @flow_base.UseProto2AnyResponses
  def ReceiveFetchedFileContents(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ):
    """This method will be called after MultiGetFile has fetched file contents."""
    if not responses.success:
      if responses.status and responses.status.error_message:
        details = responses.status.error_message
      else:
        details = responses.status
      self.Log(f"Failed to fetch file contents: {details}")

    remaining_paths = set(responses.request_data["requested_paths"])

    for response_any in responses:
      response = jobs_pb2.StatEntry()
      response.ParseFromString(response_any.value)

      # MultiGetFile doesn't return the hash directly, but rather saves it
      # in the filestore. So, we need to check there to see if we have the
      # hash before reporting the success.
      hash_entry = self._GetHashFromFilestore(response.pathspec)
      has_file_contents = self._HasFileContents(response.pathspec)
      if hash_entry and has_file_contents:
        remaining_paths.remove(response.pathspec.path)
        self.progress.num_in_progress -= 1
        self.progress.num_collected += 1
        result = flows_pb2.CollectFilesByKnownPathResult(
            stat=response,
            hash=hash_entry,
            status=flows_pb2.CollectFilesByKnownPathResult.Status.COLLECTED,
        )
        self.SendReplyProto(result)

    requested_paths = responses.request_data["requested_paths"]
    if len(requested_paths) == len(list(responses)):
      return  # All paths succeeded.

    # Remaining paths weren't successfully fetched.
    is_fallback = "is_fallback" in responses.request_data
    if self._IsRetryable(is_fallback):
      self.progress.num_raw_fs_access_retries += len(remaining_paths)
      self._RetryPaths(remaining_paths)
    else:
      for path in remaining_paths:
        self.progress.num_in_progress -= 1
        self.progress.num_failed += 1

        result = flows_pb2.CollectFilesByKnownPathResult()
        result.status = flows_pb2.CollectFilesByKnownPathResult.Status.FAILED
        result.stat.pathspec.path = path
        if is_fallback:
          result.stat.pathspec.pathtype = config.CONFIG[
              "Server.raw_filesystem_access_pathtype"
          ]
        else:
          result.stat.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

        self.SendReplyProto(result)


class CollectMultipleFiles(
    flow_base.FlowBase[
        flows_pb2.CollectMultipleFilesArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.CollectMultipleFilesProgress,
    ]
):
  """Fetches contents of files by searching for path expressions."""

  friendly_name = "Collect multiple files"
  category = "/Filesystem/"
  args_type = rdf_file_finder.CollectMultipleFilesArgs
  result_types = (rdf_file_finder.CollectMultipleFilesResult,)
  progress_type = rdf_file_finder.CollectMultipleFilesProgress
  behaviours = flow_base.BEHAVIOUR_DEBUG

  proto_args_type = flows_pb2.CollectMultipleFilesArgs
  proto_result_types = (flows_pb2.CollectMultipleFilesResult,)
  proto_progress_type = flows_pb2.CollectMultipleFilesProgress
  only_protos_allowed = True

  MAX_FILE_SIZE = 1024 * 1024 * 1024 * 10  # 10GiB

  def GetProgress(self) -> rdf_file_finder.CollectMultipleFilesProgress:
    return mig_file_finder.ToRDFCollectMultipleFilesProgress(self.progress)

  def GetProgressProto(self) -> flows_pb2.CollectMultipleFilesProgress:
    return self.progress

  def _BuildConditionsFromArgs(
      self,
  ) -> list[flows_pb2.FileFinderCondition]:
    return BuildClientFileFinderConditions(
        modification_time=self.proto_args.modification_time
        if self.proto_args.HasField("modification_time")
        else None,
        access_time=self.proto_args.access_time
        if self.proto_args.HasField("access_time")
        else None,
        inode_change_time=self.proto_args.inode_change_time
        if self.proto_args.HasField("inode_change_time")
        else None,
        size=self.proto_args.size if self.proto_args.HasField("size") else None,
        ext_flags=self.proto_args.ext_flags
        if self.proto_args.HasField("ext_flags")
        else None,
        contents_regex_match=self.proto_args.contents_regex_match
        if self.proto_args.HasField("contents_regex_match")
        else None,
        contents_literal_match=self.proto_args.contents_literal_match
        if self.proto_args.HasField("contents_literal_match")
        else None,
    )

  def Start(self):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    """See base class."""
    self.progress = flows_pb2.CollectMultipleFilesProgress(
        num_found=0,
        num_in_progress=0,
        num_raw_fs_access_retries=0,
        num_collected=0,
        num_failed=0,
    )

    file_finder_args = flows_pb2.FileFinderArgs(
        paths=self.proto_args.path_expressions,
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        conditions=self._BuildConditionsFromArgs(),
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
    )

    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessStatResponses.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def ProcessStatResponses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      if responses.status and responses.status.error_message:
        details = responses.status.error_message
      else:
        details = responses.status
      raise flow_base.FlowError(f"Failed while stat'ing files: {details}")

    if not list(responses):
      self.Log("No files were found with this criteria.")
      return

    self.progress.num_found += len(responses)

    paths = set()
    for response_any in responses:
      ff_result = flows_pb2.FileFinderResult()
      ff_result.ParseFromString(response_any.value)
      paths.add(ff_result.stat_entry.pathspec.path)

    conditions = self._BuildConditionsFromArgs()
    file_finder_args = flows_pb2.FileFinderArgs(
        paths=paths,
        pathtype=jobs_pb2.PathSpec.PathType.OS,
        conditions=conditions,
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
    )
    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessCollectedResponses.__name__,
        request_data={"requested_paths": paths},
    )

    self.progress.num_in_progress += len(paths)

  @flow_base.UseProto2AnyResponses
  def ProcessCollectedResponses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      if responses.status and responses.status.error_message:
        details = responses.status.error_message
      else:
        details = responses.status
      self.Log(f"Failed while hashing files: {details}")

    requested_paths = responses.request_data["requested_paths"]

    for response_any in responses:
      ff_result = flows_pb2.FileFinderResult()
      ff_result.ParseFromString(response_any.value)
      path = ff_result.stat_entry.pathspec.path
      self.progress.num_in_progress -= 1
      self.progress.num_collected += 1
      requested_paths.discard(path)

      result = flows_pb2.CollectMultipleFilesResult(
          stat=ff_result.stat_entry,
          hash=ff_result.hash_entry,
          status=flows_pb2.CollectMultipleFilesResult.Status.COLLECTED,
      )
      self.SendReplyProto(result)

    # If some of the requested paths were not returned, fallback once.
    is_fallback = "is_fallback" in responses.request_data
    fallback_type = config.CONFIG["Server.raw_filesystem_access_pathtype"]
    if requested_paths and self.client_os == "Windows" and not is_fallback:
      conditions = self._BuildConditionsFromArgs()
      file_finder_args = flows_pb2.FileFinderArgs(
          paths=requested_paths,
          pathtype=fallback_type,
          conditions=conditions,
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
          ),
      )
      self.CallFlowProto(
          file_finder.ClientFileFinder.__name__,
          flow_args=file_finder_args,
          next_state=self.ProcessCollectedResponses.__name__,
          request_data={
              "requested_paths": requested_paths,
              "is_fallback": True,
          },
      )
      self.progress.num_raw_fs_access_retries += len(requested_paths)
      return

    for path in requested_paths:
      error_description = (
          f"File {path} could not be fetched ({is_fallback=}), check flow logs"
          " for more details."
      )
      path_type = (
          jobs_pb2.PathSpec.PathType.OS if not is_fallback else fallback_type
      )
      result = flows_pb2.CollectMultipleFilesResult(
          stat=jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(path=path, pathtype=path_type)
          ),
          error=error_description,
          status=flows_pb2.CollectMultipleFilesResult.Status.FAILED,
      )
      self.SendReplyProto(result)
      self.progress.num_failed += 1

    # We're done, no more retries.
    self.progress.num_in_progress = 0
    if self.progress.num_failed and not self.progress.num_collected:
      raise flow_base.FlowError(
          "Failed to collect any files, failed count:"
          f" {self.progress.num_failed}, collected count:"
          f" {self.progress.num_collected}"
      )


class StatMultipleFiles(
    flow_base.FlowBase[
        flows_pb2.StatMultipleFilesArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Fetches file stats by searching for path expressions."""

  friendly_name = "Collect file stats"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_file_finder.StatMultipleFilesArgs
  result_types = (rdf_client_fs.StatEntry,)
  proto_args_type = flows_pb2.StatMultipleFilesArgs
  proto_result_types = (jobs_pb2.StatEntry,)
  only_protos_allowed = True

  def Start(self):
    conditions = BuildClientFileFinderConditions(
        modification_time=self.proto_args.modification_time
        if self.proto_args.HasField("modification_time")
        else None,
        access_time=self.proto_args.access_time
        if self.proto_args.HasField("access_time")
        else None,
        inode_change_time=self.proto_args.inode_change_time
        if self.proto_args.HasField("inode_change_time")
        else None,
        size=self.proto_args.size if self.proto_args.HasField("size") else None,
        ext_flags=self.proto_args.ext_flags
        if self.proto_args.HasField("ext_flags")
        else None,
        contents_regex_match=self.proto_args.contents_regex_match
        if self.proto_args.HasField("contents_regex_match")
        else None,
        contents_literal_match=self.proto_args.contents_literal_match
        if self.proto_args.HasField("contents_literal_match")
        else None,
    )

    file_finder_args = flows_pb2.FileFinderArgs()
    file_finder_args.paths.extend(self.proto_args.path_expressions)
    file_finder_args.pathtype = jobs_pb2.PathSpec.PathType.OS
    file_finder_args.conditions.extend(conditions)
    file_finder_args.action.CopyFrom(
        flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        )
    )

    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessResponses.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def ProcessResponses(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    for response_any in responses:
      ff_result = flows_pb2.FileFinderResult()
      ff_result.ParseFromString(response_any.value)
      self.SendReplyProto(ff_result.stat_entry)


class HashMultipleFiles(
    flow_base.FlowBase[
        flows_pb2.HashMultipleFilesArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.HashMultipleFilesProgress,
    ]
):
  """Fetches file hashes and stats by searching for path expressions."""

  friendly_name = "Collect file hashes"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_file_finder.HashMultipleFilesArgs
  result_types = (rdf_file_finder.CollectMultipleFilesResult,)
  progress_type = rdf_file_finder.HashMultipleFilesProgress
  proto_args_type = flows_pb2.HashMultipleFilesArgs
  proto_result_types = (flows_pb2.CollectMultipleFilesResult,)
  proto_progress_type = flows_pb2.HashMultipleFilesProgress
  only_protos_allowed = True

  MAX_FILE_SIZE = 1024 * 1024 * 1024 * 10  # 10GiB

  def GetProgress(self) -> rdf_file_finder.HashMultipleFilesProgress:
    return mig_file_finder.ToRDFHashMultipleFilesProgress(self.progress)

  def GetProgressProto(self) -> flows_pb2.HashMultipleFilesProgress:
    return self.progress

  def _BuildConditionsFromArgs(
      self,
  ) -> list[flows_pb2.FileFinderCondition]:
    return BuildClientFileFinderConditions(
        modification_time=self.proto_args.modification_time
        if self.proto_args.HasField("modification_time")
        else None,
        access_time=self.proto_args.access_time
        if self.proto_args.HasField("access_time")
        else None,
        inode_change_time=self.proto_args.inode_change_time
        if self.proto_args.HasField("inode_change_time")
        else None,
        size=self.proto_args.size if self.proto_args.HasField("size") else None,
        ext_flags=self.proto_args.ext_flags
        if self.proto_args.HasField("ext_flags")
        else None,
        contents_regex_match=self.proto_args.contents_regex_match
        if self.proto_args.HasField("contents_regex_match")
        else None,
        contents_literal_match=self.proto_args.contents_literal_match
        if self.proto_args.HasField("contents_literal_match")
        else None,
    )

  def Start(self):
    """See base class."""
    self.progress = flows_pb2.HashMultipleFilesProgress(
        num_found=0,
        num_in_progress=0,
        num_raw_fs_access_retries=0,
        num_hashed=0,
        num_failed=0,
    )
    file_finder_args = flows_pb2.FileFinderArgs(
        paths=self.proto_args.path_expressions,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        conditions=self._BuildConditionsFromArgs(),
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
    )
    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessStatResponses.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def ProcessStatResponses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      if responses.status and responses.status.error_message:
        details = responses.status.error_message
      else:
        details = responses.status
      raise flow_base.FlowError(f"Failed while stat'ing files: {details}")

    if not list(responses):
      self.Log("No files were found with this criteria.")
      return

    self.progress.num_found += len(responses)

    paths = set()
    for response_any in responses:
      ff_result = flows_pb2.FileFinderResult()
      ff_result.ParseFromString(response_any.value)
      paths.add(ff_result.stat_entry.pathspec.path)
    conditions = self._BuildConditionsFromArgs()
    file_finder_args = flows_pb2.FileFinderArgs(
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        conditions=conditions,
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.HASH
        ),
    )
    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessHashResponses.__name__,
        request_data={"requested_paths": paths},
    )

    self.progress.num_in_progress += len(paths)

  @flow_base.UseProto2AnyResponses
  def ProcessHashResponses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      if responses.status and responses.status.error_message:
        details = responses.status.error_message
      else:
        details = responses.status
      self.Log(f"Failed while hashing files: {details}")

    requested_paths = responses.request_data["requested_paths"]

    for response_any in responses:
      ff_result = flows_pb2.FileFinderResult()
      ff_result.ParseFromString(response_any.value)
      path = ff_result.stat_entry.pathspec.path
      self.progress.num_in_progress -= 1
      self.progress.num_hashed += 1
      requested_paths.discard(path)

      result = flows_pb2.CollectMultipleFilesResult(
          stat=ff_result.stat_entry,
          hash=ff_result.hash_entry,
          status=flows_pb2.CollectMultipleFilesResult.Status.COLLECTED,
      )
      self.SendReplyProto(result)

    # If some of the requested paths were not returned, fallback once.
    is_fallback = "is_fallback" in responses.request_data
    fallback_type = config.CONFIG["Server.raw_filesystem_access_pathtype"]
    if requested_paths and self.client_os == "Windows" and not is_fallback:
      conditions = self._BuildConditionsFromArgs()
      file_finder_args = flows_pb2.FileFinderArgs(
          paths=requested_paths,
          pathtype=fallback_type,
          conditions=conditions,
          action=flows_pb2.FileFinderAction(
              action_type=flows_pb2.FileFinderAction.Action.HASH
          ),
      )
      self.CallFlowProto(
          file_finder.ClientFileFinder.__name__,
          flow_args=file_finder_args,
          next_state=self.ProcessHashResponses.__name__,
          request_data={
              "requested_paths": requested_paths,
              "is_fallback": True,
          },
      )
      self.progress.num_raw_fs_access_retries += len(requested_paths)
      return

    for path in requested_paths:
      error_description = (
          f"File {path} could not be fetched ({is_fallback=}), check flow logs"
          " for more details."
      )
      path_type = (
          jobs_pb2.PathSpec.PathType.OS if not is_fallback else fallback_type
      )
      result = flows_pb2.CollectMultipleFilesResult(
          stat=jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(path=path, pathtype=path_type)
          ),
          error=error_description,
          status=flows_pb2.CollectMultipleFilesResult.Status.FAILED,
      )
      self.SendReplyProto(result)
      self.progress.num_failed += 1

    # We're done, no more retries.
    self.progress.num_in_progress = 0
    if self.progress.num_failed and not self.progress.num_hashed:
      raise flow_base.FlowError(
          "Failed to hash any files, failed count:"
          f" {self.progress.num_failed}, hashed count:"
          f" {self.progress.num_hashed}"
      )


def BuildClientFileFinderConditions(
    modification_time: Optional[
        flows_pb2.FileFinderModificationTimeCondition
    ] = None,
    access_time: Optional[flows_pb2.FileFinderAccessTimeCondition] = None,
    inode_change_time: Optional[
        flows_pb2.FileFinderInodeChangeTimeCondition
    ] = None,
    size: Optional[flows_pb2.FileFinderSizeCondition] = None,
    ext_flags: Optional[flows_pb2.FileFinderExtFlagsCondition] = None,
    contents_regex_match: Optional[
        flows_pb2.FileFinderContentsRegexMatchCondition
    ] = None,
    contents_literal_match: Optional[
        flows_pb2.FileFinderContentsLiteralMatchCondition
    ] = None,
) -> list[flows_pb2.FileFinderCondition]:
  """Constructs the list of conditions to be applied to ClientFileFinder flow.

  Args:
    modification_time: Min/max last modification time of the file(s).
    access_time: Min/max last access time of the file(s).
    inode_change_time: Min/max last inode time of the file(s).
    size: Min/max file size.
    ext_flags: Linux and/or macOS file flags.
    contents_regex_match: regex rule to match in the file contents.
    contents_literal_match: string literal to match in the file contents.

  Returns:
    List of file conditions for ClientFileFinder flow.
  """
  conditions = []

  if modification_time is not None:
    conditions.append(
        flows_pb2.FileFinderCondition(
            condition_type=flows_pb2.FileFinderCondition.Type.MODIFICATION_TIME,
            modification_time=modification_time,
        )
    )

  if access_time is not None:
    conditions.append(
        flows_pb2.FileFinderCondition(
            condition_type=flows_pb2.FileFinderCondition.Type.ACCESS_TIME,
            access_time=access_time,
        )
    )

  if inode_change_time is not None:
    conditions.append(
        flows_pb2.FileFinderCondition(
            condition_type=flows_pb2.FileFinderCondition.Type.INODE_CHANGE_TIME,
            inode_change_time=inode_change_time,
        )
    )

  if size is not None:
    conditions.append(
        flows_pb2.FileFinderCondition(
            condition_type=flows_pb2.FileFinderCondition.Type.SIZE,
            size=size,
        )
    )

  if ext_flags is not None:
    conditions.append(
        flows_pb2.FileFinderCondition(
            condition_type=flows_pb2.FileFinderCondition.Type.EXT_FLAGS,
            ext_flags=ext_flags,
        )
    )

  if contents_regex_match is not None:
    conditions.append(
        flows_pb2.FileFinderCondition(
            condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH,
            contents_regex_match=contents_regex_match,
        )
    )

  if contents_literal_match is not None:
    conditions.append(
        flows_pb2.FileFinderCondition(
            condition_type=flows_pb2.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
            contents_literal_match=contents_literal_match,
        )
    )

  return conditions
