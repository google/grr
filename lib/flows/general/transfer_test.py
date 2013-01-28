#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Test the file transfer mechanism."""


import os
import re

from grr.client import conf as flags

from grr.client.client_actions import standard
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.flows.general import transfer

FLAGS = flags.FLAGS


class TestTransfer(test_lib.FlowTestsBaseclass):
  """Test the transfer mechanism."""

  def setUp(self):
    super(TestTransfer, self).setUp()

    # Set suitable defaults for testing
    self.old_window_size = transfer.GetFile._WINDOW_SIZE
    self.old_chunk_size = transfer.GetFile._CHUNK_SIZE
    transfer.GetFile._WINDOW_SIZE = 10
    transfer.GetFile._CHUNK_SIZE = 600 * 1024

    # We wiped the data_store so we have to retransmit all blobs.
    standard.HASH_CACHE = utils.FastStore(100)

  def tearDown(self):
    super(TestTransfer, self).tearDown()

    transfer.GetFile._WINDOW_SIZE = self.old_window_size
    transfer.GetFile._CHUNK_SIZE = self.old_chunk_size

  def testGetMBR(self):
    """Test that the GetMBR flow works."""

    mbr = ("123456789" * 1000)[:4096]

    class ClientMock(object):

      def ReadBuffer(self, args):
        _ = args
        return [
            rdfvalue.BufferReference(
                data=mbr, offset=0, length=len(mbr))]

    for _ in test_lib.TestFlowHelper("GetMBR", ClientMock(), token=self.token,
                                     client_id=self.client_id):
      pass

    fd = aff4.FACTORY.Open("aff4:/%s/mbr" % self.client_id,
                           token=self.token)
    self.assertEqual(fd.Read(4096), mbr)

  def testGetFile(self):
    """Test that the GetFile flow works."""

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile")
    pathspec = rdfvalue.RDFPathSpec(
        pathtype=rdfvalue.RDFPathSpec.Enum("OS"),
        path=os.path.join(self.base_path, "test_img.dd"))

    for _ in test_lib.TestFlowHelper("GetFile", client_mock, token=self.token,
                                     client_id=self.client_id,
                                     pathspec=pathspec):
      pass

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")
    # Test the AFF4 file that was created.
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(pathspec.path)
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))
    self.CompareFDs(fd1, fd2)

  def CompareFDs(self, fd1, fd2):
    ranges = [
        # Start of file
        (0, 100),
        # Straddle the first chunk
        (16 * 1024 - 100, 300),
        # Read past end of file
        (fd2.tell() - 100, 300),
        # Zero length reads
        (100, 0),
        ]

    for offset, length in ranges:
      fd1.Seek(offset)
      data1 = fd1.Read(length)

      fd2.seek(offset)
      data2 = fd2.read(length)
      self.assertEqual(data1, data2)

  def testFastGetFile(self):
    """Test that the FastGetFile flow works."""

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile",
                                      "HashBuffer")
    pathspec = rdfvalue.RDFPathSpec(
        pathtype=rdfvalue.RDFPathSpec.Enum("OS"),
        path=os.path.join(self.base_path, "test_img.dd"))

    for _ in test_lib.TestFlowHelper("FastGetFile", client_mock,
                                     token=self.token,
                                     client_id=self.client_id,
                                     pathspec=pathspec):
      pass

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")

    # Test the AFF4 file that was created.
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(pathspec.path)
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))
    self.CompareFDs(fd1, fd2)

    # Should have transferred 21 buffers.
    self.assertEqual(client_mock.action_counts["TransferBuffer"], 21)

    # Now get the same file again and check that its faster.
    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile",
                                      "HashBuffer")

    # Make sure we remove the old version completely.
    aff4.FACTORY.Delete(urn, token=self.token)

    # Remove one of the hash blobs.
    aff4.FACTORY.Delete("aff4:/blobs/02303d0cb2f7fe70b933f2e83033d73de27"
                        "fed291560fd0116389de37ca8eaab", token=self.token)

    for _ in test_lib.TestFlowHelper("FastGetFile", client_mock,
                                     token=self.token,
                                     client_id=self.client_id,
                                     pathspec=pathspec):
      pass

    # Should have transferred exactly 1 buffer and Hashed 21.
    self.assertEqual(client_mock.action_counts["TransferBuffer"], 1)
    self.assertEqual(client_mock.action_counts["HashBuffer"], 21)

    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(pathspec.path)
    fd2.seek(0, 2)

    self.CompareFDs(fd1, fd2)


class TestFileCollector(test_lib.FlowTestsBaseclass):
  """Test that a CollectionFlow works."""

  def setUp(self):
    super(TestFileCollector, self).setUp()

    # Set suitable defaults for testing
    self.old_window_size = transfer.GetFile._WINDOW_SIZE
    self.old_chunk_size = transfer.GetFile._CHUNK_SIZE
    transfer.GetFile._WINDOW_SIZE = 10
    transfer.GetFile._CHUNK_SIZE = 100 * 1024

    # We wiped the data_store so we have to retransmit all blobs.
    standard.HASH_CACHE = utils.FastStore(100)

  def tearDown(self):
    super(TestFileCollector, self).tearDown()

    transfer.GetFile._WINDOW_SIZE = self.old_window_size
    transfer.GetFile._CHUNK_SIZE = self.old_chunk_size

  def testCollectFiles(self):
    """Test that files are collected."""

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find")

    output_path = "analysis/MyDownloadedFiles"

    for _ in test_lib.TestFlowHelper("TestCollector", client_mock,
                                     token=self.token, client_id=self.client_id,
                                     output=output_path):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(
        "aff4:/{0}/{1}".format(self.client_id, output_path),
        token=self.token)
    file_re = re.compile("(ntfs_img.dd|sqlite)$")
    # Make sure that it is a file.
    actual_children = [c for c in os.listdir(self.base_path) if
                       file_re.search(c)]
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), len(actual_children))
    for child in children:
      path = utils.SmartStr(child.urn)
      self.assertTrue(file_re.search(path))
      child_fd = aff4.FACTORY.Open(path, token=self.token)
      self.assertTrue(isinstance(child_fd, aff4.AFF4Stream))


class TestCollector(transfer.FileCollector):
  """Test Inherited Collector Flow."""

  def __init__(self, **kwargs):
    """Define what we collect."""
    base_path = os.path.join(FLAGS.test_srcdir, FLAGS.test_datadir)
    findspec = rdfvalue.RDFFindSpec(
        path_regex="(ntfs_img.dd|sqlite)$", max_depth=4)

    findspec.pathspec.path = base_path
    findspec.pathspec.pathtype = rdfvalue.RDFPathSpec.Enum("OS")

    super(TestCollector, self).__init__(findspecs=[findspec], **kwargs)
