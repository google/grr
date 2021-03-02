#!/usr/bin/env python
import contextlib
from unittest import mock

from absl import flags
from absl.testing import absltest

from grr_response_client import vfs as client_vfs
from grr_response_client.unprivileged.filesystem import vfs
from grr_response_client.vfs_handlers import files as vfs_files
from grr_response_client.vfs_handlers import ntfs_test_lib
from grr_response_core.lib import config_lib
from grr_response_core.lib import package


class VfsNtfsTestBase(ntfs_test_lib.NTFSTest):

  def setUp(self):
    super().setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    stack.enter_context(
        mock.patch.dict(client_vfs.VFS_HANDLERS, {
            vfs.UnprivilegedNtfsFile.supported_pathtype:
                vfs.UnprivilegedNtfsFile,
        }))


class VfsNtfsWithFileDescriptorSharingTest(VfsNtfsTestBase):
  """Test variant sharing the device file descriptor with the server."""
  pass


class VfsNtfsWithRemoteDeviceTest(VfsNtfsTestBase):
  """Test variant sharing the device via RPC calls with the server."""

  def setUp(self):
    super().setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    # The File VFS handler won't return a path.
    stack.enter_context(mock.patch.object(vfs_files.File, "native_path", None))


# Don't run tests from the base class.
# TODO(user): Remove this once there
# is support for abstract test cases.
del VfsNtfsTestBase


def setUpModule():
  # client_vfs needs a config to be loaded to work.
  flags.FLAGS.config = package.ResourcePath(
      "grr-response-test", "grr_response_test/test_data/dummyconfig.yaml")
  config_lib.ParseConfigCommandLine()

  client_vfs.Init()


def tearDownModule():
  vfs.MOUNT_CACHE.Flush()


if __name__ == "__main__":
  absltest.main()
