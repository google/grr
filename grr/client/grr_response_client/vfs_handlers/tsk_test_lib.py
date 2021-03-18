#!/usr/bin/env python
# pylint: mode=test

from grr_response_client.vfs_handlers import ntfs_image_test_lib
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths


class TSKTest(ntfs_image_test_lib.NTFSImageTest):
  PATH_TYPE = rdf_paths.PathSpec.PathType.TSK

  def _FileRefToInode(self, file_ref: int) -> int:
    # Clear the version (upper 16 bits) in the file reference.
    return file_ref & ~(0xFFFF << 48)

  def _ExpectedStatEntry(
      self, st: rdf_client_fs.StatEntry) -> rdf_client_fs.StatEntry:
    return st
