#!/usr/bin/env python
"""Flows to collect file contents and metadata."""

from collections.abc import Mapping
from typing import Any, Optional

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
class CollectFilesByKnownPath(transfer.MultiGetFileLogic, flow_base.FlowBase):
  """Fetches specified absolute path file contents."""

  friendly_name = "File contents by exact path"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  args_type = rdf_file_finder.CollectFilesByKnownPathArgs
  result_types = (rdf_file_finder.CollectFilesByKnownPathResult,)
  progress_type = rdf_file_finder.CollectFilesByKnownPathProgress

  def GetProgress(self) -> rdf_file_finder.CollectFilesByKnownPathProgress:
    if hasattr(self.state, "progress"):
      return self.state.progress
    return rdf_file_finder.CollectFilesByKnownPathProgress()

  def Start(self):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    super().Start(file_size=_MAX_FILE_SIZE)

    self.state.progress = rdf_file_finder.CollectFilesByKnownPathProgress(
        num_in_progress=0,
        num_raw_fs_access_retries=0,
        num_collected=0,
        num_failed=0,
    )

    if (
        self.args.collection_level
        == rdf_file_finder.CollectFilesByKnownPathArgs.CollectionLevel.STAT
    ):
      self.state.stop_at_stat = True
    elif (
        self.args.collection_level
        == rdf_file_finder.CollectFilesByKnownPathArgs.CollectionLevel.HASH
    ):
      self.state.stop_at_hash = True

    for path in self.args.paths:
      pathspec = rdf_paths.PathSpec.OS(path=path)
      self.StartFileFetch(
          pathspec, request_data=dict(requested_pathspec=pathspec)
      )
      self.state.progress.num_in_progress += 1

  def ReceiveFetchedFileStat(
      self,
      stat_entry: rdf_client_fs.StatEntry,
      request_data: Optional[Mapping[str, Any]] = None,
  ):
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
        stat=stat_entry, status=status
    )
    self.SendReply(result)

  def ReceiveFetchedFileHash(
      self,
      stat_entry: rdf_client_fs.StatEntry,
      file_hash: rdf_crypto.Hash,
      request_data: Optional[Mapping[str, Any]] = None,
  ):
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
        stat=stat_entry, hash=file_hash, status=status
    )
    self.SendReply(result)

  def ReceiveFetchedFile(
      self,
      stat_entry: rdf_client_fs.StatEntry,
      file_hash: rdf_crypto.Hash,
      request_data: Optional[Mapping[str, Any]] = None,
      is_duplicate: bool = False,
  ):
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
        status=rdf_file_finder.CollectFilesByKnownPathResult.Status.COLLECTED,
    )
    self.SendReply(result)

    self.state.progress.num_in_progress -= 1
    self.state.progress.num_collected += 1

  def FileFetchFailed(
      self,
      pathspec: rdf_paths.PathSpec,
      request_data: Optional[Mapping[str, Any]] = None,
      status: Optional[rdf_flow_objects.FlowStatus] = None,
  ):
    """This method will be called when stat or hash requests fail.

    Args:
      pathspec: Pathspec of a file that failed to be fetched.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
      status: FlowStatus that contains more error details.
    """
    requested_pathspec = request_data["requested_pathspec"]

    if (
        self.client_os == "Windows"
        and pathspec.pathtype == rdf_paths.PathSpec.PathType.OS
    ):
      # Retry with raw filesystem access on Windows, the file might be locked
      # for reads.
      raw_pathspec = rdf_paths.PathSpec(
          path=requested_pathspec.path,
          pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"],
      )
      self.StartFileFetch(
          raw_pathspec, request_data=dict(requested_pathspec=raw_pathspec)
      )
      self.state.progress.num_raw_fs_access_retries += 1
    else:
      if status is not None and status.error_message:
        error_description = "{} when fetching {} with {}".format(
            status.error_message, pathspec.path, pathspec.pathtype
        )
        # TODO: This is a really bad hack and should be fixed by
        # passing the 'not found' status in a more structured way.
        if "File not found" in status.error_message:
          file_status = (
              rdf_file_finder.CollectFilesByKnownPathResult.Status.NOT_FOUND
          )
        else:
          file_status = (
              rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED
          )
      else:
        error_description = (
            "File {} could not be fetched with {} due to an unknown error. "
            "Check the flow logs.".format(pathspec.path, pathspec.pathtype)
        )
        file_status = (
            rdf_file_finder.CollectFilesByKnownPathResult.Status.FAILED
        )

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
    if hasattr(self.state, "progress"):
      return self.state.progress
    return rdf_file_finder.CollectMultipleFilesProgress()

  def Start(self):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    """See base class."""
    super().Start(file_size=self.MAX_FILE_SIZE)

    self.state.progress = rdf_file_finder.CollectMultipleFilesProgress(
        num_found=0,
        num_in_progress=0,
        num_raw_fs_access_retries=0,
        num_collected=0,
        num_failed=0,
    )

    conditions = BuildClientFileFinderConditions(
        modification_time=self.args.modification_time
        if self.args.HasField("modification_time")
        else None,
        access_time=self.args.access_time
        if self.args.HasField("access_time")
        else None,
        inode_change_time=self.args.inode_change_time
        if self.args.HasField("inode_change_time")
        else None,
        size=self.args.size if self.args.HasField("size") else None,
        ext_flags=self.args.ext_flags
        if self.args.HasField("ext_flags")
        else None,
        contents_regex_match=self.args.contents_regex_match
        if self.args.HasField("contents_regex_match")
        else None,
        contents_literal_match=self.args.contents_literal_match
        if self.args.HasField("contents_literal_match")
        else None,
    )

    file_finder_args = rdf_file_finder.FileFinderArgs(
        paths=self.args.path_expressions,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        conditions=conditions,
        action=rdf_file_finder.FileFinderAction.Stat(),
    )

    self.CallFlow(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessFiles.__name__,
    )

  def ProcessFiles(self, responses):
    if not responses.success:
      raise flow_base.FlowError(responses.status.error_message)

    for response in responses:
      pathspec = response.stat_entry.pathspec
      self.StartFileFetch(
          pathspec, request_data=dict(original_pathspec=pathspec)
      )
      self.state.progress.num_found += 1
      self.state.progress.num_in_progress += 1

  def ReceiveFetchedFile(
      self, stat_entry, hash_obj, request_data=None, is_duplicate=False
  ):
    """See MultiGetFileLogic."""
    del request_data, is_duplicate  # Unused.

    self.state.progress.num_in_progress = max(
        0, self.state.progress.num_in_progress - 1
    )
    self.state.progress.num_collected += 1

    result = rdf_file_finder.CollectMultipleFilesResult(
        stat=stat_entry,
        hash=hash_obj,
        status=rdf_file_finder.CollectMultipleFilesResult.Status.COLLECTED,
    )
    self.SendReply(result)

  def FileFetchFailed(
      self,
      pathspec: rdf_paths.PathSpec,
      request_data: Any = None,
      status: Optional[rdf_flow_objects.FlowStatus] = None,
  ):
    """See MultiGetFileLogic."""
    original_pathspec = pathspec
    if request_data is not None and request_data["original_pathspec"]:
      original_pathspec = request_data["original_pathspec"]

    if (
        self.client_os == "Windows"
        and pathspec.pathtype == rdf_paths.PathSpec.PathType.OS
    ):
      # Retry with raw filesystem access on Windows,
      # the file might be locked for reads.
      raw_pathspec = rdf_paths.PathSpec(
          path=original_pathspec.path,
          pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"],
      )
      self.StartFileFetch(
          raw_pathspec, request_data=dict(original_pathspec=raw_pathspec)
      )

      self.state.progress.num_raw_fs_access_retries += 1
    else:
      if status is not None and status.error_message:
        error_description = "{} when fetching {} with {}".format(
            status.error_message, pathspec.path, pathspec.pathtype
        )
      else:
        error_description = (
            "File {} could not be fetched with {} due to an unknown error. "
            "Check the flow logs.".format(pathspec.path, pathspec.pathtype)
        )

      self.state.progress.num_in_progress = max(
          0, self.state.progress.num_in_progress - 1
      )
      self.state.progress.num_failed += 1

      result = rdf_file_finder.CollectMultipleFilesResult(
          stat=rdf_client_fs.StatEntry(pathspec=original_pathspec),
          error=error_description,
          status=rdf_file_finder.CollectMultipleFilesResult.Status.FAILED,
      )
      self.SendReply(result)


