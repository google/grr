#!/usr/bin/env python
"""Test the file transfer mechanism."""

import hashlib
import io
import os
import platform
import stat
import struct
import unittest
from unittest import mock

from absl import app

from grr_response_core.lib import constants
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_core.lib.util import text
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import config_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import mig_transfer
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2

# pylint:mode=test


class ClientMock(action_mocks.ActionMock):

  BUFFER_SIZE = 1024 * 1024

  def __init__(self, mbr_data=None, client_id=None):
    self.mbr = mbr_data
    self.client_id = client_id

  def ReadBuffer(self, args):
    return_data = self.mbr[args.offset : args.offset + args.length]
    return [
        rdf_client.BufferReference(
            data=return_data, offset=args.offset, length=len(return_data)
        )
    ]


class GetMBRFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the transfer mechanism."""

  mbr = (b"123456789" * 1000)[:4096]

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testGetMBR(self):
    """Test that the GetMBR flow works."""

    flow_id = flow_test_lib.StartAndRunFlow(
        transfer.GetMBR,
        ClientMock(self.mbr),
        creator=self.test_username,
        client_id=self.client_id,
    )

    results = data_store.REL_DB.ReadFlowResults(self.client_id, flow_id, 0, 10)
    self.assertLen(results, 1)
    result = config_pb2.BytesValue()
    result.ParseFromString(results[0].payload.value)
    self.assertEqual(result.value, self.mbr)

  def _RunAndCheck(self, chunk_size, download_length):

    with mock.patch.object(constants, "CLIENT_MAX_BUFFER_SIZE", chunk_size):
      flow_id = flow_test_lib.StartAndRunFlow(
          transfer.GetMBR,
          ClientMock(self.mbr),
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=transfer.GetMBRArgs(length=download_length),
      )

    results = data_store.REL_DB.ReadFlowResults(self.client_id, flow_id, 0, 10)
    self.assertLen(results, 1)
    result = config_pb2.BytesValue()
    result.ParseFromString(results[0].payload.value)
    self.assertEqual(result.value, self.mbr[:download_length])

  def testGetMBRChunked(self):

    chunk_size = 100
    download_length = 15 * chunk_size
    self._RunAndCheck(chunk_size, download_length)

    # Not a multiple of the chunk size.
    download_length = 15 * chunk_size + chunk_size // 2
    self._RunAndCheck(chunk_size, download_length)


class CompareFDsMixin(object):

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
      fd1.seek(offset)
      data1 = fd1.read(length)

      fd2.seek(offset)
      data2 = fd2.read(length)
      self.assertEqual(data1, data2)


class MultiGetFileFlowTest(CompareFDsMixin, flow_test_lib.FlowTestsBaseclass):
  """Test the transfer mechanism."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  @unittest.skipUnless(
      platform.system() == "Linux", "/proc only exists on Linux"
  )
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
    with open(zero_sized_filename, "wb"):
      pass

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=zero_sized_filename
    )

    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=transfer.MultiGetFileArgs(
            file_size="1MiB", pathspecs=[pathspec]
        ),
    )

    # Now if we try to fetch a real /proc/ filename this will fail because the
    # filestore already contains the zero length file
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path="/proc/self/environ"
    )

    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=transfer.MultiGetFileArgs(
            pathspecs=[pathspec],
            file_size=1024 * 1024,
        ),
    )

    with open(pathspec.last.path, "rb") as fd:
      data = fd.read()

    cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
    fd_rel_db = file_store.OpenFile(cp)
    self.assertEqual(fd_rel_db.size, len(data))
    self.assertEqual(fd_rel_db.read(), data)

    # Check that SHA256 hash of the file matches the contents
    # hash and that MD5 and SHA1 are set.
    history = data_store.REL_DB.ReadPathInfoHistory(
        cp.client_id, cp.path_type, cp.components
    )
    self.assertEqual(history[-1].hash_entry.sha256, fd_rel_db.hash_id.AsBytes())
    self.assertEqual(history[-1].hash_entry.num_bytes, len(data))
    self.assertIsNotNone(history[-1].hash_entry.sha1)
    self.assertIsNotNone(history[-1].hash_entry.md5)

  def testMultiGetFile(self):
    """Test MultiGetFile."""

    client_mock = action_mocks.MultiGetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"),
    )
    expected_size = os.path.getsize(pathspec.path)

    args = transfer.MultiGetFileArgs(pathspecs=[pathspec, pathspec])
    with test_lib.Instrument(
        transfer.MultiGetFile, "_ReceiveFileStat"
    ) as receivestat_instrument:
      flow_test_lib.StartAndRunFlow(
          transfer.MultiGetFile,
          client_mock,
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=args,
      )

      # We should only have called StoreStat once because the two paths
      # requested were identical.
      self.assertLen(receivestat_instrument.args, 1)

    # Fix path for Windows testing.
    pathspec.path = pathspec.path.replace("\\", "/")

    with open(pathspec.path, "rb") as fd2:
      # Test the file that was created.
      cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
      fd_rel_db = file_store.OpenFile(cp)
      self.CompareFDs(fd2, fd_rel_db)

    # Check that SHA256 hash of the file matches the contents
    # hash and that MD5 and SHA1 are set.
    history = data_store.REL_DB.ReadPathInfoHistory(
        cp.client_id, cp.path_type, cp.components
    )
    self.assertEqual(history[-1].hash_entry.sha256, fd_rel_db.hash_id.AsBytes())
    self.assertEqual(history[-1].hash_entry.num_bytes, expected_size)
    self.assertIsNotNone(history[-1].hash_entry.sha1)
    self.assertIsNotNone(history[-1].hash_entry.md5)

  def testMultiGetFile_StopAtStat_CallsClientOnce(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"),
    )
    args = transfer.MultiGetFileArgs(
        pathspecs=[pathspec, pathspec],
        stop_at=transfer.MultiGetFileArgs.StopAt.STAT,
    )

    with mock.patch.object(
        flow_base.FlowBase, "CallClientProto"
    ) as mock_call_client:
      flow_id = flow_test_lib.StartAndRunFlow(
          transfer.MultiGetFile,
          client_mock,
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=args,
      )
    mock_call_client.assert_called_once()
    mock_call_client.assert_called_with(
        server_stubs.GetFileStat,
        mock.ANY,
        next_state=mock.ANY,
        request_data=mock.ANY,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(
        flow_obj.flow_state, rdf_flow_objects.Flow.FlowState.FINISHED
    )

  def testMultiGetFile_StopAtStat_Results(self):
    client_mock = action_mocks.MultiGetFileClientMock()

    with temp.AutoTempDirPath(remove_non_empty=True) as tmp_path:
      file_foo_path = os.path.join(tmp_path, "foo")
      with open(file_foo_path, "wb") as fd:
        fd.write(b"foo")
      expected_size = os.path.getsize(file_foo_path)
      pathspec = rdf_paths.PathSpec(
          path=file_foo_path,
          pathtype=rdf_paths.PathSpec.PathType.OS,
      )
      args = transfer.MultiGetFileArgs(
          pathspecs=[pathspec, pathspec],
          stop_at=transfer.MultiGetFileArgs.StopAt.STAT,
      )
      flow_id = flow_test_lib.StartAndRunFlow(
          transfer.MultiGetFile,
          client_mock,
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=args,
      )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(
        flow_obj.flow_state, rdf_flow_objects.Flow.FlowState.FINISHED
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].pathspec.path, file_foo_path)
    self.assertEqual(
        results[0].pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
    )
    self.assertEqual(results[0].st_size, expected_size)

    # While MultiGetFile only returns the `stat_entry`, we count on the
    # path info being written to the file store.
    cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
    self.assertRaises(file_store.FileHasNoContentError, file_store.OpenFile, cp)

    history = data_store.REL_DB.ReadPathInfoHistory(
        cp.client_id, cp.path_type, cp.components
    )
    self.assertLen(history, 1)
    self.assertEqual(history[0].components[-1], "foo")
    self.assertTrue(history[0].HasField("stat_entry"))
    self.assertEqual(
        history[0].stat_entry, mig_client_fs.ToProtoStatEntry(results[0])
    )
    self.assertFalse(history[0].HasField("hash_entry"))

  def testMultiGetFile_StopAtHash_CallsClientTwice(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"),
    )
    args = transfer.MultiGetFileArgs(
        pathspecs=[pathspec, pathspec],
        stop_at=transfer.MultiGetFileArgs.StopAt.HASH,
    )

    with mock.patch.object(
        flow_base.FlowBase, "CallClientProto"
    ) as mock_call_client:
      flow_id = flow_test_lib.StartAndRunFlow(
          transfer.MultiGetFile,
          client_mock,
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=args,
      )
    self.assertEqual(mock_call_client.call_count, 2)
    self.assertCountEqual(
        [
            mock.call(
                server_stubs.GetFileStat,
                mock.ANY,
                next_state=mock.ANY,
                request_data=mock.ANY,
            ),
            mock.call(
                server_stubs.HashFile,
                mock.ANY,
                next_state=mock.ANY,
                request_data=mock.ANY,
            ),
        ],
        mock_call_client.mock_calls,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(
        flow_obj.flow_state, rdf_flow_objects.Flow.FlowState.FINISHED
    )

  def testMultiGetFile_StopAtHash_Results(self):
    client_mock = action_mocks.MultiGetFileClientMock()

    with temp.AutoTempDirPath(remove_non_empty=True) as tmp_path:
      file_foo_path = os.path.join(tmp_path, "foo")
      with open(file_foo_path, "wb") as fd:
        fd.write(b"foo")
      expected_size = os.path.getsize(file_foo_path)
      pathspec = rdf_paths.PathSpec(
          path=file_foo_path,
          pathtype=rdf_paths.PathSpec.PathType.OS,
      )
      args = transfer.MultiGetFileArgs(
          pathspecs=[pathspec, pathspec],
          stop_at=transfer.MultiGetFileArgs.StopAt.HASH,
      )
      flow_id = flow_test_lib.StartAndRunFlow(
          transfer.MultiGetFile,
          client_mock,
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=args,
      )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(
        flow_obj.flow_state, rdf_flow_objects.Flow.FlowState.FINISHED
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].pathspec.path, file_foo_path)
    self.assertEqual(
        results[0].pathspec.pathtype, rdf_paths.PathSpec.PathType.OS
    )
    self.assertEqual(results[0].st_size, expected_size)

    # While MultiGetFile only returns the `stat_entry`, we count on the
    # path info being written to the file store.
    cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
    self.assertRaises(file_store.FileHasNoContentError, file_store.OpenFile, cp)

    history = data_store.REL_DB.ReadPathInfoHistory(
        cp.client_id, cp.path_type, cp.components
    )
    self.assertLen(history, 1)
    self.assertEqual(history[0].components[-1], "foo")
    self.assertTrue(history[0].HasField("stat_entry"))
    self.assertEqual(
        history[0].stat_entry, mig_client_fs.ToProtoStatEntry(results[0])
    )
    self.assertTrue(history[0].HasField("hash_entry"))
    self.assertEqual(
        text.Hexify(history[0].hash_entry.sha1),
        hashlib.sha1(b"foo").hexdigest(),
    )
    self.assertEqual(
        text.Hexify(history[0].hash_entry.sha256),
        hashlib.sha256(b"foo").hexdigest(),
    )
    self.assertEqual(
        text.Hexify(history[0].hash_entry.md5), hashlib.md5(b"foo").hexdigest()
    )

  # Setting MIN_CALL_TO_FILE_STORE to a smaller value emulates MultiGetFile's
  # behavior when dealing with large files.
  @mock.patch.object(transfer.MultiGetFile, "MIN_CALL_TO_FILE_STORE", 1)
  def testMultiGetFileCorrectlyFetchesSameFileMultipleTimes(self):
    """Test MultiGetFile."""

    client_mock = action_mocks.MultiGetFileClientMock()

    total_num_chunks = 10
    total_size = transfer.MultiGetFile.CHUNK_SIZE * total_num_chunks
    path = os.path.join(self.temp_dir, "test_big.txt")
    with io.open(path, "wb") as fd:
      for i in range(total_num_chunks):
        fd.write(struct.pack("b", i) * transfer.MultiGetFile.CHUNK_SIZE)

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=path
    )

    def _Check(expected_size):
      args = transfer.MultiGetFileArgs(
          pathspecs=[pathspec], file_size=expected_size
      )
      flow_test_lib.StartAndRunFlow(
          transfer.MultiGetFile,
          client_mock,
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=args,
      )

      # Test the file that was created.
      cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
      fd = file_store.OpenFile(cp)
      self.assertEqual(fd.size, expected_size)

    # Fetch the file twice to test a real-world scenario when a file is first
    # fetched with a smaller limit, and then - with a bigger one.
    # This tests against a bug in MultiGetFileLogic when first N chunks of
    # the file were already fetched during a previous MultiGetFileLogic run,
    # and as a consequence the file was considered fully fetched, even if
    # the max_file_size value of the current run was much bigger than
    # the size of the previously fetched file.
    _Check(transfer.MultiGetFile.CHUNK_SIZE * 2)
    _Check(total_size)

  def testMultiGetFileMultiFiles(self):
    """Test MultiGetFile downloading many files at once."""
    client_mock = action_mocks.MultiGetFileClientMock()

    pathspecs = []
    # Make 30 files to download.
    for i in range(30):
      path = os.path.join(self.temp_dir, "test_%s.txt" % i)
      with io.open(path, "wb") as fd:
        fd.write(b"Hello")

      pathspecs.append(
          rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS, path=path)
      )

    args = transfer.MultiGetFileArgs(
        pathspecs=pathspecs, maximum_pending_files=10
    )
    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )

    # Now open each file and make sure the data is there.
    for pathspec in pathspecs:
      cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
      fd_rel_db = file_store.OpenFile(cp)
      self.assertEqual(b"Hello", fd_rel_db.read())

      # Check that SHA256 hash of the file matches the contents
      # hash and that MD5 and SHA1 are set.
      history = data_store.REL_DB.ReadPathInfoHistory(
          cp.client_id, cp.path_type, cp.components
      )
      self.assertEqual(
          history[-1].hash_entry.sha256, fd_rel_db.hash_id.AsBytes()
      )
      self.assertEqual(history[-1].hash_entry.num_bytes, 5)
      self.assertIsNotNone(history[-1].hash_entry.sha1)
      self.assertIsNotNone(history[-1].hash_entry.md5)

  def testMultiGetFileDeduplication(self):
    client_mock = action_mocks.MultiGetFileClientMock()

    pathspecs = []
    # Make 10 files to download.
    for i in range(10):
      path = os.path.join(self.temp_dir, "test_%s.txt" % i)
      with io.open(path, "wb") as fd:
        fd.write(b"Hello")

      pathspecs.append(
          rdf_paths.PathSpec(pathtype=rdf_paths.PathSpec.PathType.OS, path=path)
      )

    # All those files are the same so the individual chunks should
    # only be downloaded once. By forcing maximum_pending_files=1,
    # there should only be a single TransferBuffer call.
    args = transfer.MultiGetFileArgs(
        pathspecs=pathspecs, maximum_pending_files=1
    )
    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )

    self.assertEqual(client_mock.action_counts["TransferBuffer"], 1)

    for pathspec in pathspecs:
      # Check that each referenced file can be read.
      cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
      fd_rel_db = file_store.OpenFile(cp)
      self.assertEqual(b"Hello", fd_rel_db.read())

      # Check that SHA256 hash of the file matches the contents
      # hash and that MD5 and SHA1 are set.
      history = data_store.REL_DB.ReadPathInfoHistory(
          cp.client_id, cp.path_type, cp.components
      )
      self.assertEqual(
          history[-1].hash_entry.sha256, fd_rel_db.hash_id.AsBytes()
      )
      self.assertEqual(history[-1].hash_entry.num_bytes, 5)
      self.assertIsNotNone(history[-1].hash_entry.sha1)
      self.assertIsNotNone(history[-1].hash_entry.md5)

  def testExistingChunks(self):
    client_mock = action_mocks.MultiGetFileClientMock()

    # Make a file to download that is three chunks long.
    # For the second run, we change the middle chunk. This will lead to a
    # different hash for the whole file and three chunks to download of which we
    # already have two.
    chunk_size = transfer.MultiGetFile.CHUNK_SIZE
    for data in [
        b"A" * chunk_size + b"B" * chunk_size + b"C" * 100,
        b"A" * chunk_size + b"X" * chunk_size + b"C" * 100,
    ]:
      path = os.path.join(self.temp_dir, "test.txt")
      with io.open(path, "wb") as fd:
        fd.write(data)

      pathspec = rdf_paths.PathSpec(
          pathtype=rdf_paths.PathSpec.PathType.OS, path=path
      )

      args = transfer.MultiGetFileArgs(pathspecs=[pathspec])
      flow_test_lib.StartAndRunFlow(
          transfer.MultiGetFile,
          client_mock,
          creator=self.test_username,
          client_id=self.client_id,
          flow_args=args,
      )

      cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
      fd_rel_db = file_store.OpenFile(cp)
      self.assertEqual(fd_rel_db.size, len(data))
      self.assertEqual(fd_rel_db.read(), data)

      # Check that SHA256 hash of the file matches the contents
      # hash and that MD5 and SHA1 are set.
      history = data_store.REL_DB.ReadPathInfoHistory(
          cp.client_id, cp.path_type, cp.components
      )
      self.assertEqual(
          history[-1].hash_entry.sha256, fd_rel_db.hash_id.AsBytes()
      )
      self.assertEqual(history[-1].hash_entry.num_bytes, len(data))
      self.assertIsNotNone(history[-1].hash_entry.sha1)
      self.assertIsNotNone(history[-1].hash_entry.md5)

    # Three chunks to get for the first file, only one for the second.
    self.assertEqual(client_mock.action_counts["TransferBuffer"], 4)

  def testMultiGetFileSetsFileHashAttributeWhenMultipleChunksDownloaded(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"),
    )
    expected_size = os.path.getsize(pathspec.path)

    args = transfer.MultiGetFileArgs(pathspecs=[pathspec])
    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )

    h = hashlib.sha256()
    with io.open(os.path.join(self.base_path, "test_img.dd"), "rb") as model_fd:
      h.update(model_fd.read())

    cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
    fd_rel_db = file_store.OpenFile(cp)
    self.assertEqual(fd_rel_db.hash_id.AsBytes(), h.digest())

    # Check that SHA256 hash of the file matches the contents
    # hash and that MD5 and SHA1 are set.
    history = data_store.REL_DB.ReadPathInfoHistory(
        cp.client_id, cp.path_type, cp.components
    )
    self.assertEqual(history[-1].hash_entry.sha256, fd_rel_db.hash_id.AsBytes())
    self.assertEqual(history[-1].hash_entry.num_bytes, expected_size)
    self.assertIsNotNone(history[-1].hash_entry.sha1)
    self.assertIsNotNone(history[-1].hash_entry.md5)

  def testMultiGetFileSizeLimit(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    image_path = os.path.join(self.base_path, "test_img.dd")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=image_path
    )

    # Read a bit more than one chunk (600 * 1024).
    expected_size = 750 * 1024
    args = transfer.MultiGetFileArgs(
        pathspecs=[pathspec], file_size=expected_size
    )
    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )

    with open(image_path, "rb") as fd:
      expected_data = fd.read(expected_size)

    cp = db.ClientPath.FromPathSpec(self.client_id, pathspec)
    fd_rel_db = file_store.OpenFile(cp)

    self.assertEqual(fd_rel_db.size, expected_size)

    data = fd_rel_db.read(2 * expected_size)
    self.assertLen(data, expected_size)

    d = hashlib.sha256()
    d.update(expected_data)
    self.assertEqual(fd_rel_db.hash_id.AsBytes(), d.digest())

    # Check that SHA256 hash of the file matches the contents
    # hash and that MD5 and SHA1 are set.
    history = data_store.REL_DB.ReadPathInfoHistory(
        cp.client_id, cp.path_type, cp.components
    )
    self.assertEqual(history[-1].hash_entry.sha256, fd_rel_db.hash_id.AsBytes())
    self.assertEqual(history[-1].hash_entry.num_bytes, expected_size)
    self.assertIsNotNone(history[-1].hash_entry.sha1)
    self.assertIsNotNone(history[-1].hash_entry.md5)

  def testMultiGetFileProgressReportsFailuresAndSuccessesCorrectly(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    image_path = os.path.join(self.base_path, "test_img.dd")
    pathspec_1 = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=image_path
    )
    pathspec_2 = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path="/non/existing/path"
    )

    args = transfer.MultiGetFileArgs(
        pathspecs=[
            pathspec_1,
            pathspec_2,
        ]
    )
    flow_id = flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )

    f_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    f_instance = transfer.MultiGetFile(f_obj)
    p = f_instance.GetProgress()

    self.assertEqual(p.num_pending_hashes, 0)
    self.assertEqual(p.num_pending_files, 0)
    self.assertEqual(p.num_skipped, 0)
    self.assertEqual(p.num_collected, 1)
    self.assertEqual(p.num_failed, 1)

    # Check that pathspecs in the progress proto are returned in the same order
    # as in the args proto.
    self.assertEqual(p.pathspecs_progress[0].pathspec, pathspec_1)
    self.assertEqual(p.pathspecs_progress[1].pathspec, pathspec_2)
    # Check that per-pathspecs statuses are correct.
    self.assertEqual(
        p.pathspecs_progress[0].status,
        transfer.PathSpecProgress.Status.COLLECTED,
    )
    self.assertEqual(
        p.pathspecs_progress[1].status, transfer.PathSpecProgress.Status.FAILED
    )

  def testMultiGetFileProgressReportsSkippedDuplicatesCorrectly(self):
    client_mock = action_mocks.MultiGetFileClientMock()
    image_path = os.path.join(self.base_path, "test_img.dd")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=image_path
    )

    args = transfer.MultiGetFileArgs(pathspecs=[pathspec])
    # Let the flow run to make sure the file is collected.
    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )

    # Run the flow second time to make sure duplicates are collected.
    flow_id = flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )

    f_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    f_instance = transfer.MultiGetFile(f_obj)

    p = f_instance.GetProgress()
    self.assertEqual(p.num_collected, 0)
    self.assertEqual(p.num_failed, 0)
    self.assertEqual(p.num_skipped, 1)

    self.assertLen(p.pathspecs_progress, 1)
    self.assertEqual(p.pathspecs_progress[0].pathspec, pathspec)
    self.assertEqual(
        p.pathspecs_progress[0].status, transfer.PathSpecProgress.Status.SKIPPED
    )

  @mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles")
  def testExternalFileStoreSubmissionIsTriggeredWhenFileIsSentToFileStore(
      self, add_file_mock
  ):

    client_mock = action_mocks.MultiGetFileClientMock()
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "test_img.dd"),
    )

    flow_test_lib.StartAndRunFlow(
        transfer.MultiGetFile,
        client_mock,
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=transfer.MultiGetFileArgs(pathspecs=[pathspec]),
    )

    add_file_mock.assert_called_once()
    args = add_file_mock.call_args_list[0][0]
    hash_id = list(args[0].keys())[0]
    self.assertIsInstance(hash_id, rdf_objects.SHA256HashID)
    self.assertEqual(
        args[0][hash_id].client_path,
        db.ClientPath.FromPathSpec(self.client_id, pathspec),
    )
    self.assertNotEmpty(args[0][hash_id].blob_refs)
    for blob_ref in args[0][hash_id].blob_refs:
      self.assertIsInstance(blob_ref, rdf_objects.BlobReference)

  def testStatCallsStatReceiveFileStatOnly(self):
    pathtype = rdf_paths.PathSpec.PathType.OS
    path = os.path.join(self.base_path, "test_img.dd")

    with mock.patch.object(
        transfer.MultiGetFile, "ReceiveFetchedFileStat"
    ) as dummy_fetched_stat:
      with mock.patch.object(
          transfer.MultiGetFile, "ReceiveFetchedFileHash"
      ) as dummy_fetched_hash:
        with mock.patch.object(
            transfer.MultiGetFile, "ReceiveFetchedFile"
        ) as dummy_fetched_file:
          with mock.patch.object(
              transfer.MultiGetFile, "FileFetchFailed"
          ) as mock_failure:
            flow_test_lib.StartAndRunFlow(
                transfer.MultiGetFile,
                action_mocks.MultiGetFileClientMock(),
                creator=self.test_username,
                client_id=self.client_id,
                flow_args=transfer.MultiGetFileArgs(
                    pathspecs=[
                        rdf_paths.PathSpec(pathtype=pathtype, path=path)
                    ],
                    stop_at=transfer.MultiGetFileArgs.StopAt.STAT,
                ),
            )

            self.assertTrue(dummy_fetched_stat.called)
            self.assertEqual(
                dummy_fetched_stat.call_args[0][0].pathspec.path, path
            )
            self.assertEqual(
                dummy_fetched_stat.call_args[0][0].pathspec.pathtype, pathtype
            )
            self.assertFalse(dummy_fetched_hash.called)
            self.assertFalse(dummy_fetched_file.called)
            self.assertFalse(mock_failure.called)

  def testStatCallsFileFetchFailed(self):
    pathtype = rdf_paths.PathSpec.PathType.OS
    path = os.path.join(self.base_path, "invalid.dd")

    with mock.patch.object(
        transfer.MultiGetFile, "ReceiveFetchedFileStat"
    ) as dummy_fetched_stat:
      with mock.patch.object(
          transfer.MultiGetFile, "ReceiveFetchedFileHash"
      ) as dummy_fetched_hash:
        with mock.patch.object(
            transfer.MultiGetFile, "ReceiveFetchedFile"
        ) as dummy_fetched_file:
          with mock.patch.object(
              transfer.MultiGetFile, "FileFetchFailed"
          ) as mock_failure:
            flow_test_lib.StartAndRunFlow(
                transfer.MultiGetFile,
                action_mocks.MultiGetFileClientMock(),
                creator=self.test_username,
                client_id=self.client_id,
                flow_args=transfer.MultiGetFileArgs(
                    pathspecs=[
                        rdf_paths.PathSpec(pathtype=pathtype, path=path)
                    ],
                    stop_at=transfer.MultiGetFileArgs.StopAt.STAT,
                ),
            )

            self.assertFalse(dummy_fetched_stat.called)
            self.assertFalse(dummy_fetched_hash.called)
            self.assertFalse(dummy_fetched_file.called)
            self.assertTrue(mock_failure.called)

  def testHashCallsReceiveFileHash(self):
    pathtype = rdf_paths.PathSpec.PathType.OS
    path = os.path.join(self.base_path, "test_img.dd")

    with mock.patch.object(
        transfer.MultiGetFile, "ReceiveFetchedFileStat"
    ) as dummy_fetched_stat:
      with mock.patch.object(
          transfer.MultiGetFile, "ReceiveFetchedFileHash"
      ) as dummy_fetched_hash:
        with mock.patch.object(
            transfer.MultiGetFile, "ReceiveFetchedFile"
        ) as dummy_fetched_file:
          with mock.patch.object(
              transfer.MultiGetFile, "FileFetchFailed"
          ) as mock_failure:
            flow_test_lib.StartAndRunFlow(
                transfer.MultiGetFile,
                action_mocks.MultiGetFileClientMock(),
                creator=self.test_username,
                client_id=self.client_id,
                flow_args=transfer.MultiGetFileArgs(
                    pathspecs=[
                        rdf_paths.PathSpec(pathtype=pathtype, path=path)
                    ],
                    stop_at=transfer.MultiGetFileArgs.StopAt.HASH,
                ),
            )

            self.assertTrue(dummy_fetched_stat.called)
            self.assertTrue(dummy_fetched_hash.called)
            self.assertEqual(
                dummy_fetched_hash.call_args[0][0].pathspec.path, path
            )
            self.assertEqual(
                dummy_fetched_hash.call_args[0][0].pathspec.pathtype, pathtype
            )
            self.assertFalse(dummy_fetched_file.called)
            self.assertFalse(mock_failure.called)

  def testHashCallsFileFetchFailed(self):
    pathtype = rdf_paths.PathSpec.PathType.OS
    path = os.path.join(self.base_path, "invalid.dd")

    with mock.patch.object(
        transfer.MultiGetFile, "ReceiveFetchedFileStat"
    ) as dummy_fetched_stat:
      with mock.patch.object(
          transfer.MultiGetFile, "ReceiveFetchedFileHash"
      ) as dummy_fetched_hash:
        with mock.patch.object(
            transfer.MultiGetFile, "ReceiveFetchedFile"
        ) as dummy_fetched_file:
          with mock.patch.object(
              transfer.MultiGetFile, "FileFetchFailed"
          ) as mock_failure:
            flow_test_lib.StartAndRunFlow(
                transfer.MultiGetFile,
                action_mocks.MultiGetFileClientMock(),
                creator=self.test_username,
                client_id=self.client_id,
                flow_args=transfer.MultiGetFileArgs(
                    pathspecs=[
                        rdf_paths.PathSpec(pathtype=pathtype, path=path)
                    ],
                    stop_at=transfer.MultiGetFileArgs.StopAt.HASH,
                ),
            )

            self.assertFalse(dummy_fetched_stat.called)
            self.assertFalse(dummy_fetched_hash.called)
            self.assertFalse(dummy_fetched_file.called)
            self.assertTrue(mock_failure.called)

  def testFileCallsReceiveFetchedFile(self):
    pathtype = rdf_paths.PathSpec.PathType.OS
    path = os.path.join(self.base_path, "test_img.dd")

    with mock.patch.object(
        transfer.MultiGetFile, "ReceiveFetchedFileStat"
    ) as dummy_fetched_stat:
      with mock.patch.object(
          transfer.MultiGetFile, "ReceiveFetchedFileHash"
      ) as dummy_fetched_hash:
        with mock.patch.object(
            transfer.MultiGetFile, "ReceiveFetchedFile"
        ) as dummy_fetched_file:
          with mock.patch.object(
              transfer.MultiGetFile, "FileFetchFailed"
          ) as mock_failure:
            flow_test_lib.StartAndRunFlow(
                transfer.MultiGetFile,
                action_mocks.MultiGetFileClientMock(),
                creator=self.test_username,
                client_id=self.client_id,
                flow_args=transfer.MultiGetFileArgs(
                    pathspecs=[
                        rdf_paths.PathSpec(pathtype=pathtype, path=path)
                    ],
                    stop_at=transfer.MultiGetFileArgs.StopAt.NOTHING,
                ),
            )

            self.assertTrue(dummy_fetched_stat.called)
            self.assertTrue(dummy_fetched_hash.called)
            self.assertTrue(dummy_fetched_file.called)
            self.assertEqual(
                dummy_fetched_file.call_args[0][0].pathspec.path, path
            )
            self.assertEqual(
                dummy_fetched_file.call_args[0][0].pathspec.pathtype, pathtype
            )
            self.assertFalse(mock_failure.called)

  def testFileCallsFileFetchFailed(self):
    pathtype = rdf_paths.PathSpec.PathType.OS
    path = os.path.join(self.base_path, "invalid.dd")

    with mock.patch.object(
        transfer.MultiGetFile, "ReceiveFetchedFileStat"
    ) as dummy_fetched_stat:
      with mock.patch.object(
          transfer.MultiGetFile, "ReceiveFetchedFileHash"
      ) as dummy_fetched_hash:
        with mock.patch.object(
            transfer.MultiGetFile, "ReceiveFetchedFile"
        ) as dummy_fetched_file:
          with mock.patch.object(
              transfer.MultiGetFile, "FileFetchFailed"
          ) as mock_failure:
            flow_test_lib.StartAndRunFlow(
                transfer.MultiGetFile,
                action_mocks.MultiGetFileClientMock(),
                creator=self.test_username,
                client_id=self.client_id,
                flow_args=transfer.MultiGetFileArgs(
                    pathspecs=[
                        rdf_paths.PathSpec(pathtype=pathtype, path=path)
                    ],
                    stop_at=transfer.MultiGetFileArgs.StopAt.NOTHING,
                ),
            )

            self.assertFalse(dummy_fetched_stat.called)
            self.assertFalse(dummy_fetched_hash.called)
            self.assertFalse(dummy_fetched_file.called)
            self.assertTrue(mock_failure.called)

  @db_test_lib.WithDatabase
  def testRRG_StopAtStat(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.MultiGetFileArgs()
    args.stop_at = flows_pb2.MultiGetFileArgs.StopAt.STAT

    pathspec = args.pathspecs.add()
    pathspec.pathtype = jobs_pb2.PathSpec.TMPFILE
    pathspec.path = "/tmp/foo/bar"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/tmp/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert

    path_info = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.TEMP,
        components=("tmp", "foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEmpty(path_info.hash_entry.sha256)

  @db_test_lib.WithDatabase
  def testRRG_StopAtHash(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.MultiGetFileArgs()
    args.stop_at = flows_pb2.MultiGetFileArgs.StopAt.HASH

    pathspec = args.pathspecs.add()
    pathspec.pathtype = jobs_pb2.PathSpec.TMPFILE
    pathspec.path = "/tmp/foo/bar"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/tmp/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert

    path_info = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.TEMP,
        components=("tmp", "foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

  @db_test_lib.WithDatabase
  def testRRG_StopAtNothing(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.MultiGetFileArgs()
    args.stop_at = flows_pb2.MultiGetFileArgs.StopAt.NOTHING

    pathspec = args.pathspecs.add()
    pathspec.pathtype = jobs_pb2.PathSpec.TMPFILE
    pathspec.path = "/tmp/foo/bar"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/tmp/foo/bar": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert

    path_info = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.TEMP,
        components=("tmp", "foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, len(b"Lorem ipsum."))  # pylint: disable=g-generic-assert
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.Temp(
            client_id=client_id,
            components=("tmp", "foo", "bar"),
        )
    )
    self.assertEqual(file.read(), b"Lorem ipsum.")

  @db_test_lib.WithDatabase
  def testRRG_StopAtNothing_Large(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )
    content = os.urandom(13371337)

    args = flows_pb2.MultiGetFileArgs()
    args.stop_at = flows_pb2.MultiGetFileArgs.StopAt.NOTHING

    pathspec = args.pathspecs.add()
    pathspec.pathtype = jobs_pb2.PathSpec.OS
    pathspec.path = "/foo/bar"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": content,
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.st_mode))
    self.assertEqual(result.st_size, 13371337)

    path_info = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))
    self.assertEqual(path_info.stat_entry.st_size, 13371337)
    self.assertEqual(
        path_info.hash_entry.sha256,
        hashlib.sha256(content).digest(),
    )

    file = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("foo", "bar"),
        )
    )
    # We need to explicitly pass length to `read` as otherwise it fails with
    # oversized read error. Oversized reads are not enforced if the length is
    # specifiad manually.
    self.assertEqual(file.read(13371337), content)

  @db_test_lib.WithDatabase
  def testRRG_StopAtNothing_Multiple(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.MultiGetFileArgs()
    args.stop_at = flows_pb2.MultiGetFileArgs.StopAt.NOTHING

    pathspec_foo = args.pathspecs.add()
    pathspec_foo.pathtype = jobs_pb2.PathSpec.OS
    pathspec_foo.path = "/quux/foo"

    pathspec_bar = args.pathspecs.add()
    pathspec_bar.pathtype = jobs_pb2.PathSpec.OS
    pathspec_bar.path = "/quux/bar"

    pathspec_baz = args.pathspecs.add()
    pathspec_baz.pathtype = jobs_pb2.PathSpec.OS
    pathspec_baz.path = "/quux/baz"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/quux/foo": b"Lorem ipsum.",
            "/quux/bar": b"Dolor sit amet.",
            "/quux/baz": b"Consectetur adipiscing elit.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 3)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    self.assertTrue(stat.S_ISREG(results_by_path["/quux/foo"].st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        results_by_path["/quux/foo"].st_size,
        len(b"Lorem ipsum."),
    )

    self.assertTrue(stat.S_ISREG(results_by_path["/quux/bar"].st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        results_by_path["/quux/bar"].st_size,
        len(b"Dolor sit amet."),
    )

    self.assertTrue(stat.S_ISREG(results_by_path["/quux/baz"].st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        results_by_path["/quux/baz"].st_size,
        len(b"Consectetur adipiscing elit."),
    )

    path_info_foo = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("quux", "foo"),
    )
    self.assertTrue(stat.S_ISREG(path_info_foo.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_foo.stat_entry.st_size,
        len(b"Lorem ipsum."),
    )
    self.assertEqual(
        path_info_foo.hash_entry.sha256,
        hashlib.sha256(b"Lorem ipsum.").digest(),
    )

    path_info_bar = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("quux", "bar"),
    )
    self.assertTrue(stat.S_ISREG(path_info_bar.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_bar.stat_entry.st_size,
        len(b"Dolor sit amet."),
    )
    self.assertEqual(
        path_info_bar.hash_entry.sha256,
        hashlib.sha256(b"Dolor sit amet.").digest(),
    )

    path_info_baz = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("quux", "baz"),
    )
    self.assertTrue(stat.S_ISREG(path_info_baz.stat_entry.st_mode))
    self.assertEqual(  # pylint: disable=g-generic-assert
        path_info_baz.stat_entry.st_size,
        len(b"Consectetur adipiscing elit."),
    )
    self.assertEqual(
        path_info_baz.hash_entry.sha256,
        hashlib.sha256(b"Consectetur adipiscing elit.").digest(),
    )

    file_foo = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "foo"),
        )
    )
    self.assertEqual(file_foo.read(), b"Lorem ipsum.")

    file_bar = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "bar"),
        )
    )
    self.assertEqual(file_bar.read(), b"Dolor sit amet.")

    file_baz = file_store.OpenFile(
        db.ClientPath.OS(
            client_id=client_id,
            components=("quux", "baz"),
        )
    )
    self.assertEqual(file_baz.read(), b"Consectetur adipiscing elit.")

  @db_test_lib.WithDatabase
  def testRRG_WindowsLeadingSlash(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = flows_pb2.MultiGetFileArgs()
    args.stop_at = flows_pb2.MultiGetFileArgs.StopAt.STAT

    pathspec = args.pathspecs.add()
    pathspec.pathtype = jobs_pb2.PathSpec.OS
    pathspec.path = "/C:/Windows/System32/notepad.exe"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(args),
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            r"C:\Windows\System32\notepad.exe": b"",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 1)

    result = jobs_pb2.StatEntry()
    self.assertTrue(flow_results[0].payload.Unpack(result))

    self.assertTrue(stat.S_ISREG(result.st_mode))

    path_info = rel_db.ReadPathInfo(
        client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("C:", "Windows", "System32", "notepad.exe"),
    )
    self.assertTrue(stat.S_ISREG(path_info.stat_entry.st_mode))

  @db_test_lib.WithDatabase
  def testRRG_StopAtNothing_Dir(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.MultiGetFileArgs()
    args.stop_at = flows_pb2.MultiGetFileArgs.StopAt.NOTHING

    pathspec = args.pathspecs.add()
    pathspec.pathtype = jobs_pb2.PathSpec.OS
    pathspec.path = "/tmp"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=mig_transfer.ToRDFMultiGetFileArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/tmp": {},
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_logs = rel_db.ReadFlowLogEntries(
        client_id=client_id,
        flow_id=flow_id,
        offset=0,
        count=1024,
    )
    flow_log_messages = [flow_log.message for flow_log in flow_logs]

    self.assertIn("Unexpected file type for '/tmp': DIR", flow_log_messages)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
