#!/usr/bin/env python
"""A module with action for large file collection."""
from typing import Iterator

from grr_response_client import actions
from grr_response_client import gcs
from grr_response_client import vfs
from grr_response_core.lib.rdfvalues import large_file as rdf_large_file


def CollectLargeFile(
    args: rdf_large_file.CollectLargeFileArgs,
) -> Iterator[rdf_large_file.CollectLargeFileResult]:
  """Implements the large file collection action procedure."""
  with vfs.VFSOpen(args.path_spec) as file:
    session = gcs.UploadSession.Open(args.signed_url)

    result = rdf_large_file.CollectLargeFileResult()
    result.session_uri = session.uri
    yield result

    session.SendFile(file)


class CollectLargeFileAction(actions.ActionPlugin):
  """An action class for large file collection."""

  in_rdfvalue = rdf_large_file.CollectLargeFileArgs
  out_rdfvalues = [rdf_large_file.CollectLargeFileResult]

  def Run(self, args: rdf_large_file.CollectLargeFileArgs) -> None:
    for result in CollectLargeFile(args):
      self.SendReply(result)
