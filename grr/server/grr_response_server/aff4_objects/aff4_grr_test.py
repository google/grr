#!/usr/bin/env python
"""Test the grr aff4 objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import time

from builtins import range  # pylint: disable=redefined-builtin
import mock

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import aff4_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class MockChangeEvent(events.EventListener):
  EVENTS = ["MockChangeEvent"]

  CHANGED_URNS = []

  def ProcessMessages(self, msgs=None, token=None):
    MockChangeEvent.CHANGED_URNS.extend(msgs)


class AFF4GRRTest(aff4_test_lib.AFF4ObjectTest):
  """Test the client aff4 implementation."""

  def setUp(self):
    super(AFF4GRRTest, self).setUp()
    MockChangeEvent.CHANGED_URNS = []

  def testAFF4Path(self):
    """Test the pathspec to URN conversion function."""
    pathspec = rdf_paths.PathSpec(
        path="\\\\.\\Volume{1234}\\",
        pathtype=rdf_paths.PathSpec.PathType.OS,
        mount_point="/c:/").Append(
            path="/windows", pathtype=rdf_paths.PathSpec.PathType.TSK)

    urn = pathspec.AFF4Path(rdf_client.ClientURN("C.1234567812345678"))
    self.assertEqual(
        urn,
        rdfvalue.RDFURN(
            r"aff4:/C.1234567812345678/fs/tsk/\\.\Volume{1234}\/windows"))

    # Test an ADS
    pathspec = rdf_paths.PathSpec(
        path="\\\\.\\Volume{1234}\\",
        pathtype=rdf_paths.PathSpec.PathType.OS,
        mount_point="/c:/").Append(
            pathtype=rdf_paths.PathSpec.PathType.TSK,
            path="/Test Directory/notes.txt:ads",
            inode=66,
            ntfs_type=128,
            ntfs_id=2)

    urn = pathspec.AFF4Path(rdf_client.ClientURN("C.1234567812345678"))
    self.assertEqual(
        urn,
        rdfvalue.RDFURN(r"aff4:/C.1234567812345678/fs/tsk/\\.\Volume{1234}\/"
                        "Test Directory/notes.txt:ads"))

  def testClientSubfieldGet(self):
    """Test we can get subfields of the client."""
    fd = aff4.FACTORY.Create(
        "C.0000000000000000", aff4_grr.VFSGRRClient, token=self.token)

    kb = fd.Schema.KNOWLEDGE_BASE()
    for i in range(5):
      kb.users.Append(rdf_client.User(username="user%s" % i))
    fd.Set(kb)
    fd.Close()

    fd = aff4.FACTORY.Open(
        "C.0000000000000000", aff4_grr.VFSGRRClient, token=self.token)
    for i, user in enumerate(fd.Get(fd.Schema.KNOWLEDGE_BASE).users):
      self.assertEqual(user.username, "user%s" % i)

  def testVFSFileContentLastNotUpdated(self):
    """Make sure CONTENT_LAST does not update when only STAT is written.."""
    path = "/C.12345/contentlastchecker"

    timestamp = 1
    with utils.Stubber(time, "time", lambda: timestamp):
      fd = aff4.FACTORY.Create(
          path, aff4_grr.VFSFile, mode="w", token=self.token)

      timestamp += 1
      fd.SetChunksize(10)

      # Make lots of small writes - The length of this string and the chunk size
      # are relative primes for worst case.
      for i in range(100):
        fd.Write(b"%s%08X\n" % (b"Test", i))

        # Flush after every write.
        fd.Flush()

        # And advance the time.
        timestamp += 1

      fd.Set(fd.Schema.STAT, rdf_client_fs.StatEntry())

      fd.Close()

    fd = aff4.FACTORY.Open(path, mode="rw", token=self.token)
    # Make sure the attribute was written when the write occured.
    self.assertEqual(int(fd.GetContentAge()), 101000000)

    # Write the stat (to be the same as before, but this still counts
    # as a write).
    fd.Set(fd.Schema.STAT, fd.Get(fd.Schema.STAT))
    fd.Flush()

    fd = aff4.FACTORY.Open(path, token=self.token)

    # The age of the content should still be the same.
    self.assertEqual(int(fd.GetContentAge()), 101000000)

  def testVFSFileStartsOnlyOneMultiGetFileFlowOnUpdate(self):
    """File updates should only start one MultiGetFile at any point in time."""
    client_id = self.SetupClient(0)
    # We need to create a file path having a pathspec.
    path = "fs/os/c/bin/bash"

    with aff4.FACTORY.Create(
        client_id.Add(path),
        aff4_type=aff4_grr.VFSFile,
        mode="rw",
        token=self.token) as file_fd:
      file_fd.Set(
          file_fd.Schema.STAT,
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(path="/bin/bash", pathtype="OS")))

      # Starts a MultiGetFile flow.
      file_fd.Update()

    # Check that there is exactly one flow on the client.
    flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
    flows = list(flows_fd.ListChildren())
    self.assertLen(flows, 1)

    # The flow is the MultiGetFile flow holding the lock on the file.
    flow_obj = aff4.FACTORY.Open(flows[0], token=self.token)
    self.assertEqual(
        flow_obj.Get(flow_obj.Schema.TYPE), transfer.MultiGetFile.__name__)
    self.assertEqual(flow_obj.urn, file_fd.Get(file_fd.Schema.CONTENT_LOCK))

    # Since there is already a running flow having the lock on the file,
    # this call shouldn't do anything.
    file_fd.Update()

    # There should still be only one flow on the client.
    flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
    flows = list(flows_fd.ListChildren())
    self.assertLen(flows, 1)

  def testVFSFileStartsNewMultiGetFileWhenLockingFlowHasFinished(self):
    """A new MultiFileGet can be started when the locking flow has finished."""
    client_id = self.SetupClient(0)
    path = "fs/os/c/bin/bash"

    with aff4.FACTORY.Create(
        client_id.Add(path),
        aff4_type=aff4_grr.VFSFile,
        mode="rw",
        token=self.token) as file_fd:
      file_fd.Set(
          file_fd.Schema.STAT,
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(path="/bin/bash", pathtype="OS")))
      # Starts a MultiGetFile flow.
      first_update_flow_urn = file_fd.Update()

    # Check that there is exactly one flow on the client.
    flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
    flows = list(flows_fd.ListChildren())
    self.assertLen(flows, 1)

    # Finish the flow holding the lock.
    client_mock = action_mocks.ActionMock()
    flow_test_lib.TestFlowHelper(
        flows[0], client_mock, client_id=client_id, token=self.token)

    # The flow holding the lock has finished, so Update() should start a new
    # flow.
    second_update_flow_urn = file_fd.Update()

    # There should be two flows now.
    flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
    flows = list(flows_fd.ListChildren())
    self.assertLen(flows, 2)

    # Make sure that each Update() started a new flow and that the second flow
    # is holding the lock.
    self.assertNotEqual(first_update_flow_urn, second_update_flow_urn)
    self.assertEqual(second_update_flow_urn,
                     file_fd.Get(file_fd.Schema.CONTENT_LOCK))

  def testGetClientSummary(self):
    hostname = "test"
    system = "Linux"
    os_release = "12.02"
    kernel = "3.15-rc2"
    fqdn = "test.test.com"
    arch = "amd64"
    install_time = rdfvalue.RDFDatetime.Now()
    user = "testuser"
    userobj = rdf_client.User(username=user)
    interface = rdf_client_network.Interface(ifname="eth0")
    google_cloud_instance = rdf_cloud.GoogleCloudInstance(
        instance_id="1771384456894610289",
        zone="projects/123456789733/zones/us-central1-a",
        project_id="myproject",
        unique_id="us-central1-a/myproject/1771384456894610289")
    cloud_instance = rdf_cloud.CloudInstance(
        cloud_type="GOOGLE", google=google_cloud_instance)

    serial_number = "DSD33679FZ"
    system_manufacturer = "Foobar Inc."
    system_uuid = "C31292AD-6Z4F-55D8-28AC-EC1100E42222"
    hwinfo = rdf_client.HardwareInfo(
        serial_number=serial_number,
        system_manufacturer=system_manufacturer,
        system_uuid=system_uuid)

    timestamp = 1
    with utils.Stubber(time, "time", lambda: timestamp):
      with aff4.FACTORY.Create(
          "C.0000000000000000",
          aff4_grr.VFSGRRClient,
          mode="rw",
          token=self.token) as fd:
        kb = rdf_client.KnowledgeBase()
        kb.users.Append(userobj)
        empty_summary = fd.GetSummary()
        self.assertEqual(empty_summary.client_id, "C.0000000000000000")
        self.assertFalse(empty_summary.system_info.version)
        self.assertEqual(empty_summary.timestamp.AsSecondsSinceEpoch(), 1)

        # This will cause TYPE to be written with current time = 101 when the
        # object is closed
        timestamp += 100
        fd.Set(fd.Schema.HOSTNAME(hostname))
        fd.Set(fd.Schema.SYSTEM(system))
        fd.Set(fd.Schema.OS_RELEASE(os_release))
        fd.Set(fd.Schema.KERNEL(kernel))
        fd.Set(fd.Schema.FQDN(fqdn))
        fd.Set(fd.Schema.ARCH(arch))
        fd.Set(fd.Schema.INSTALL_DATE(install_time))
        fd.Set(fd.Schema.KNOWLEDGE_BASE(kb))
        fd.Set(fd.Schema.USERNAMES(user))
        fd.Set(fd.Schema.HARDWARE_INFO(hwinfo))
        fd.Set(fd.Schema.INTERFACES([interface]))
        fd.Set(fd.Schema.CLOUD_INSTANCE(cloud_instance))

      with aff4.FACTORY.Open(
          "C.0000000000000000",
          aff4_grr.VFSGRRClient,
          mode="rw",
          token=self.token) as fd:
        summary = fd.GetSummary()
        self.assertEqual(summary.system_info.system, system)
        self.assertEqual(summary.system_info.release, os_release)
        self.assertEqual(summary.system_info.kernel, kernel)
        self.assertEqual(summary.system_info.fqdn, fqdn)
        self.assertEqual(summary.system_info.machine, arch)
        self.assertEqual(summary.system_info.install_date, install_time)
        self.assertCountEqual(summary.users, [userobj])
        self.assertCountEqual(summary.interfaces, [interface])
        self.assertFalse(summary.client_info)

        self.assertEqual(summary.timestamp.AsSecondsSinceEpoch(), 101)
        self.assertEqual(summary.cloud_type, "GOOGLE")
        self.assertEqual(summary.cloud_instance_id,
                         "us-central1-a/myproject/1771384456894610289")

        self.assertEqual(summary.serial_number, serial_number)
        self.assertEqual(summary.system_manufacturer, system_manufacturer)
        self.assertEqual(summary.system_uuid, system_uuid)


def WriteBlobWithUnknownHashStub(blob):
  return rdf_objects.BlobID.FromBlobData(blob)


class BlobImageTest(aff4_test_lib.AFF4ObjectTest):
  """Tests for cron functionality."""

  def testAppendContentError(self):
    src_content = b"ABCD" * 10
    src_fd = io.BytesIO(src_content)

    dest_fd = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("temp"),
        aff4_grr.VFSBlobImage,
        token=self.token,
        mode="rw")
    dest_fd.SetChunksize(7)
    dest_fd.AppendContent(src_fd)
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content)

    src_fd.seek(0)
    self.assertRaises(IOError, dest_fd.AppendContent, src_fd)

  def testAppendContent(self):
    """Test writing content where content length % chunksize == 0."""
    src_content = b"ABCDEFG" * 10  # 10 chunksize blobs
    src_fd = io.BytesIO(src_content)

    dest_fd = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("temp"),
        aff4_grr.VFSBlobImage,
        token=self.token,
        mode="rw")
    self.assertEqual(dest_fd.Get(dest_fd.Schema.HASHES), None)

    dest_fd.SetChunksize(7)
    dest_fd.AppendContent(src_fd)

    self.assertEqual(int(dest_fd.Get(dest_fd.Schema.SIZE)), len(src_content))
    self.assertTrue(dest_fd.Get(dest_fd.Schema.HASHES))

    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content)

    src_fd.seek(0)
    dest_fd.AppendContent(src_fd)
    self.assertEqual(dest_fd.size, 2 * len(src_content))
    self.assertEqual(
        int(dest_fd.Get(dest_fd.Schema.SIZE)), 2 * len(src_content))
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content + src_content)

  def testMultiStreamStreamsSingleFileWithSingleChunk(self):
    with aff4.FACTORY.Create(
        "aff4:/foo", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(io.BytesIO(b"123456789"))

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    chunks_fds = list(aff4.AFF4Stream.MultiStream([fd]))

    self.assertLen(chunks_fds, 1)
    self.assertEqual(chunks_fds[0][1], b"123456789")
    self.assertIs(chunks_fds[0][0], fd)

  def testMultiStreamStreamsSinglfeFileWithTwoChunks(self):
    with aff4.FACTORY.Create(
        "aff4:/foo", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(io.BytesIO(b"123456789"))

    with aff4.FACTORY.Create(
        "aff4:/bar", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(io.BytesIO(b"abcd"))

    fd1 = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    fd2 = aff4.FACTORY.Open("aff4:/bar", token=self.token)
    chunks_fds = list(aff4.AFF4Stream.MultiStream([fd1, fd2]))

    self.assertLen(chunks_fds, 2)

    self.assertEqual(chunks_fds[0][1], b"123456789")
    self.assertIs(chunks_fds[0][0], fd1)

    self.assertEqual(chunks_fds[1][1], b"abcd")
    self.assertIs(chunks_fds[1][0], fd2)

  def testMultiStreamStreamsTwoFilesWithTwoChunksInEach(self):
    with aff4.FACTORY.Create(
        "aff4:/foo", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(io.BytesIO(b"*" * 10 + b"123456789"))

    with aff4.FACTORY.Create(
        "aff4:/bar", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(io.BytesIO(b"*" * 10 + b"abcd"))

    fd1 = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    fd2 = aff4.FACTORY.Open("aff4:/bar", token=self.token)
    chunks_fds = list(aff4.AFF4Stream.MultiStream([fd1, fd2]))

    self.assertLen(chunks_fds, 4)

    self.assertEqual(chunks_fds[0][1], b"*" * 10)
    self.assertIs(chunks_fds[0][0], fd1)

    self.assertEqual(chunks_fds[1][1], b"123456789")
    self.assertIs(chunks_fds[1][0], fd1)

    self.assertEqual(chunks_fds[2][1], b"*" * 10)
    self.assertIs(chunks_fds[2][0], fd2)

    self.assertEqual(chunks_fds[3][1], b"abcd")
    self.assertIs(chunks_fds[3][0], fd2)

  def testMultiStreamReturnsExceptionIfChunkIsMissing(self):
    with aff4.FACTORY.Create(
        "aff4:/foo", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      # Patching WriteBlobWithUnknownHash prevents the blobs from actually being
      # written.
      with mock.patch.object(
          data_store.BLOBS,
          "WriteBlobWithUnknownHash",
          side_effect=WriteBlobWithUnknownHashStub):
        fd.AppendContent(io.BytesIO(b"123456789"))

      fd.index.seek(0)
      blob_id = rdf_objects.BlobID.FromBytes(fd.index.read(fd._HASH_SIZE))

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    returned_fd, _, e = list(aff4.AFF4Stream.MultiStream([fd]))[0]
    self.assertNotEqual(e, None)
    self.assertEqual(returned_fd, fd)
    self.assertEqual(e.missing_chunks, [blob_id])

  def testMultiStreamIgnoresTheFileIfAnyChunkIsMissingInReadAheadChunks(self):
    with aff4.FACTORY.Create(
        "aff4:/foo", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(io.BytesIO(b"*" * 10))

      # Patching WriteBlobWithUnknownHash prevents the blobs from actually being
      # written.
      with mock.patch.object(
          data_store.BLOBS,
          "WriteBlobWithUnknownHash",
          side_effect=WriteBlobWithUnknownHashStub):
        fd.AppendContent(io.BytesIO(b"123456789"))

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    count = 0
    for _, _, e in aff4.AFF4Stream.MultiStream([fd]):
      if not e:
        count += 1

    self.assertEqual(count, 0)

  @mock.patch.object(aff4_grr.VFSBlobImage, "MULTI_STREAM_CHUNKS_READ_AHEAD", 1)
  def testMultiStreamTruncatesBigFileIfLastChunkIsMissing(self):
    # If the file is split between 2 batches of chunks, and the missing
    # chunk is in the second batch, the first batch will be succesfully
    # yielded.
    with aff4.FACTORY.Create(
        "aff4:/foo", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(io.BytesIO(b"*" * 10))

      # Patching WriteBlobWithUnknownHash prevents the blobs from actually being
      # written.
      with mock.patch.object(
          data_store.BLOBS,
          "WriteBlobWithUnknownHash",
          side_effect=WriteBlobWithUnknownHashStub):
        fd.AppendContent(io.BytesIO(b"123456789"))

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    content = []
    error_detected = False
    for fd, chunk, e in aff4.AFF4Stream.MultiStream([fd]):
      if not e:
        content.append(chunk)
      else:
        error_detected = True

    self.assertEqual(content, [b"*" * 10])
    self.assertTrue(error_detected)

  @mock.patch.object(aff4_grr.VFSBlobImage, "MULTI_STREAM_CHUNKS_READ_AHEAD", 1)
  def testMultiStreamSkipsBigFileIfFirstChunkIsMissing(self):
    # If the file is split between 2 batches of chunks, and the missing
    # chunk is in the first batch, the file will be skipped entirely.
    with aff4.FACTORY.Create(
        "aff4:/foo", aff4_type=aff4_grr.VFSBlobImage, token=self.token) as fd:
      fd.SetChunksize(10)

      # Patching WriteBlobWithUnknownHash prevents the blobs from actually being
      # written.
      with mock.patch.object(
          data_store.BLOBS,
          "WriteBlobWithUnknownHash",
          side_effect=WriteBlobWithUnknownHashStub):
        fd.AppendContent(io.BytesIO(b"*" * 10))

      fd.AppendContent(io.BytesIO(b"123456789"))

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    count = 0
    for _, _, e in aff4.AFF4Stream.MultiStream([fd]):
      if not e:
        count += 1

    self.assertEqual(count, 0)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