class StatMultipleFiles(flow_base.FlowBase):
  """Fetches file stats by searching for path expressions."""

  friendly_name = "Collect file stats"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_file_finder.StatMultipleFilesArgs
  result_types = (rdf_client_fs.StatEntry,)

  def Start(self):
    conditions = BuildClientFileFinderConditions(
        modification_time=self.args.modification_time
        if self.args.HasField("modification_time")
        else None,
        access_time=self.args.access_time
        if self.args.HasField("access_time")
        else None,
        inode_change_time=self.args.inode_change_time
        if self.args.HasField("inode_change_time")
        else None,
        size=self.args.size if self.args.HasField("size") else None,
        ext_flags=self.args.ext_flags
        if self.args.HasField("ext_flags")
        else None,
        contents_regex_match=self.args.contents_regex_match
        if self.args.HasField("contents_regex_match")
        else None,
        contents_literal_match=self.args.contents_literal_match
        if self.args.HasField("contents_literal_match")
        else None,
    )

    file_finder_args = rdf_file_finder.FileFinderArgs(
        paths=self.args.path_expressions,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        conditions=conditions,
        action=rdf_file_finder.FileFinderAction.Stat(),
    )

    self.CallFlow(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessResponses.__name__,
    )

  def ProcessResponses(self, responses):
    if not responses.success:
      raise flow_base.FlowError(responses.status.error_message)

    for response in responses:
      self.SendReply(response.stat_entry)


