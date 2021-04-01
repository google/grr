#!/usr/bin/env python
import contextlib
from unittest import mock
from absl.testing import absltest

from grr_response_client.unprivileged import test_lib
from grr_response_client.unprivileged.filesystem import client
from grr_response_client.unprivileged.filesystem import ntfs_image_test_lib
from grr_response_client.unprivileged.proto import filesystem_pb2


class NtfsTestBase(ntfs_image_test_lib.NtfsImageTest):

  _IMPLEMENTATION_TYPE = filesystem_pb2.NTFS

  def _ExpectedStatEntry(
      self, st: filesystem_pb2.StatEntry) -> filesystem_pb2.StatEntry:
    st.ClearField("st_mode")
    st.ClearField("st_nlink")
    st.ClearField("st_uid")
    st.ClearField("st_gid")
    return st

  def _FileRefToInode(self, file_ref: int) -> int:
    return file_ref

  def _Path(self, path: str) -> str:
    return path


class NtfsWithRemoteDeviceTest(NtfsTestBase):
  """Test variant sharing the device via RPC calls with the server."""

  def setUp(self):
    super().setUp()
    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    # The FileDevice won't return a file descriptor.
    stack.enter_context(
        mock.patch.object(client.FileDevice, "file_descriptor", None))


class NtfsWithFileDescriptorSharingTest(NtfsTestBase):
  """Test variant sharing a file descriptor of the device with the server."""

  pass


# Don't run tests from the base class.
# TODO(user): Remove this once there
# is support for abstract test cases.
del NtfsTestBase


def setUpModule() -> None:
  test_lib.SetUpDummyConfig()


if __name__ == "__main__":
  absltest.main()
