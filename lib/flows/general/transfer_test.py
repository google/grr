#!/usr/bin/env python
"""Test the file transfer mechanism."""


import os


from grr.client.client_actions import standard
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.flows.general import transfer

# pylint:mode=test


class TestTransfer(test_lib.FlowTestsBaseclass):
  """Test the transfer mechanism."""

  def setUp(self):
    super(TestTransfer, self).setUp()

    # Set suitable defaults for testing
    self.old_window_size = transfer.GetFile.WINDOW_SIZE
    self.old_chunk_size = transfer.GetFile.CHUNK_SIZE
    transfer.GetFile.WINDOW_SIZE = 10
    transfer.GetFile.CHUNK_SIZE = 600 * 1024

    # We wiped the data_store so we have to retransmit all blobs.
    standard.HASH_CACHE = utils.FastStore(100)

  def tearDown(self):
    super(TestTransfer, self).tearDown()

    transfer.GetFile.WINDOW_SIZE = self.old_window_size
    transfer.GetFile.CHUNK_SIZE = self.old_chunk_size

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

    fd = aff4.FACTORY.Open(self.client_id.Add("mbr"), token=self.token)
    self.assertEqual(fd.Read(4096), mbr)

  def testGetFile(self):
    """Test that the GetFile flow works."""

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile")
    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
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

  def testGetFileWithZeroStat(self):
    """Test GetFile works on stat.st_size==0 files when read_length is set."""
    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    class ClientMock(action_mocks.ActionMock):

      def StatFile(self, _):
        # Return a stat response with no size.
        return [rdfvalue.StatEntry(st_size=0, pathspec=pathspec)]

    client_mock = ClientMock("TransferBuffer")

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)

    for _ in test_lib.TestFlowHelper("GetFile", client_mock, token=self.token,
                                     client_id=self.client_id,
                                     pathspec=pathspec):
      pass

    # Test the AFF4 file that was created - it should be empty since by default
    # we judge the file size based on its stat.st_size.
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.size, 0)

    for _ in test_lib.TestFlowHelper("GetFile", client_mock, token=self.token,
                                     client_id=self.client_id,
                                     read_length=2*1024*1024 + 5,
                                     pathspec=pathspec):
      pass

    # When we explicitly pass the read_length parameter we read more of the
    # file.
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.size, 2*1024*1024 + 5)

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

  def testMultiGetFile(self):
    """Test MultiGetFile."""

    client_mock = action_mocks.ActionMock("TransferBuffer", "FingerprintFile",
                                          "StatFile", "HashBuffer")
    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    args = rdfvalue.MultiGetFileArgs(pathspecs=[pathspec, pathspec])
    with test_lib.Instrument(
        transfer.MultiGetFile, "StoreStat") as storestat_instrument:
      for _ in test_lib.TestFlowHelper("MultiGetFile", client_mock,
                                       token=self.token,
                                       client_id=self.client_id, args=args):
        pass

      # We should only have called StoreStat once because the two paths
      # requested were identical.
      self.assertEqual(len(storestat_instrument.args), 1)

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")
    # Test the AFF4 file that was created.
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(pathspec.path)
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))
    self.CompareFDs(fd1, fd2)
