#!/usr/bin/env python
import contextlib
from unittest import mock

from absl.testing import absltest

from grr_response_client import vfs as client_vfs
from grr_response_client.unprivileged import test_lib
from grr_response_client.unprivileged.filesystem import vfs
from grr_response_client.vfs_handlers import tsk_test_lib


class VfsTskTest(tsk_test_lib.TSKTest):

  def setUp(self):
    super().setUp()

    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    stack.enter_context(
        mock.patch.dict(client_vfs.VFS_HANDLERS, {
            vfs.UnprivilegedTskFile.supported_pathtype: vfs.UnprivilegedTskFile,
        }))


def setUpModule():
  test_lib.SetUpDummyConfig()
  client_vfs.Init()


def tearDownModule():
  vfs.MOUNT_CACHE.Flush()


if __name__ == "__main__":
  absltest.main()
