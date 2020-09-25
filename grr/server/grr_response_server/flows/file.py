#!/usr/bin/env python
# Lint as: python3
"""Flows to collect file contents and metadata."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Any, Optional

from grr_response_core import config
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import flow_base
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


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
    self.state.progress.status = rdf_file_finder.CollectSingleFileProgress.Status.COLLECTED

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

      self.state.progress.tatus = rdf_file_finder.CollectSingleFileProgress.Status.FAILED
      self.state.progress.error_description = error_description

      raise flow_base.FlowError(error_description)

  @classmethod
  def GetDefaultArgs(cls, username=None):
    """See base class."""
    del username  # Unused.
    return rdf_file_finder.CollectSingleFileArgs(
        path="", max_size_bytes="1 GiB")


class CollectMultipleFiles(flow_base.FlowBase):
  """Fetches contents of files by searching for path expressions."""
  friendly_name = "Collect multiple files"
  category = "/Filesystem/"
  args_type = rdf_file_finder.CollectMultipleFilesArgs
  result_types = (rdf_file_finder.CollectMultipleFilesResult,)
  behaviours = flow_base.BEHAVIOUR_DEBUG

  def Start(self):
    """See base class."""
    super().Start()

    self.CallFlow(
        file_finder.FileFinder.__name__,
        paths=list(self.args.path_expressions),
        pathtype=rdf_paths.PathSpec.PathType.OS,
        action=rdf_file_finder.FileFinderAction.Download(),
        next_state=self._ReceiveFiles.__name__)

  def _ReceiveFiles(self, responses):
    result = rdf_file_finder.CollectMultipleFilesResult()

    for response in responses:
      result.files.Append(
          rdf_file_finder.CollectedFile(
              stat=response.stat_entry, hash=response.hash_entry))

    self.SendReply(result)

    if not responses.success:
      raise flow_base.FlowError(responses.status.error_message)
