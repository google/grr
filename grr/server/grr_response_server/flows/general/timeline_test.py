#!/usr/bin/env python
from collections.abc import Iterator
import os
import stat as stat_mode

from absl.testing import absltest

from grr_response_client.client_actions import timeline as timeline_action
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_timeline
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import temp
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import timeline_pb2
from grr_response_server import blob_store as abstract_bs
from grr_response_server import data_store
from grr_response_server import flow_responses
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import timeline as timeline_flow
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import filesystem_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import testing_startup
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import get_filesystem_timeline_pb2 as rrg_get_filesystem_timeline_pb2


class TimelineTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super(TimelineTest, cls).setUpClass()
    testing_startup.TestInit()

  def setUp(self) -> None:
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testRaisesOnEmptyRoot(self) -> None:
    with self.assertRaisesRegex(RuntimeError, "root directory not specified"):
      self._Collect(b"")

  def testSingleFile(self) -> None:
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo")
      filesystem_test_lib.CreateFile(filepath, content=b"foobar")

      entries = list(self._Collect(dirpath.encode("utf-8")))
      self.assertLen(entries, 2)

      self.assertTrue(stat_mode.S_ISDIR(entries[0].mode))
      self.assertEqual(entries[0].path, dirpath.encode("utf-8"))

      self.assertTrue(stat_mode.S_ISREG(entries[1].mode))
      self.assertEqual(entries[1].path, filepath.encode("utf-8"))
      self.assertEqual(entries[1].size, 6)

  def testMultipleFiles(self) -> None:
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      foo_filepath = os.path.join(dirpath, "foo")
      filesystem_test_lib.CreateFile(foo_filepath)

      bar_filepath = os.path.join(dirpath, "bar")
      filesystem_test_lib.CreateFile(bar_filepath)

      baz_filepath = os.path.join(dirpath, "baz")
      filesystem_test_lib.CreateFile(baz_filepath)

      entries = list(self._Collect(dirpath.encode("utf-8")))
      self.assertLen(entries, 4)

      self.assertTrue(stat_mode.S_ISDIR(entries[0].mode))
      self.assertEqual(entries[0].path, dirpath.encode("utf-8"))

      paths = [_.path for _ in entries[1:]]
      self.assertIn(foo_filepath.encode("utf-8"), paths)
      self.assertIn(bar_filepath.encode("utf-8"), paths)
      self.assertIn(baz_filepath.encode("utf-8"), paths)

      for entry in entries[1:]:
        self.assertTrue(stat_mode.S_ISREG(entry.mode))

  def testNestedHierarchy(self):
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      thud_filepath = os.path.join(dirpath, "foo", "bar", "baz", "quux", "thud")
      filesystem_test_lib.CreateFile(thud_filepath, content=b"thud")

      blargh_filepath = os.path.join(dirpath, "foo", "bar", "blargh")
      filesystem_test_lib.CreateFile(blargh_filepath, content=b"blargh")

      entries = list(self._Collect(dirpath.encode("utf-8")))
      self.assertLen(entries, 7)

      paths = [_.path.decode("utf-8") for _ in entries]
      self.assertCountEqual(
          paths,
          [
              os.path.join(dirpath),
              os.path.join(dirpath, "foo"),
              os.path.join(dirpath, "foo", "bar"),
              os.path.join(dirpath, "foo", "bar", "baz"),
              os.path.join(dirpath, "foo", "bar", "baz", "quux"),
              os.path.join(dirpath, "foo", "bar", "baz", "quux", "thud"),
              os.path.join(dirpath, "foo", "bar", "blargh"),
          ],
      )

      entries_by_path = {entry.path.decode("utf-8"): entry for entry in entries}
      self.assertEqual(entries_by_path[thud_filepath].size, 4)
      self.assertEqual(entries_by_path[blargh_filepath].size, 6)

  def testProgress(self):
    client_id = self.client_id

    with temp.AutoTempDirPath(remove_non_empty=True) as tempdir:
      filesystem_test_lib.CreateFile(os.path.join(tempdir, "foo"))
      filesystem_test_lib.CreateFile(os.path.join(tempdir, "bar"))
      filesystem_test_lib.CreateFile(os.path.join(tempdir, "baz"))

      args = rdf_timeline.TimelineArgs()
      args.root = tempdir.encode("utf-8")

      flow_id = flow_test_lib.StartFlow(
          timeline_flow.TimelineFlow, client_id=client_id, flow_args=args
      )

      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      progress = timeline_pb2.TimelineProgress()
      assert flow_obj.progress.Unpack(progress)
      self.assertEqual(progress.total_entry_count, 0)

      flow_test_lib.RunFlow(
          client_id=client_id,
          flow_id=flow_id,
          client_mock=action_mocks.ActionMock(timeline_action.Timeline),
      )

      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      progress = timeline_pb2.TimelineProgress()
      assert flow_obj.progress.Unpack(progress)
      self.assertEqual(progress.total_entry_count, 4)

  @db_test_lib.WithDatabase
  def testLogsWarningIfBtimeNotSupported(self, db: abstract_db.Database):
    client_id = self.client_id
    db.WriteClientMetadata(client_id)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.timeline_btime_support = False
    db.WriteClientSnapshot(snapshot)

    with temp.AutoTempDirPath() as tempdir:
      args = rdf_timeline.TimelineArgs(root=tempdir.encode("utf-8"))

      flow_id = flow_test_lib.StartAndRunFlow(
          timeline_flow.TimelineFlow,
          action_mocks.ActionMock(timeline_action.Timeline),
          client_id=client_id,
          creator=self.test_username,
          flow_args=args,
      )

      flow_test_lib.FinishAllFlowsOnClient(client_id)

    log_entries = db.ReadFlowLogEntries(client_id, flow_id, offset=0, count=1)
    self.assertLen(log_entries, 1)
    self.assertRegex(log_entries[0].message, "birth time is not supported")

  @db_test_lib.WithDatabase
  def testNoLogsIfBtimeSupported(self, db: abstract_db.Database):
    client_id = self.client_id
    db.WriteClientMetadata(client_id)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.timeline_btime_support = True
    db.WriteClientSnapshot(snapshot)

    with temp.AutoTempDirPath() as tempdir:
      args = rdf_timeline.TimelineArgs(root=tempdir.encode("utf-8"))

      flow_id = flow_test_lib.StartAndRunFlow(
          timeline_flow.TimelineFlow,
          action_mocks.ActionMock(timeline_action.Timeline),
          client_id=client_id,
          creator=self.test_username,
          flow_args=args,
      )

      flow_test_lib.FinishAllFlowsOnClient(client_id)

    log_entries = db.ReadFlowLogEntries(client_id, flow_id, offset=0, count=1)
    self.assertEmpty(log_entries)

  def testSymlink(self) -> None:
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      target_path = os.path.join(dirpath, "target")
      filesystem_test_lib.CreateFile(target_path, content=b"target_content")

      link_path = os.path.join(dirpath, "link")
      os.symlink(target_path, link_path)

      entries = list(self._Collect(dirpath.encode("utf-8")))
      self.assertLen(entries, 3)

      paths = [_.path.decode("utf-8") for _ in entries]
      self.assertCountEqual(
          paths,
          [
              dirpath,
              target_path,
              link_path,
          ],
      )

      entries_by_path = {entry.path.decode("utf-8"): entry for entry in entries}

      self.assertTrue(stat_mode.S_ISREG(entries_by_path[target_path].mode))
      self.assertEqual(entries_by_path[target_path].size, 14)

      self.assertTrue(stat_mode.S_ISLNK(entries_by_path[link_path].mode))
      # Symlink size varies by platform, so we don't assert on it.

  def testTimestamps(self) -> None:
    with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
      filepath = os.path.join(dirpath, "foo")
      filesystem_test_lib.CreateFile(filepath, content=b"foobar")

      # Set specific timestamps to test against.
      atime = 1234567890
      mtime = 1234567891
      os.utime(filepath, (atime, mtime))

      # ctime and btime are harder to mock reliably across platforms,
      # so we check for their presence and basic validity.

      entries = list(self._Collect(dirpath.encode("utf-8")))
      self.assertLen(entries, 2)

      entries_by_path = {entry.path.decode("utf-8"): entry for entry in entries}
      file_entry = entries_by_path[filepath]

      self.assertEqual(file_entry.atime_ns / 1e9, atime)
      self.assertEqual(file_entry.mtime_ns / 1e9, mtime)
      self.assertGreater(file_entry.ctime_ns, 0)

  def _Collect(self, root: bytes) -> Iterator[timeline_pb2.TimelineEntry]:
    args = rdf_timeline.TimelineArgs(root=root)

    flow_id = flow_test_lib.StartAndRunFlow(
        timeline_flow.TimelineFlow,
        action_mocks.ActionMock(timeline_action.Timeline),
        client_id=self.client_id,
        creator=self.test_username,
        flow_args=args,
    )

    flow_test_lib.FinishAllFlowsOnClient(self.client_id)

    return timeline_flow.ProtoEntries(client_id=self.client_id, flow_id=flow_id)

  @db_test_lib.WithDatabase
  @db_test_lib.WithDatabaseBlobstore
  def testHandleRRGGetFilesystemTimeline(
      self,
      db: abstract_db.Database,
      bs: abstract_bs.BlobStore,
  ):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    args = rdf_timeline.TimelineArgs()
    args.root = b"/foo/bar"

    result = rrg_get_filesystem_timeline_pb2.Result()
    result.blob_sha256 = bytes(bs.WriteBlobWithUnknownHash(os.urandom(1024)))
    result.entry_count = 1337

    result_response = rdf_flow_objects.FlowResponse()
    result_response.any_payload = rdf_structs.AnyValue.PackProto2(result)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response,
        status_response,
    ])

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = timeline_flow.TimelineFlow.__name__
    rdf_flow.args = args

    flow = timeline_flow.TimelineFlow(rdf_flow)
    flow.Start()
    flow.HandleRRGGetFilesystemTimeline(responses)

    self.assertEqual(flow.progress.total_entry_count, 1337)

  @db_test_lib.WithDatabase
  def testRRG_NonAbsolute_POSIX(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = timeline_pb2.TimelineArgs()
    args.root = "foo/bar".encode("utf-8")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=timeline_flow.TimelineFlow,
        flow_args=mig_timeline.ToRDFTimelineArgs(args),
        handlers={},
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertEqual(flow_obj.error_message, "Non-absolute path: foo/bar")

  @db_test_lib.WithDatabase
  def testRRG_NonAbsolute_Windows(
      self,
      db: abstract_db.Database,
  ):
    client_id = db_test_utils.InitializeRRGClient(
        db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = timeline_pb2.TimelineArgs()
    args.root = "/".encode("utf-8")

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=timeline_flow.TimelineFlow,
        flow_args=mig_timeline.ToRDFTimelineArgs(args),
        handlers={},
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertEqual(flow_obj.error_message, "Non-absolute path: /")


class FilesystemTypeTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testFlowWithNoResult(self, db: abstract_db.Database) -> None:
    client_id = "C.1234567890123456"
    flow_id = "ABCDEF92"

    db.WriteClientMetadata(client_id, last_ping=rdfvalue.RDFDatetime.Now())

    flow_obj = rdf_flow_objects.Flow()
    flow_obj.client_id = client_id
    flow_obj.flow_id = flow_id
    flow_obj.flow_class_name = timeline_flow.TimelineFlow.__name__
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj))

    self.assertIsNone(timeline_flow.FilesystemType(client_id, flow_id))

  @db_test_lib.WithDatabase
  def testFlowWithResult(self, db: abstract_db.Database) -> None:
    client_id = "C.1234567890123456"
    flow_id = "ABCDEF92"

    db.WriteClientMetadata(client_id, last_ping=rdfvalue.RDFDatetime.Now())

    flow_obj = rdf_flow_objects.Flow()
    flow_obj.client_id = client_id
    flow_obj.flow_id = flow_id
    flow_obj.flow_class_name = timeline_flow.TimelineFlow.__name__
    db.WriteFlowObject(mig_flow_objects.ToProtoFlow(flow_obj))

    flow_result = rdf_flow_objects.FlowResult()
    flow_result.client_id = client_id
    flow_result.flow_id = flow_id
    flow_result.payload = rdf_timeline.TimelineResult(filesystem_type="ntfs")
    db.WriteFlowResults([mig_flow_objects.ToProtoFlowResult(flow_result)])

    self.assertEqual(timeline_flow.FilesystemType(client_id, flow_id), "ntfs")


if __name__ == "__main__":
  absltest.main()
