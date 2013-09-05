#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.standard."""

import StringIO


from grr.lib import aff4
from grr.lib import test_lib


class BlobImageTest(test_lib.GRRBaseTest):
  """Tests for cron functionality."""

  def testAppendContentError(self):
    src_content = "ABCD" * 10
    src_fd = StringIO.StringIO(src_content)

    dest_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp"),
                                  "BlobImage", token=self.token, mode="rw")
    dest_fd.SetChunksize(7)
    dest_fd.AppendContent(src_fd)
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content)

    src_fd.seek(0)
    self.assertRaises(IOError, dest_fd.AppendContent, src_fd)

  def testAppendContent(self):
    """Test writing content where content length % chunksize == 0."""
    src_content = "ABCDEFG" * 10  # 10 chunksize blobs
    src_fd = StringIO.StringIO(src_content)

    dest_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp"),
                                  "BlobImage", token=self.token, mode="rw")
    dest_fd.SetChunksize(7)
    dest_fd.AppendContent(src_fd)
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content)

    src_fd.seek(0)
    dest_fd.AppendContent(src_fd)
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content+src_content)




