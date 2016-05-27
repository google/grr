#!/usr/bin/env python
"""Tests for grr.lib.flows.cron.filestore_stats."""

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import filestore as aff4_filestore
from grr.lib.flows.cron import filestore_stats


class FilestoreStatsCronFlowTest(test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(FilestoreStatsCronFlowTest, self).setUp()

    for i in range(0, 10):
      newfd = aff4.FACTORY.Create("aff4:/files/hash/generic/sha256/fsi%s" % i,
                                  aff4_filestore.FileStoreImage,
                                  token=self.token)
      newfd.size = i * 1e6
      for j in range(0, i):
        newfd.AddIndex("aff4:/C.000000000000000%s/fs/os/blah%s" % (j, j))
      newfd.Close()

    newfd = aff4.FACTORY.Create("aff4:/files/hash/generic/sha256/blobbig",
                                aff4_filestore.FileStoreImage,
                                token=self.token)
    newfd.size = 1e12
    newfd.AddIndex("aff4:/C.0000000000000001/fs/os/1")
    newfd.AddIndex("aff4:/C.0000000000000001/fs/os/2")
    newfd.Close()

    newfd = aff4.FACTORY.Create("aff4:/files/hash/generic/sha256/blobtiny",
                                aff4_filestore.FileStoreImage,
                                token=self.token)
    newfd.size = 12
    newfd.AddIndex("aff4:/C.0000000000000001/fs/os/1")
    newfd.Close()

  def testFileTypes(self):
    for _ in test_lib.TestFlowHelper("FilestoreStatsCronFlow",
                                     token=self.token):
      pass

    fd = aff4.FACTORY.Open(
        filestore_stats.FilestoreStatsCronFlow.FILESTORE_STATS_URN,
        token=self.token)

    filetypes = fd.Get(fd.Schema.FILESTORE_FILETYPES)
    self.assertEqual(len(filetypes), 1)
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

    clientcount = fd.Get(fd.Schema.FILESTORE_CLIENTCOUNT_HISTOGRAM)
    self.assertEqual(clientcount.data[0].x_value, 0)
    self.assertEqual(clientcount.data[0].y_value, 1)
    self.assertEqual(clientcount.data[1].x_value, 1)
    self.assertEqual(clientcount.data[1].y_value, 6)
    self.assertEqual(clientcount.data[2].x_value, 5)
    self.assertEqual(clientcount.data[2].y_value, 5)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
