#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for API client and VFS-related API calls."""

import io
import os
import threading
import time
from unittest import mock
import zipfile

from absl import app

from grr_api_client import errors
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_proto.api import vfs_pb2
from grr_response_server import artifact_registry
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class ApiClientLibVfsTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests VFS operations part of GRR Python API client library."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    fixture_test_lib.ClientFixture(self.client_id)

  def testGetFileFromRef(self):
    file_ref = self.api.Client(
        client_id=self.client_id).File("fs/os/c/Downloads/a.txt")
    self.assertEqual(file_ref.path, "fs/os/c/Downloads/a.txt")

    file_obj = file_ref.Get()
    self.assertEqual(file_obj.path, "fs/os/c/Downloads/a.txt")
    self.assertFalse(file_obj.is_directory)
    self.assertEqual(file_obj.data.name, "a.txt")

  def testGetFileForDirectory(self):
    file_obj = self.api.Client(
        client_id=self.client_id).File("fs/os/c/Downloads").Get()
    self.assertEqual(file_obj.path, "fs/os/c/Downloads")
    self.assertTrue(file_obj.is_directory)

  def testListFiles(self):
    files_iter = self.api.Client(
        client_id=self.client_id).File("fs/os/c/Downloads").ListFiles()
    files_list = list(files_iter)

    self.assertCountEqual(
        [f.data.name for f in files_list],
        ["a.txt", "b.txt", "c.txt", "d.txt", "sub1", "中国新闻网新闻中.txt"])

  def testGetBlob(self):
    out = io.BytesIO()
    self.api.Client(client_id=self.client_id).File(
        "fs/tsk/c/bin/rbash").GetBlob().WriteToStream(out)

    self.assertEqual(out.getvalue(), b"Hello world")

  def testGetBlobUnicode(self):
    vfs_test_lib.CreateFile(
        db.ClientPath.TSK("C.1000000000000000", ["c", "bin", "中国新闻网新闻中"]),
        b"Hello world")

    out = io.BytesIO()
    self.api.Client(client_id=self.client_id).File(
        "fs/tsk/c/bin/中国新闻网新闻中").GetBlob().WriteToStream(out)

    self.assertEqual(out.getvalue(), b"Hello world")

  def testGetBlobFailsWhenFileIsCorrupt(self):
    _, blob_refs = vfs_test_lib.GenerateBlobRefs(10, "0")
    # We write just the references, without actual data, simulating a case
    # when blobs were not written to the blob store for some reason.
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        db.ClientPath.OS("C.1000000000000000", ["c", "bin", "test"]), blob_refs,
        [])

    out = io.BytesIO()
    with self.assertRaises(errors.UnknownError):
      self.api.Client(client_id=self.client_id).File(
          "fs/os/c/bin/test").GetBlob().WriteToStream(out)

  def testGetBlobWithOffset(self):
    tsk = db.ClientPath.TSK("C.1000000000000000", ["c", "bin", "foobar"])
    vfs_test_lib.CreateFile(tsk, b"Hello world")

    out = io.BytesIO()
    client = self.api.Client(client_id=self.client_id)
    f = client.File("fs/tsk/c/bin/foobar")
    f.GetBlobWithOffset(6).WriteToStream(out)

    self.assertEqual(out.getvalue(), b"world")

  def testGetBlobWithOffsetUnicode(self):
    tsk = db.ClientPath.TSK("C.1000000000000000", ["c", "bin", "中"])
    vfs_test_lib.CreateFile(tsk, b"Hello world")

    out = io.BytesIO()
    client = self.api.Client(client_id=self.client_id)
    f = client.File("fs/tsk/c/bin/中")
    f.GetBlobWithOffset(6).WriteToStream(out)

    self.assertEqual(out.getvalue(), b"world")

  def testGetFilesArchive(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    zip_stream = io.BytesIO()
    self.api.Client(client_id=self.client_id).File(
        "fs/tsk/c/bin").GetFilesArchive().WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertCountEqual(namelist, [
        "vfs_C_1000000000000000_fs_tsk_c_bin/fs/tsk/c/bin/rbash",
        "vfs_C_1000000000000000_fs_tsk_c_bin/fs/tsk/c/bin/bash"
    ])

    for info in zip_fd.infolist():
      self.assertGreater(info.compress_size, 0)

    # Check that notification was pushed indicating the failure to the user.
    pending_notifications = list(self.api.GrrUser().ListPendingNotifications(
        timestamp=timestamp.AsMicrosecondsSinceEpoch()))
    self.assertLen(pending_notifications, 1)
    self.assertEqual(
        pending_notifications[0].data.notification_type,
        int(rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED))
    self.assertEqual(pending_notifications[0].data.reference.type,
                     pending_notifications[0].data.reference.VFS)
    self.assertEqual(pending_notifications[0].data.reference.vfs.client_id,
                     self.client_id)
    self.assertEqual(pending_notifications[0].data.reference.vfs.vfs_path,
                     "fs/tsk/c/bin")

  def testGetFilesArchiveFailsWhenFirstFileBlobIsMissing(self):
    _, blob_refs = vfs_test_lib.GenerateBlobRefs(10, "0")
    # We write just the references, without actual data, simulating a case
    # when blobs were not written to the blob store for some reason.
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        db.ClientPath.TSK("C.1000000000000000", ["c", "universe", "42"]),
        blob_refs, [])

    zip_stream = io.BytesIO()
    timestamp = rdfvalue.RDFDatetime.Now()
    with self.assertRaises(errors.UnknownError):
      self.api.Client(client_id=self.client_id).File(
          "fs/tsk/c/universe").GetFilesArchive().WriteToStream(zip_stream)

    # Check that notification was pushed indicating the failure to the user.
    pending_notifications = list(self.api.GrrUser().ListPendingNotifications(
        timestamp=timestamp.AsMicrosecondsSinceEpoch()))
    self.assertLen(pending_notifications, 1)
    self.assertEqual(
        pending_notifications[0].data.notification_type,
        int(rdf_objects.UserNotification.Type
            .TYPE_FILE_ARCHIVE_GENERATION_FAILED))
    self.assertEqual(pending_notifications[0].data.reference.type,
                     pending_notifications[0].data.reference.VFS)
    self.assertEqual(pending_notifications[0].data.reference.vfs.client_id,
                     self.client_id)
    self.assertEqual(pending_notifications[0].data.reference.vfs.vfs_path,
                     "fs/tsk/c/universe")

  def testGetFilesArchiveDropsStreamingResponsesWhenSecondFileBlobIsMissing(
      self):
    blob_data, blob_refs = vfs_test_lib.GenerateBlobRefs(1024 * 1024 * 10, "01")
    # We write just the references, without actual data, simulating a case
    # when blobs were not written to the blob store for some reason.
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        db.ClientPath.TSK("C.1000000000000000", ["c", "universe", "42"]),
        blob_refs, blob_data[:1])

    zip_stream = io.BytesIO()
    timestamp = rdfvalue.RDFDatetime.Now()
    self.api.Client(client_id=self.client_id).File(
        "fs/tsk/c/universe").GetFilesArchive().WriteToStream(zip_stream)

    with self.assertRaises(zipfile.BadZipfile):
      zipfile.ZipFile(zip_stream)

    # Check that notification was pushed indicating the failure to the user.
    pending_notifications = list(self.api.GrrUser().ListPendingNotifications(
        timestamp=timestamp.AsMicrosecondsSinceEpoch()))
    self.assertLen(pending_notifications, 1)
    self.assertEqual(
        pending_notifications[0].data.notification_type,
        int(rdf_objects.UserNotification.Type
            .TYPE_FILE_ARCHIVE_GENERATION_FAILED))
    self.assertEqual(pending_notifications[0].data.reference.type,
                     pending_notifications[0].data.reference.VFS)
    self.assertEqual(pending_notifications[0].data.reference.vfs.client_id,
                     self.client_id)
    self.assertEqual(pending_notifications[0].data.reference.vfs.vfs_path,
                     "fs/tsk/c/universe")

  def testGetVersionTimes(self):
    vtimes = self.api.Client(client_id=self.client_id).File(
        "fs/os/c/Downloads/a.txt").GetVersionTimes()
    self.assertLen(vtimes, 1)

  def testRefresh(self):
    operation = self.api.Client(
        client_id=self.client_id).File("fs/os/c/Downloads").Refresh()
    self.assertTrue(operation.operation_id)
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

  def testRefreshWaitUntilDone(self):
    f = self.api.Client(client_id=self.client_id).File("fs/os/c/Downloads")

    with flow_test_lib.TestWorker():
      operation = f.Refresh()
      self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

      def ProcessOperation():
        time.sleep(1)
        flow_test_lib.FinishAllFlowsOnClient(self.client_id)

      threading.Thread(target=ProcessOperation).start()
      result_f = operation.WaitUntilDone().target_file

    self.assertEqual(f.path, result_f.path)
    self.assertEqual(operation.GetState(), operation.STATE_FINISHED)

  def testRefreshRecursively(self):
    operation = self.api.Client(
        client_id=self.client_id).File("fs/os/c/Downloads").RefreshRecursively(
            max_depth=5)
    self.assertTrue(operation.operation_id)
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

  def testRefreshRecursivelyWaitUntilDone(self):
    f = self.api.Client(client_id=self.client_id).File("fs/os/c/Downloads")

    with flow_test_lib.TestWorker():
      operation = f.RefreshRecursively(max_depth=5)
      self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

      def ProcessOperation():
        time.sleep(1)
        flow_test_lib.FinishAllFlowsOnClient(self.client_id)

      threading.Thread(target=ProcessOperation).start()
      result_f = operation.WaitUntilDone().target_file

    self.assertEqual(f.path, result_f.path)
    self.assertEqual(operation.GetState(), operation.STATE_FINISHED)

  def testCollect(self):
    operation = self.api.Client(
        client_id=self.client_id).File("fs/os/c/Downloads/a.txt").Collect()
    self.assertTrue(operation.operation_id)
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

  def testCollectWaitUntilDone(self):
    f = self.api.Client(
        client_id=self.client_id).File("fs/os/c/Downloads/a.txt")

    with flow_test_lib.TestWorker():
      operation = f.Collect()
      self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

      def ProcessOperation():
        time.sleep(1)
        flow_test_lib.FinishAllFlowsOnClient(self.client_id)

      threading.Thread(target=ProcessOperation).start()
      result_f = operation.WaitUntilDone().target_file

    self.assertEqual(f.path, result_f.path)
    self.assertEqual(operation.GetState(), operation.STATE_FINISHED)

  def testFileFinderIndicatesCollectedSizeAfterCollection(self):
    client_ref = self.api.Client(client_id=self.client_id)
    # TODO(user): for symlink-related test scenarios, this should require
    # follow_links to be True. However, unlike the ClientFileFinder test
    # below, this one doesn't care about this setting. Fix the
    # FileFinder/ClientFileFinder behavior to match each other.
    args = rdf_file_finder.FileFinderArgs(
        paths=[os.path.join(self.base_path, "numbers.txt")],
        action=rdf_file_finder.FileFinderAction.Download()).AsPrimitiveProto()
    client_ref.CreateFlow(name=file_finder.FileFinder.__name__, args=args)

    flow_test_lib.FinishAllFlowsOnClient(
        self.client_id, client_mock=action_mocks.FileFinderClientMock())

    f = client_ref.File("fs/os" +
                        os.path.join(self.base_path, "numbers.txt")).Get()
    self.assertNotEqual(f.data.hash.sha256, b"")
    self.assertGreater(f.data.hash.num_bytes, 0)
    self.assertGreater(f.data.last_collected, 0)
    self.assertGreater(f.data.last_collected_size, 0)

  def testClientFileFinderIndicatesCollectedSizeAfterCollection(self):
    client_ref = self.api.Client(client_id=self.client_id)
    args = rdf_file_finder.FileFinderArgs(
        paths=[os.path.join(self.base_path, "numbers.txt")],
        action=rdf_file_finder.FileFinderAction.Download(),
        follow_links=True).AsPrimitiveProto()
    client_ref.CreateFlow(name=file_finder.ClientFileFinder.__name__, args=args)

    flow_test_lib.FinishAllFlowsOnClient(
        self.client_id, client_mock=action_mocks.ClientFileFinderClientMock())

    f = client_ref.File("fs/os" +
                        os.path.join(self.base_path, "numbers.txt")).Get()
    self.assertNotEqual(f.data.hash.sha256, b"")
    self.assertGreater(f.data.hash.num_bytes, 0)
    self.assertGreater(f.data.last_collected, 0)
    self.assertGreater(f.data.last_collected_size, 0)

  def testGetFileIndicatesCollectedSizeAfterCollection(self):
    # Find the file with FileFinder stat action, so that we can reference it
    # and trigger "Collect" operation on it.
    client_ref = self.api.Client(client_id=self.client_id)
    args = rdf_file_finder.FileFinderArgs(
        paths=[os.path.join(self.base_path, "numbers.txt")],
        action=rdf_file_finder.FileFinderAction.Stat()).AsPrimitiveProto()
    client_ref.CreateFlow(name=file_finder.FileFinder.__name__, args=args)

    client_mock = action_mocks.FileFinderClientMock()
    flow_test_lib.FinishAllFlowsOnClient(
        self.client_id, client_mock=client_mock)

    f = client_ref.File("fs/os" + os.path.join(self.base_path, "numbers.txt"))
    with flow_test_lib.TestWorker():
      operation = f.Collect()
      self.assertEqual(operation.GetState(), operation.STATE_RUNNING)
      flow_test_lib.FinishAllFlowsOnClient(
          self.client_id, client_mock=client_mock)
      self.assertEqual(operation.GetState(), operation.STATE_FINISHED)

    f = f.Get()
    self.assertNotEqual(f.data.hash.sha256, b"")
    self.assertGreater(f.data.hash.num_bytes, 0)
    self.assertGreater(f.data.last_collected, 0)
    self.assertGreater(f.data.last_collected_size, 0)

  def testArtifactCollectorIndicatesCollectedSizeAfterCollection(self):
    registry_stub = artifact_registry.ArtifactRegistry()
    source = rdf_artifacts.ArtifactSource(
        type=rdf_artifacts.ArtifactSource.SourceType.FILE,
        attributes={
            "paths": [os.path.join(self.base_path, "numbers.txt")],
        })
    artifact = rdf_artifacts.Artifact(
        name="FakeArtifact", sources=[source], doc="fake artifact doc")
    registry_stub.RegisterArtifact(artifact)

    client_ref = self.api.Client(client_id=self.client_id)
    with mock.patch.object(artifact_registry, "REGISTRY", registry_stub):
      args = rdf_artifacts.ArtifactCollectorFlowArgs(
          artifact_list=["FakeArtifact"]).AsPrimitiveProto()
      client_ref.CreateFlow(
          name=collectors.ArtifactCollectorFlow.__name__, args=args)

      client_mock = action_mocks.FileFinderClientMock()
      flow_test_lib.FinishAllFlowsOnClient(
          self.client_id, client_mock=client_mock)

    f = client_ref.File("fs/os" +
                        os.path.join(self.base_path, "numbers.txt")).Get()
    self.assertNotEqual(f.data.hash.sha256, b"")
    self.assertGreater(f.data.hash.num_bytes, 0)
    self.assertGreater(f.data.last_collected, 0)
    self.assertGreater(f.data.last_collected_size, 0)

  def testGetTimeline(self):
    timeline = self.api.Client(
        client_id=self.client_id).File("fs/os").GetTimeline()
    self.assertTrue(timeline)
    for item in timeline:
      self.assertIsInstance(item, vfs_pb2.ApiVfsTimelineItem)

  def testGetTimelineAsCsv(self):
    out = io.BytesIO()
    self.api.Client(client_id=self.client_id).File(
        "fs/os").GetTimelineAsCsv().WriteToStream(out)
    self.assertTrue(out.getvalue())


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
