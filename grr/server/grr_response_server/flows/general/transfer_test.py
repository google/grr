#!/usr/bin/env python
"""Test the file transfer mechanism."""

import hashlib
import os
import platform
import unittest

from grr.lib import constants
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.flows.general import transfer
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# pylint:mode=test


class ClientMock(object):

  BUFFER_SIZE = 1024 * 1024

  def __init__(self, mbr_data=None, client_id=None):
    self.mbr = mbr_data
    self.client_id = client_id

  def ReadBuffer(self, args):
    return_data = self.mbr[args.offset:args.offset + args.length]
    return [
        rdf_client.BufferReference(
            data=return_data, offset=args.offset, length=len(return_data))
    ]


class TestTransfer(flow_test_lib.FlowTestsBaseclass):
  """Test the transfer mechanism."""
  maxDiff = 65 * 1024
  mbr = ("123456789" * 1000)[:4096]

  def setUp(self):
    super(TestTransfer, self).setUp()
    self.client_id = self.SetupClient(0)

    # Set suitable defaults for testing
    self.old_window_size = transfer.GetFile.WINDOW_SIZE
    self.old_chunk_size = transfer.GetFile.CHUNK_SIZE
    transfer.GetFile.WINDOW_SIZE = 10
    transfer.GetFile.CHUNK_SIZE = 600 * 1024

  def tearDown(self):
    super(TestTransfer, self).tearDown()

    transfer.GetFile.WINDOW_SIZE = self.old_window_size
    transfer.GetFile.CHUNK_SIZE = self.old_chunk_size

  def testGetMBR(self):
    """Test that the GetMBR flow works."""

    flow_test_lib.TestFlowHelper(
        transfer.GetMBR.__name__,
        ClientMock(self.mbr),
        token=self.token,
        client_id=self.client_id)

    fd = aff4.FACTORY.Open(self.client_id.Add("mbr"), token=self.token)
    self.assertEqual(fd.Read(4096), self.mbr)

  def _RunAndCheck(self, chunk_size, download_length):

    with utils.Stubber(constants, "CLIENT_MAX_BUFFER_SIZE", chunk_size):
      flow_test_lib.TestFlowHelper(
          transfer.GetMBR.__name__,
          ClientMock(self.mbr),
          token=self.token,
          client_id=self.client_id,
          length=download_length)

      fd = aff4.FACTORY.Open(self.client_id.Add("mbr"), token=self.token)
      self.assertEqual(fd.Read(download_length), self.mbr[:download_length])
      aff4.FACTORY.Delete(fd.urn, token=self.token)

  def testGetMBRChunked(self):

    chunk_size = 100
    download_length = 15 * chunk_size
    self._RunAndCheck(chunk_size, download_length)

    # Not a multiple of the chunk size.
    download_length = 15 * chunk_size + chunk_size / 2
    self._RunAndCheck(chunk_size, download_length)

  def testGetFile(self):
    """Test that the GetFile flow works."""

    client_mock = action_mocks.GetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    flow_test_lib.TestFlowHelper(
        transfer.GetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        pathspec=pathspec)

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")
    # Test the AFF4 file that was created.
    urn = pathspec.AFF4Path(self.client_id)
    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(pathspec.path, "rb")
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))
    self.CompareFDs(fd1, fd2)

  def testGetFilePathCorrection(self):
    """Tests that the pathspec returned is used for the aff4path."""
    client_mock = action_mocks.GetFileClientMock()
    # Deliberately using the wrong casing.
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "TEST_IMG.dd"))

    session_id = flow_test_lib.TestFlowHelper(
        transfer.GetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        pathspec=pathspec)

    results = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(results), 1)
    res_pathspec = results[0].pathspec

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")
    # Test the AFF4 file that was created.
    urn = res_pathspec.AFF4Path(self.client_id)
    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(res_pathspec.path, "rb")
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))
    self.CompareFDs(fd1, fd2)

  @unittest.skipUnless(platform.system() == "Linux",
                       "/proc only exists on Linux")
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
    client_mock = action_mocks.MultiGetFileClientMock()

    # # Create a zero sized file.
    zero_sized_filename = os.path.join(self.temp_dir, "zero_size")
    with open(zero_sized_filename, "wb") as fd:
      pass

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=zero_sized_filename)

    flow_test_lib.TestFlowHelper(
        transfer.MultiGetFile.__name__,
        client_mock,
        token=self.token,
        file_size="1MiB",
        client_id=self.client_id,
        pathspecs=[pathspec])

    # Now if we try to fetch a real /proc/ filename this will fail because the
    # filestore already contains the zero length file
    # aff4:/files/nsrl/da39a3ee5e6b4b0d3255bfef95601890afd80709.
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path="/proc/self/environ")

    flow_test_lib.TestFlowHelper(
        transfer.MultiGetFile.__name__,
        client_mock,
        token=self.token,
        file_size=1024 * 1024,
        client_id=self.client_id,
        pathspecs=[pathspec])

    data = open(pathspec.last.path, "rb").read()

    # Test the AFF4 file that was created - it should be empty since by default
    # we judge the file size based on its stat.st_size.
    urn = pathspec.AFF4Path(self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.size, len(data))
    self.assertMultiLineEqual(fd.read(len(data)), data)

  def CompareFDs(self, fd1, fd2):
    # Seek the files to the end to make sure they are the same size.
    fd2.seek(0, 2)
    fd1.seek(0, 2)
    self.assertEqual(fd2.tell(), fd1.tell())

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

    client_mock = action_mocks.MultiGetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    args = transfer.MultiGetFileArgs(pathspecs=[pathspec, pathspec])
    with test_lib.Instrument(transfer.MultiGetFile,
                             "StoreStat") as storestat_instrument:
      flow_test_lib.TestFlowHelper(
          transfer.MultiGetFile.__name__,
          client_mock,
          token=self.token,
          client_id=self.client_id,
          args=args)

      # We should only have called StoreStat once because the two paths
      # requested were identical.
      self.assertEqual(len(storestat_instrument.args), 1)

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")
    # Test the AFF4 file that was created.
    urn = pathspec.AFF4Path(self.client_id)
    fd1 = aff4.FACTORY.Open(urn, token=self.token)
    fd2 = open(pathspec.path, "rb")
    fd2.seek(0, 2)

    self.assertEqual(fd2.tell(), int(fd1.Get(fd1.Schema.SIZE)))
    self.CompareFDs(fd1, fd2)

  def testMultiGetFileMultiFiles(self):
    """Test MultiGetFile downloading many files at once."""
    client_mock = action_mocks.MultiGetFileClientMock()

    pathspecs = []
    # Make 30 files to download.
    for i in xrange(30):
      path = os.path.join(self.temp_dir, "test_%s.txt" % i)
      with open(path, "wb") as fd:
        fd.write("Hello")

      pathspecs.append(
          rdf_paths.PathSpec(
              pathtype=rdf_paths.PathSpec.PathType.OS, path=path))

    args = transfer.MultiGetFileArgs(
        pathspecs=pathspecs, maximum_pending_files=10)
    for session_id in flow_test_lib.TestFlowHelper(
        transfer.MultiGetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        args=args):
      # Check up on the internal flow state.
      flow_obj = aff4.FACTORY.Open(session_id, mode="r", token=self.token)
      flow_state = flow_obj.state
      # All the pathspecs should be in this list.
      self.assertEqual(len(flow_state.indexed_pathspecs), 30)

      # At any one time, there should not be more than 10 files or hashes
      # pending.
      self.assertLessEqual(len(flow_state.pending_files), 10)
      self.assertLessEqual(len(flow_state.pending_hashes), 10)

    # When we finish there should be no pathspecs stored in the flow state.
    for flow_pathspec in flow_state.indexed_pathspecs:
      self.assertIsNone(flow_pathspec)
    for flow_request_data in flow_state.request_data_list:
      self.assertIsNone(flow_request_data)

    # Now open each file and make sure the data is there.
    for pathspec in pathspecs:
      urn = pathspec.AFF4Path(self.client_id)
      fd = aff4.FACTORY.Open(urn, token=self.token)
      self.assertEqual("Hello", fd.read())

  def testMultiGetFileDeduplication(self):
    client_mock = action_mocks.MultiGetFileClientMock()

    pathspecs = []
    # Make 10 files to download.
    for i in xrange(10):
      path = os.path.join(self.temp_dir, "test_%s.txt" % i)
      with open(path, "wb") as fd:
        fd.write("Hello")

      pathspecs.append(
          rdf_paths.PathSpec(
              pathtype=rdf_paths.PathSpec.PathType.OS, path=path))

    # All those files are the same so the individual chunks should
    # only be downloaded once. By forcing maximum_pending_files=1,
    # there should only be a single TransferBuffer call.
    args = transfer.MultiGetFileArgs(
        pathspecs=pathspecs, maximum_pending_files=1)
    flow_test_lib.TestFlowHelper(
        transfer.MultiGetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        args=args)

    self.assertEqual(client_mock.action_counts["TransferBuffer"], 1)

  def testMultiGetFileSetsFileHashAttributeWhenMultipleChunksDownloaded(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"))

    args = transfer.MultiGetFileArgs(pathspecs=[pathspec])
    flow_test_lib.TestFlowHelper(
        transfer.MultiGetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        args=args)

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")
    # Test the AFF4 file that was created.
    urn = pathspec.AFF4Path(self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    fd_hash = fd.Get(fd.Schema.HASH)

    self.assertTrue(fd_hash)

    h = hashlib.sha256()
    with open(os.path.join(self.base_path, "test_img.dd"), "rb") as model_fd:
      h.update(model_fd.read())
    self.assertEqual(fd_hash.sha256, h.digest())

  def testMultiGetFileSizeLimit(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    image_path = os.path.join(self.base_path, "test_img.dd")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=image_path)

    # Read a bit more than one chunk (600 * 1024).
    expected_size = 750 * 1024
    args = transfer.MultiGetFileArgs(
        pathspecs=[pathspec], file_size=expected_size)
    flow_test_lib.TestFlowHelper(
        transfer.MultiGetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        args=args)

    urn = pathspec.AFF4Path(self.client_id)
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


class TestTransferRelational(db_test_lib.RelationalDBEnabledMixin,
                             TestTransfer):
  pass


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
