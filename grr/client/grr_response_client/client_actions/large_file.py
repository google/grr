#!/usr/bin/env python
"""A module with action for large file collection."""

from collections.abc import Iterator

from grr_response_client import actions
from grr_response_client import gcs
from grr_response_client import vfs
from grr_response_core.lib.rdfvalues import large_file as rdf_large_file
from grr_response_core.lib.util import aead


def CollectLargeFile(
    args: rdf_large_file.CollectLargeFileArgs,
) -> Iterator[rdf_large_file.CollectLargeFileResult]:
  """Implements the large file collection action procedure."""
  # Note that we don't validate encryption key length in the action code itself
  # since this is done in the cryptography library anyway (but should be ensured
  # with tests). By letting the library handle this it is up to the server to
  # decide what length of the key to use (be it 128, 192 or 256 bits) without
  # the need to push a new agent version.

  with vfs.VFSOpen(args.path_spec) as file:
    file = aead.Encrypt(file, args.encryption_key)

    session = gcs.UploadSession.Open(args.signed_url)

    start_upload_result = rdf_large_file.CollectLargeFileResult()
    start_upload_result.session_uri = session.uri
    yield start_upload_result

    total_content_length = session.SendFile(file)

    finish_upload_result = start_upload_result.Copy()
    finish_upload_result.total_bytes_sent = total_content_length
    yield finish_upload_result


class CollectLargeFileAction(actions.ActionPlugin):
  """An action class for large file collection."""

  in_rdfvalue = rdf_large_file.CollectLargeFileArgs
  out_rdfvalues = [rdf_large_file.CollectLargeFileResult]

  def Run(self, args: rdf_large_file.CollectLargeFileArgs) -> None:
    for result in CollectLargeFile(args):
      self.SendReply(result)