class HashMultipleFiles(transfer.MultiGetFileLogic, flow_base.FlowBase):
  """Fetches file hashes and stats by searching for path expressions."""

  friendly_name = "Collect file hashes"
  category = "/Filesystem/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  args_type = rdf_file_finder.HashMultipleFilesArgs
  result_types = (rdf_file_finder.CollectMultipleFilesResult,)
  progress_type = rdf_file_finder.HashMultipleFilesProgress

  MAX_FILE_SIZE = 1024 * 1024 * 1024 * 10  # 10GiB

  def GetProgress(self) -> rdf_file_finder.HashMultipleFilesProgress:
    if hasattr(self.state, "progress"):
      return self.state.progress
    return rdf_file_finder.HashMultipleFilesProgress()

  def Start(self):  # pytype: disable=signature-mismatch  # overriding-parameter-count-checks
    """See base class."""
    super().Start(file_size=self.MAX_FILE_SIZE)

    self.state.progress = rdf_file_finder.HashMultipleFilesProgress(
        num_found=0,
        num_in_progress=0,
        num_raw_fs_access_retries=0,
        num_hashed=0,
        num_failed=0,
    )

    # Set the collection level for MultiGetFileLogic mixin, as the default
    # one is collecting the file contents
    self.state.stop_at_hash = True

    conditions = BuildClientFileFinderConditions(
        modification_time=self.args.modification_time
        if self.args.HasField("modification_time")
        else None,
        access_time=self.args.access_time
        if self.args.HasField("access_time")
        else None,
        inode_change_time=self.args.inode_change_time
        if self.args.HasField("inode_change_time")
        else None,
        size=self.args.size if self.args.HasField("size") else None,
        ext_flags=self.args.ext_flags
        if self.args.HasField("ext_flags")
        else None,
        contents_regex_match=self.args.contents_regex_match
        if self.args.HasField("contents_regex_match")
        else None,
        contents_literal_match=self.args.contents_literal_match
        if self.args.HasField("contents_literal_match")
        else None,
    )

    file_finder_args = rdf_file_finder.FileFinderArgs(
        paths=self.args.path_expressions,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        conditions=conditions,
        action=rdf_file_finder.FileFinderAction.Hash(),
    )

    self.CallFlow(
        file_finder.ClientFileFinder.__name__,
        flow_args=file_finder_args,
        next_state=self.ProcessResponses.__name__,
    )

  def ProcessResponses(self, responses):
    if not responses.success:
      raise flow_base.FlowError(responses.status.error_message)

    for response in responses:
      pathspec = response.stat_entry.pathspec
      self.StartFileFetch(
          pathspec, request_data=dict(original_pathspec=pathspec)
      )
      self.state.progress.num_found += 1
      self.state.progress.num_in_progress += 1

  def FileFetchFailed(
      self,
      pathspec: rdf_paths.PathSpec,
      request_data: Any = None,
      status: Optional[rdf_flow_objects.FlowStatus] = None,
  ):
    """See MultiGetFileLogic."""
    original_pathspec = pathspec
    if request_data is not None and request_data["original_pathspec"]:
      original_pathspec = request_data["original_pathspec"]

    if (
        self.client_os == "Windows"
        and pathspec.pathtype == rdf_paths.PathSpec.PathType.OS
    ):
      # Retry with raw filesystem access on Windows,
      # the file might be locked for reads.
      raw_pathspec = rdf_paths.PathSpec(
          path=original_pathspec.path,
          pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"],
      )
      self.StartFileFetch(
          raw_pathspec, request_data=dict(original_pathspec=raw_pathspec)
      )

      self.state.progress.num_raw_fs_access_retries += 1
    else:
      if status is not None and status.error_message:
        error_description = "{} when fetching {} with {}".format(
            status.error_message, pathspec.path, pathspec.pathtype
        )
      else:
        error_description = (
            "File {} could not be fetched with {} due to an unknown error. "
            "Check the flow logs.".format(pathspec.path, pathspec.pathtype)
        )

      self.state.progress.num_in_progress = max(
          0, self.state.progress.num_in_progress - 1
      )
      self.state.progress.num_failed += 1

      result = rdf_file_finder.CollectMultipleFilesResult(
          stat=rdf_client_fs.StatEntry(pathspec=original_pathspec),
          error=error_description,
          status=rdf_file_finder.CollectMultipleFilesResult.Status.FAILED,
      )
      self.SendReply(result)

  def ReceiveFetchedFileHash(
      self,
      stat_entry: rdf_client_fs.StatEntry,
      file_hash: rdf_crypto.Hash,
      request_data: Optional[Mapping[str, Any]] = None,
  ):
    """This method will be called for each new file hash successfully fetched.

    Args:
      stat_entry: rdf_client_fs.StatEntry object describing the file.
      file_hash: rdf_crypto.Hash object with file hashes.
      request_data: Arbitrary dictionary that was passed to the corresponding
        StartFileFetch call.
    """
    del request_data  # Unused.

    self.state.progress.num_in_progress -= 1
    self.state.progress.num_hashed += 1

    result = rdf_file_finder.CollectMultipleFilesResult(
        stat=stat_entry,
        hash=file_hash,
        status=rdf_file_finder.CollectMultipleFilesResult.Status.COLLECTED,
    )

    self.SendReply(result)


