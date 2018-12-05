#!/usr/bin/env python
"""Tests for the filestore stats."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_server import aff4
from grr_response_server.aff4_objects import filestore as aff4_filestore
from grr_response_server.flows.cron import filestore_stats
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class FilestoreStatsCronFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Tests for the filestore stats."""

  def setUp(self):
    super(FilestoreStatsCronFlowTest, self).setUp()

    fs = aff4.FACTORY.Open("aff4:/files", token=self.token)

    for i in range(0, 10):
      with aff4.FACTORY.Create(
          "aff4:/files/hash/generic/sha256/fsi%s" % i,
          aff4_filestore.FileStoreImage,
          token=self.token) as newfd:
        newfd.size = i * 1e6

      fake_hash = "fsi%s" % i
      for j in range(0, i):
        fs.AddURNToIndex(fake_hash,
                         "aff4:/C.000000000000000%s/fs/os/blah%s" % (j, j))

    with aff4.FACTORY.Create(
        "aff4:/files/hash/generic/sha256/blobbig",
        aff4_filestore.FileStoreImage,
        token=self.token) as newfd:
      newfd.size = 1e12

    fs.AddURNToIndex("blobbig", "aff4:/C.0000000000000001/fs/os/1")
    fs.AddURNToIndex("blobbig", "aff4:/C.0000000000000001/fs/os/2")

    with aff4.FACTORY.Create(
        "aff4:/files/hash/generic/sha256/blobtiny",
        aff4_filestore.FileStoreImage,
        token=self.token) as newfd:
      newfd.size = 12

    fs.AddURNToIndex("blobtiny", "aff4:/C.0000000000000001/fs/os/1")

  def testFileTypes(self):
    flow_test_lib.TestFlowHelper(
        filestore_stats.FilestoreStatsCronFlow.__name__, token=self.token)

    fd = aff4.FACTORY.Open(
        filestore_stats.FilestoreStatsCronFlow.FILESTORE_STATS_URN,
        token=self.token)

    filetypes = fd.Get(fd.Schema.FILESTORE_FILETYPES)
    self.assertLen(filetypes, 1)
    self.assertEqual(filetypes.data[0].label, "FileStoreImage")
    self.assertEqual(filetypes.data[0].y_value, 12)

    filetype_size = fd.Get(fd.Schema.FILESTORE_FILETYPES_SIZE)
    self.assertEqual(filetype_size.data[0].label, "FileStoreImage")
    self.assertEqual(filetype_size.data[0].y_value, 931.364501953125)

    filesizes = fd.Get(fd.Schema.FILESTORE_FILESIZE_HISTOGRAM)
    self.assertEqual(filesizes.data[0].x_value, 0)
    self.assertEqual(filesizes.data[0].y_value, 1)
    self.assertEqual(filesizes.data[1].x_value, 2)
    self.assertEqual(filesizes.data[1].y_value, 1)
    self.assertEqual(filesizes.data[8].x_value, 1000000)
    self.assertEqual(filesizes.data[8].y_value, 4)
    self.assertEqual(filesizes.data[9].x_value, 5000000)
    self.assertEqual(filesizes.data[9].y_value, 5)
    self.assertEqual(filesizes.data[-1].y_value, 1)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
