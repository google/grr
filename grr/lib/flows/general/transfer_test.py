#!/usr/bin/env python
"""Test the file transfer mechanism."""


import hashlib
import os

from grr.client.client_actions import standard
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths

# pylint:mode=test


class TestTransfer(test_lib.FlowTestsBaseclass):
  """Test the transfer mechanism."""
  maxDiff = 65 * 1024

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
        return [rdf_client.BufferReference(data=mbr, offset=0, length=len(mbr))]

    for _ in test_lib.TestFlowHelper("GetMBR",
                                     ClientMock(),
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add("mbr"), token=self.token)
    self.assertEqual(fd.Read(4096), mbr)

  def testGetFile(self):
    """Test that the GetFile flow works."""

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    for _ in test_lib.TestFlowHelper("GetFile",
                                     client_mock,
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

  def testMultiGetFileOfSpecialFiles(self):
    """Test that special /proc/ files are handled correctly.

    /proc/ files have the property that they are non seekable from their end
    (i.e. seeking them relative to the end is not supported). They also return
    an st_size of 0. For example:

    $ stat /proc/self/maps
    File: '/proc/self/maps'
    Size: 0   Blocks: 0   IO Block: 1024 regular empty file

    $ head /proc/self/maps
    00400000-00409000 r-xp 00000000 fc:01 9180740 /usr/bin/head
    00608000-00609000 r--p 00008000 fc:01 9180740 /usr/bin/head
    ...

    When we try to use the MultiGetFile flow, it deduplicates the files and
    since it thinks the file has a zero size, the flow will not download the
    file, and instead copy the zero size file into it.
    """
    client_mock = action_mocks.ActionMock("TransferBuffer", "HashFile",
                                          "HashBuffer", "StatFile")

    # # Create a zero sized file.
    zero_sized_filename = os.path.join(self.temp_dir, "zero_size")
    with open(zero_sized_filename, "wb") as fd:
      pass

    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS,
                                  path=zero_sized_filename)

    for _ in test_lib.TestFlowHelper("MultiGetFile",
                                     client_mock,
                                     token=self.token,
                                     file_size="1MiB",
                                     client_id=self.client_id,
                                     pathspecs=[pathspec]):
      pass

    # Now if we try to fetch a real /proc/ filename this will fail because the
    # filestore already contains the zero length file
    # aff4:/files/nsrl/da39a3ee5e6b4b0d3255bfef95601890afd80709.
    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS,
                                  path="/proc/self/environ")

    for _ in test_lib.TestFlowHelper("MultiGetFile",
                                     client_mock,
                                     token=self.token,
                                     file_size=1024 * 1024,
                                     client_id=self.client_id,
                                     pathspecs=[pathspec]):
      pass

    data = open(pathspec.last.path).read()

    # Test the AFF4 file that was created - it should be empty since by default
    # we judge the file size based on its stat.st_size.
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.size, len(data))
    self.assertMultiLineEqual(fd.read(len(data)), data)

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

    client_mock = action_mocks.ActionMock("TransferBuffer", "HashFile",
                                          "StatFile", "HashBuffer")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    args = transfer.MultiGetFileArgs(pathspecs=[pathspec, pathspec])
    with test_lib.Instrument(transfer.MultiGetFile,
                             "StoreStat") as storestat_instrument:
      for _ in test_lib.TestFlowHelper("MultiGetFile",
                                       client_mock,
                                       token=self.token,
                                       client_id=self.client_id,
                                       args=args):
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

  def testMultiGetFileSetsFileHashAttributeWhenMultipleChunksDownloaded(self):
    client_mock = action_mocks.ActionMock("TransferBuffer", "HashFile",
                                          "StatFile", "HashBuffer")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    args = transfer.MultiGetFileArgs(pathspecs=[pathspec])
    for _ in test_lib.TestFlowHelper("MultiGetFile",
                                     client_mock,
                                     token=self.token,
                                     client_id=self.client_id,
                                     args=args):
      pass

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")
    # Test the AFF4 file that was created.
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    fd_hash = fd.Get(fd.Schema.HASH)

    self.assertTrue(fd_hash)

    h = hashlib.sha256()
    with open(os.path.join(self.base_path, "test_img.dd")) as model_fd:
      h.update(model_fd.read())
    self.assertEqual(fd_hash.sha256, h.digest())

  def testMultiGetFileSizeLimit(self):
    client_mock = action_mocks.ActionMock("TransferBuffer", "HashFile",
                                          "StatFile", "HashBuffer")
    image_path = os.path.join(self.base_path, "test_img.dd")
    pathspec = rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS,
                                  path=image_path)

    # Read a bit more than one chunk (600 * 1024).
    expected_size = 750 * 1024
    args = transfer.MultiGetFileArgs(pathspecs=[pathspec],
                                     file_size=expected_size)
    for _ in test_lib.TestFlowHelper("MultiGetFile",
                                     client_mock,
                                     token=self.token,
                                     client_id=self.client_id,
                                     args=args):
      pass

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    blobimage = aff4.FACTORY.Open(urn, token=self.token)
    # Make sure a VFSBlobImage got written.
    self.assertTrue(isinstance(blobimage, aff4_grr.VFSBlobImage))

    self.assertEqual(len(blobimage), expected_size)
    data = blobimage.read(100 * expected_size)
    self.assertEqual(len(data), expected_size)

    expected_data = open(image_path, "rb").read(expected_size)

    self.assertEqual(data, expected_data)
    hash_obj = blobimage.Get(blobimage.Schema.HASH)

    d = hashlib.sha1()
    d.update(expected_data)
    expected_hash = d.hexdigest()

    self.assertEqual(hash_obj.sha1, expected_hash)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
