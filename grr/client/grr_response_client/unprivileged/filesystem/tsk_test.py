#!/usr/bin/env python
from absl.testing import absltest

from grr_response_client.unprivileged import test_lib
from grr_response_client.unprivileged.filesystem import ntfs_image_test_lib
from grr_response_client.unprivileged.proto import filesystem_pb2


class TskTest(ntfs_image_test_lib.NtfsImageTest):

  _IMPLEMENTATION_TYPE = filesystem_pb2.TSK

  def _ExpectedStatEntry(
      self, st: filesystem_pb2.StatEntry) -> filesystem_pb2.StatEntry:
    """Clears the fields which are not returned by TSK."""
    if st.HasField("ntfs"):
      st.ClearField("ntfs")
    # TSK doesn't report sub-second granularity for timestamps.
    if st.HasField("st_atime"):
      st.st_atime.nanos = 0
    if st.HasField("st_btime"):
      st.st_btime.nanos = 0
    if st.HasField("st_ctime"):
      st.st_ctime.nanos = 0
    if st.HasField("st_mtime"):
      st.st_mtime.nanos = 0
    return st

  def _FileRefToInode(self, file_ref: int) -> int:
    # Clear the version (upper 16 bits) in the file reference.
    return file_ref & ~(0xFFFF << 48)

  def _Path(self, path: str) -> str:
    # TSK uses slashes as path separators.
    return path.replace("\\", "/")

  def testOpenByInode_stale(self):
    pass


def setUpModule() -> None:
  test_lib.SetUpDummyConfig()


if __name__ == "__main__":
  absltest.main()
