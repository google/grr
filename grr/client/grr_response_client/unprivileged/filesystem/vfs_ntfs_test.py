#!/usr/bin/env python
import contextlib
import platform
from unittest import mock

from absl import flags
from absl.testing import absltest

from grr_response_client import vfs as client_vfs
from grr_response_client.unprivileged.filesystem import vfs
from grr_response_client.vfs_handlers import ntfs_test_lib
from grr_response_core.lib import config_lib
from grr_response_core.lib import package


@absltest.skipIf(platform.system() == "Windows",
                 "Currently not running on Windows.")
class VfsNtfsTest(ntfs_test_lib.NTFSTest):

  def setUp(self):
    super(VfsNtfsTest, self).setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    stack.enter_context(
        mock.patch.dict(client_vfs.VFS_HANDLERS, {
            vfs.UnprivilegedNtfsFile.supported_pathtype:
                vfs.UnprivilegedNtfsFile,
        }))


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
