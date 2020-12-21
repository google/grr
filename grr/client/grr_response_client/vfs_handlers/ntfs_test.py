#!/usr/bin/env python
from absl import app

# pylint: disable=unused-import
from grr_response_client.vfs_handlers.ntfs_test_lib import NTFSNativeWindowsTest
from grr_response_client.vfs_handlers.ntfs_test_lib import NTFSTest
# pylint: enable=unused-import
from grr.test_lib import test_lib


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
