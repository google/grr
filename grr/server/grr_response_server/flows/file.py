#!/usr/bin/env python
"""Flows to collect file contents and metadata."""

from typing import Any, Mapping, Optional

from grr_response_core import config
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import flow_base
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects

_MAX_FILE_SIZE = 1024 * 1024 * 1024 * 10  # 10 GiB.


# Although MultiGetFileLogic is a leaky, complex, and overall problematic Mixin
# it seems to be best choice to fetch the stat, hashes, and contents of a file.
# At the time of writing, none of the flows exposed all three to the caller in
# a sensible way.
class CollectSingleFile(transfer.MultiGetFileLogic, flow_base.FlowBase):
  """Fetches contents of a single file from the specified absolute path."""
  friendly_name = "File content"
  category = "/Filesystem/"
  args_type = rdf_file_finder.CollectSingleFileArgs
  result_types = (rdf_file_finder.CollectSingleFileResult,)
  progress_type = rdf_file_finder.CollectSingleFileProgress
  behaviours = flow_base.BEHAVIOUR_DEBUG

  def GetProgress(self) -> rdf_file_finder.CollectSingleFileProgress:
    return self.state.progress

  def Start(self):
    super().Start(file_size=self.args.max_size_bytes)

    self.state.progress = rdf_file_finder.CollectSingleFileProgress(
        status=rdf_file_finder.CollectSingleFileProgress.Status.IN_PROGRESS)

    pathspec = rdf_paths.PathSpec.OS(path=self.args.path)
    self.StartFileFetch(pathspec)

  def ReceiveFetchedFile(self,
                         stat_entry,
                         hash_obj,
                         request_data=None,
                         is_duplicate=False):
    """See MultiGetFileLogic."""
    del request_data, is_duplicate  # Unused.

    result = rdf_file_finder.CollectSingleFileResult(
        stat=stat_entry, hash=hash_obj)
    self.SendReply(result)

    self.state.progress.result = result
    self.state.progress.status = (
        rdf_file_finder.CollectSingleFileProgress.Status.COLLECTED)

  def FileFetchFailed(self,
                      pathspec: rdf_paths.PathSpec,
                      request_data: Any = None,
                      status: Optional[rdf_flow_objects.FlowStatus] = None):
    """See MultiGetFileLogic."""
    if (self.client_os == "Windows" and
        pathspec.pathtype == rdf_paths.PathSpec.PathType.OS):
      # Retry with raw filesystem access on Windows,
      # the file might be locked for reads.
      raw_pathspec = rdf_paths.PathSpec(
          path=self.args.path,
          pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"])
      self.StartFileFetch(raw_pathspec)
    elif status is not None and status.error_message:
      error_description = "{} when fetching {} with {}".format(
          status.error_message, pathspec.path, pathspec.pathtype)

      # TODO: this is a really bad hack and should be fixed by
      # passing the 'not found' status in a more structured way.
      if "File not found" in status.error_message:
        self.state.progress.status = rdf_file_finder.CollectSingleFileProgress.Status.NOT_FOUND
      else:
        self.state.progress.status = rdf_file_finder.CollectSingleFileProgress.Status.FAILED
        self.state.progress.error_description = error_description

      raise flow_base.FlowError(error_description)
    else:
      error_description = (
          "File {} could not be fetched with {} due to an unknown error. "
          "Check the flow logs.".format(pathspec.path, pathspec.pathtype))

      self.state.progress.status = rdf_file_finder.CollectSingleFileProgress.Status.FAILED
      self.state.progress.error_description = error_description

      raise flow_base.FlowError(error_description)

  @classmethod
  def GetDefaultArgs(cls, username=None):
    """See base class."""
    del username  # Unused.
    return rdf_file_finder.CollectSingleFileArgs(
        path="", max_size_bytes="1 GiB")


# Although MultiGetFileLogic is a leaky, complex, and overall problematic Mixin
# it seems to be best choice to fetch the stat, hashes, and contents of a file.
# At the time of writing, none of the flows exposed all three to the caller in
# a sensible way.
class CollectFilesByKnownPath(transfer.MultiGetFileLogic, flow_base.FlowBase):
  """Fetches specified absolute path file contents."""

  friendly_name = "File contents by exact path"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  args_type = rdf_file_finder.CollectFilesByKnownPathArgs
  result_types = (rdf_file_finder.CollectFilesByKnownPathResult,)
  progress_type = rdf_file_finder.CollectFilesByKnownPathProgress

  def GetProgress(self) -> rdf_file_finder.CollectFilesByKnownPathProgress:
    return self.state.progress

  def Start(self):
    super().Start(file_size=_MAX_FILE_SIZE)

    self.state.progress = rdf_file_finder.CollectFilesByKnownPathProgress(
        num_in_progress=0,
        num_raw_fs_access_retries=0,
        num_collected=0,
        num_failed=0,
    )

    if self.args.collection_level == rdf_file_finder.CollectFilesByKnownPathArgs.CollectionLevel.STAT:
      self.state.stop_at_stat = True
    elif self.args.collection_level == rdf_file_finder.CollectFilesByKnownPathArgs.CollectionLevel.HASH:
      self.state.stop_at_hash = True

    for path in self.args.paths:
      pathspec = rdf_paths.PathSpec.OS(path=path)
      self.StartFileFetch(
          pathspec, request_data=dict(requested_pathspec=pathspec))
      self.state.progress.num_in_progress += 1

  def ReceiveFetchedFileStat(self,
                             stat_entry: rdf_client_fs.StatEntry,
                             request_data: Optional[Mapping[str, Any]] = None):
    """This method will be called for each new file stat successfully fetched.

    Args:
      stat_entry: rdf_client_fs.StatEntry object describing the file.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
    """
    del request_data  # Unused.

    if self.state.stop_at_stat:
      status = rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED
      self.state.progress.num_in_progress -= 1
      self.state.progress.num_collected += 1
    else:
      status = rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS

    result = rdf_file_finder.CollectFilesByKnownPathResult(
        stat=stat_entry, status=status)
    self.SendReply(result)

  def ReceiveFetchedFileHash(self,
                             stat_entry: rdf_client_fs.StatEntry,
                             file_hash: rdf_crypto.Hash,
                             request_data: Optional[Mapping[str, Any]] = None):
    """This method will be called for each new file hash successfully fetched.

    Args:
      stat_entry: rdf_client_fs.StatEntry object describing the file.
      file_hash: rdf_crypto.Hash object with file hashes.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
    """
    del request_data  # Unused.

    if self.state.stop_at_hash:
      status = rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED
      self.state.progress.num_in_progress -= 1
      self.state.progress.num_collected += 1
    else:
      status = rdf_file_finder.CollectFilesByKnownPathResult.Status.IN_PROGRESS

    result = rdf_file_finder.CollectFilesByKnownPathResult(
        stat=stat_entry, hash=file_hash, status=status)
    self.SendReply(result)

  def ReceiveFetchedFile(self,
                         stat_entry: rdf_client_fs.StatEntry,
                         file_hash: rdf_crypto.Hash,
                         request_data: Optional[Mapping[str, Any]] = None,
                         is_duplicate: bool = False):
    """This method will be called for each new file successfully fetched.

    Args:
      stat_entry: rdf_client_fs.StatEntry object describing the file.
      file_hash: rdf_crypto.Hash object with file hashes.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
      is_duplicate: If True, the file wasn't actually collected as its hash was
        found in the filestore.
    """
    del request_data, is_duplicate  # Unused.

    result = rdf_file_finder.CollectFilesByKnownPathResult(
        stat=stat_entry,
        hash=file_hash,
        status=rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED)
    self.SendReply(result)

    self.state.progress.num_in_progress -= 1
    self.state.progress.num_collected += 1

  def FileFetchFailed(self,
                      pathspec: rdf_paths.PathSpec,
                      request_data: Optional[Mapping[str, Any]] = None,
                      status: Optional[rdf_flow_objects.FlowStatus] = None):
    """This method will be called when stat or hash requests fail.

    Args:
      pathspec: Pathspec of a file that failed to be fetched.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
      status: FlowStatus that contains more error details.
    """
    requested_pathspec = request_data["requested_pathspec"]

    if (self.client_os == "Windows" and
        pathspec.pathtype == rdf_paths.PathSpec.PathType.OS):
      # Retry with raw filesystem access on Windows, the file might be locked
      # for reads.
      raw_pathspec = rdf_paths.PathSpec(
          path=requested_pathspec.path,
          pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"])
      self.StartFileFetch(
          raw_pathspec, request_data=dict(requested_pathspec=raw_pathspec))
      self.state.progress.num_raw_fs_access_retries += 1
    else:
      if status is not None and status.error_message:
        error_description = "{} when fetching {} with {}".format(
            status.error_message, pathspec.path, pathspec.pathtype)
        # TODO: This is a really bad hack and should be fixed by
        # passing the 'not found' status in a more structured way.
        if "File not found" in status.error_message:
          file_status = rdf_file_finder.CollectFilesByKnownPathResult.Status.NOT_FOUND
        else:
          file_status = rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED
      else:
        error_description = (
            "File {} could not be fetched with {} due to an unknown error. "
            "Check the flow logs.".format(pathspec.path, pathspec.pathtype))
        file_status = rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED

      result = rdf_file_finder.CollectFilesByKnownPathResult(
          stat=rdf_client_fs.StatEntry(pathspec=requested_pathspec),
          error=error_description,
          status=file_status,
      )
      self.SendReply(result)

      self.state.progress.num_in_progress -= 1
      self.state.progress.num_failed += 1


class CollectMultipleFiles(transfer.MultiGetFileLogic, flow_base.FlowBase):
  """Fetches contents of files by searching for path expressions."""
  friendly_name = "Collect multiple files"
  category = "/Filesystem/"
  args_type = rdf_file_finder.CollectMultipleFilesArgs
  result_types = (rdf_file_finder.CollectMultipleFilesResult,)
  progress_type = rdf_file_finder.CollectMultipleFilesProgress
  behaviours = flow_base.BEHAVIOUR_DEBUG

  MAX_FILE_SIZE = 1024 * 1024 * 1024 * 10  # 10GiB

  def GetProgress(self) -> rdf_file_finder.CollectMultipleFilesProgress:
    return self.state.progress

  def Start(self):
    """See base class."""
    super().Start(file_size=self.MAX_FILE_SIZE)

    self.state.progress = rdf_file_finder.CollectMultipleFilesProgress(
        num_found=0,
        num_in_progress=0,
        num_raw_fs_access_retries=0,
        num_collected=0,
        num_failed=0,
    )

    conditions = []

    if self.args.HasField("modification_time"):
      conditions.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=rdf_file_finder.FileFinderCondition.Type
              .MODIFICATION_TIME,
              modification_time=self.args.modification_time,
          ))

    if self.args.HasField("access_time"):
      conditions.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=rdf_file_finder.FileFinderCondition.Type
              .ACCESS_TIME,
              access_time=self.args.access_time,
          ))

    if self.args.HasField("inode_change_time"):
      conditions.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=rdf_file_finder.FileFinderCondition.Type
              .INODE_CHANGE_TIME,
              inode_change_time=self.args.inode_change_time,
          ))

    if self.args.HasField("size"):
      conditions.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=rdf_file_finder.FileFinderCondition.Type.SIZE,
              size=self.args.size,
          ))

    if self.args.HasField("ext_flags"):
      conditions.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=rdf_file_finder.FileFinderCondition.Type.EXT_FLAGS,
              ext_flags=self.args.ext_flags,
          ))

    if self.args.HasField("contents_regex_match"):
      conditions.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=rdf_file_finder.FileFinderCondition.Type
              .CONTENTS_REGEX_MATCH,
              contents_regex_match=self.args.contents_regex_match,
          ))

    if self.args.HasField("contents_literal_match"):
      conditions.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=rdf_file_finder.FileFinderCondition.Type
              .CONTENTS_LITERAL_MATCH,
              contents_literal_match=self.args.contents_literal_match,
          ))

    file_finder_args = rdf_file_finder.FileFinderArgs(
        paths=self.args.path_expressions,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        conditions=conditions,
        action=rdf_file_finder.FileFinderAction.Stat())

    self.CallFlow(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessFiles.__name__)

  def ProcessFiles(self, responses):
    if not responses.success:
      raise flow_base.FlowError(responses.status.error_message)

    for response in responses:
      pathspec = response.stat_entry.pathspec
      self.StartFileFetch(pathspec, request_data=dict(original_result=response))
      self.state.progress.num_found += 1
      self.state.progress.num_in_progress += 1

  def ReceiveFetchedFile(self,
                         stat_entry,
                         hash_obj,
                         request_data=None,
                         is_duplicate=False):
    """See MultiGetFileLogic."""
    del request_data, is_duplicate  # Unused.

    result = rdf_file_finder.CollectMultipleFilesResult(
        stat=stat_entry,
        hash=hash_obj,
        status=rdf_file_finder.CollectMultipleFilesResult.Status.COLLECTED)
    self.SendReply(result)

    self.state.progress.num_in_progress = max(
        0, self.state.progress.num_in_progress - 1)
    self.state.progress.num_collected += 1

  def FileFetchFailed(self,
                      pathspec: rdf_paths.PathSpec,
                      request_data: Any = None,
                      status: Optional[rdf_flow_objects.FlowStatus] = None):
    """See MultiGetFileLogic."""
    original_result = request_data["original_result"]

    if (self.client_os == "Windows" and
        pathspec.pathtype == rdf_paths.PathSpec.PathType.OS):
      # Retry with raw filesystem access on Windows,
      # the file might be locked for reads.
      raw_pathspec = rdf_paths.PathSpec(
          path=self.args.path,
          pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"])
      self.StartFileFetch(raw_pathspec)

      self.state.progress.num_raw_fs_access_retries += 1
    else:
      if status is not None and status.error_message:
        error_description = "{} when fetching {} with {}".format(
            status.error_message, pathspec.path, pathspec.pathtype)
      else:
        error_description = (
            "File {} could not be fetched with {} due to an unknown error. "
            "Check the flow logs.".format(pathspec.path, pathspec.pathtype))

      result = rdf_file_finder.CollectMultipleFilesResult(
          stat=original_result.stat_entry,
          error=error_description,
          status=rdf_file_finder.CollectMultipleFilesResult.Status.FAILED,
      )
      self.SendReply(result)

      self.state.progress.num_in_progress = max(
          0, self.state.progress.num_in_progress - 1)