def BuildClientFileFinderConditions(
    modification_time: Optional[
        rdf_file_finder.FileFinderModificationTimeCondition
    ] = None,
    access_time: Optional[rdf_file_finder.FileFinderAccessTimeCondition] = None,
    inode_change_time: Optional[
        rdf_file_finder.FileFinderInodeChangeTimeCondition
    ] = None,
    size: Optional[rdf_file_finder.FileFinderSizeCondition] = None,
    ext_flags: Optional[rdf_file_finder.FileFinderExtFlagsCondition] = None,
    contents_regex_match: Optional[
        rdf_file_finder.FileFinderContentsRegexMatchCondition
    ] = None,
    contents_literal_match: Optional[
        rdf_file_finder.FileFinderContentsLiteralMatchCondition
    ] = None,
) -> list[rdf_file_finder.FileFinderCondition]:
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
        rdf_file_finder.FileFinderCondition(
            condition_type=rdf_file_finder.FileFinderCondition.Type.MODIFICATION_TIME,
            modification_time=modification_time,
        )
    )

  if access_time is not None:
    conditions.append(
        rdf_file_finder.FileFinderCondition(
            condition_type=rdf_file_finder.FileFinderCondition.Type.ACCESS_TIME,
            access_time=access_time,
        )
    )

  if inode_change_time is not None:
    conditions.append(
        rdf_file_finder.FileFinderCondition(
            condition_type=rdf_file_finder.FileFinderCondition.Type.INODE_CHANGE_TIME,
            inode_change_time=inode_change_time,
        )
    )

  if size is not None:
    conditions.append(
        rdf_file_finder.FileFinderCondition(
            condition_type=rdf_file_finder.FileFinderCondition.Type.SIZE,
            size=size,
        )
    )

  if ext_flags is not None:
    conditions.append(
        rdf_file_finder.FileFinderCondition(
            condition_type=rdf_file_finder.FileFinderCondition.Type.EXT_FLAGS,
            ext_flags=ext_flags,
        )
    )

  if contents_regex_match is not None:
    conditions.append(
        rdf_file_finder.FileFinderCondition(
            condition_type=rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH,
            contents_regex_match=contents_regex_match,
        )
    )

  if contents_literal_match is not None:
    conditions.append(
        rdf_file_finder.FileFinderCondition(
            condition_type=rdf_file_finder.FileFinderCondition.Type.CONTENTS_LITERAL_MATCH,
            contents_literal_match=contents_literal_match,
        )
    )

  return conditions
