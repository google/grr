#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import stat as stat_mode
from typing import Iterator

from absl.testing import absltest

from grr_response_client.client_actions import timeline as timeline_action
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import temp
from grr_response_proto import timeline_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.flows.general import timeline as timeline_flow
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import filesystem_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import testing_startup


class TimelineTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super(TimelineTest, cls).setUpClass()
    testing_startup.TestInit()

  def setUp(self) -> None:
    super(TimelineTest, self).setUp()
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
      self.assertCountEqual(paths, [
          os.path.join(dirpath),
          os.path.join(dirpath, "foo"),
          os.path.join(dirpath, "foo", "bar"),
          os.path.join(dirpath, "foo", "bar", "baz"),
          os.path.join(dirpath, "foo", "bar", "baz", "quux"),
          os.path.join(dirpath, "foo", "bar", "baz", "quux", "thud"),
          os.path.join(dirpath, "foo", "bar", "blargh"),
      ])

      entries_by_path = {entry.path.decode("utf-8"): entry for entry in entries}
      self.assertEqual(entries_by_path[thud_filepath].size, 4)
      self.assertEqual(entries_by_path[blargh_filepath].size, 6)

  @db_test_lib.WithDatabase
  def testLogsWarningIfBtimeNotSupported(self, db: abstract_db.Database):
    client_id = self.client_id
    db.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.timeline_btime_support = False
    db.WriteClientSnapshot(snapshot)

    with temp.AutoTempDirPath() as tempdir:
      args = rdf_timeline.TimelineArgs(root=tempdir.encode("utf-8"))

      flow_id = flow_test_lib.TestFlowHelper(
          timeline_flow.TimelineFlow.__name__,
          action_mocks.ActionMock(timeline_action.Timeline),
          client_id=client_id,
          token=self.token,
          args=args)

      flow_test_lib.FinishAllFlowsOnClient(client_id)

    log_entries = db.ReadFlowLogEntries(client_id, flow_id, offset=0, count=1)
    self.assertLen(log_entries, 1)
    self.assertRegex(log_entries[0].message, "birth time is not supported")

  @db_test_lib.WithDatabase
  def testNoLogsIfBtimeSupported(self, db: abstract_db.Database):
    client_id = self.client_id
    db.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "Linux"
    snapshot.startup_info.client_info.timeline_btime_support = True
    db.WriteClientSnapshot(snapshot)

    with temp.AutoTempDirPath() as tempdir:
      args = rdf_timeline.TimelineArgs(root=tempdir.encode("utf-8"))

      flow_id = flow_test_lib.TestFlowHelper(
          timeline_flow.TimelineFlow.__name__,
          action_mocks.ActionMock(timeline_action.Timeline),
          client_id=client_id,
          token=self.token,
          args=args)

      flow_test_lib.FinishAllFlowsOnClient(client_id)

    log_entries = db.ReadFlowLogEntries(client_id, flow_id, offset=0, count=1)
    self.assertEmpty(log_entries)

  # TODO(hanuszczak): Add tests for symlinks.
  # TODO(hanuszczak): Add tests for timestamps.

  def _Collect(self, root: bytes) -> Iterator[timeline_pb2.TimelineEntry]:
    args = rdf_timeline.TimelineArgs(root=root)

    flow_id = flow_test_lib.TestFlowHelper(
        timeline_flow.TimelineFlow.__name__,
        action_mocks.ActionMock(timeline_action.Timeline),
        client_id=self.client_id,
        token=self.token,
        args=args)

    flow_test_lib.FinishAllFlowsOnClient(self.client_id)

    return timeline_flow.ProtoEntries(client_id=self.client_id, flow_id=flow_id)


if __name__ == "__main__":
  absltest.main()
