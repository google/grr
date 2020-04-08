#!/usr/bin/env python
# Lint as: python3
"""Flows to collect file contents and metadata."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import flow_base
from grr_response_server.flows.general import transfer


class CollectSingleFile(transfer.MultiGetFileLogic, flow_base.FlowBase):
  """Fetches contents of a single file from the specified absolute path."""
  friendly_name = "File content"
  category = "/Filesystem/"
  args_type = rdf_file_finder.CollectSingleFileArgs
  result_types = (rdf_file_finder.CollectSingleFileResult,)
  behaviours = flow_base.BEHAVIOUR_DEBUG

  def Start(self):
    super().Start(file_size=self.args.max_size_bytes)
    pathspec = rdf_paths.PathSpec.OS(path=self.args.path)
    self.StartFileFetch(pathspec)

  def ReceiveFetchedFile(self,
                         stat_entry,
                         hash_obj,
                         request_data=None,
                         is_duplicate=False):
    """See MultiGetFileLogic."""
    del request_data, is_duplicate  # Unused.
    # TODO(user): If client is Windows and collection failed, retry
    #  with TSK/NTFS.
    result = rdf_file_finder.CollectSingleFileResult(
        stat=stat_entry, hash=hash_obj)
    self.SendReply(result)

  def FileFetchFailed(self, pathspec, request_data=None):
    """See MultiGetFileLogic."""
    raise flow_base.FlowError("Error while fetching file.")
