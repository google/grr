#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import os
import stat as stat_mode

from absl.testing import absltest
from typing import Iterator

from grr_response_client.client_actions import timeline as timeline_action
from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import temp
from grr_response_server.flows.general import timeline as timeline_flow
from grr.test_lib import action_mocks
from grr.test_lib import filesystem_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import testing_startup


class TimelineTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super(TimelineTest, cls).setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super(TimelineTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def testSingleFile(self):
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

  def testMultipleFiles(self):
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

  # TODO(hanuszczak): Add tests for symlinks.
  # TODO(hanuszczak): Add tests for timestamps.

  def _Collect(self, root):
    args = rdf_timeline.TimelineArgs(root=root)

    flow_id = flow_test_lib.TestFlowHelper(
        timeline_flow.TimelineFlow.__name__,
        action_mocks.ActionMock(timeline_action.Timeline),
        client_id=self.client_id,
        token=self.token,
        args=args)

    flow_test_lib.FinishAllFlowsOnClient(self.client_id)

    return timeline_flow.Entries(client_id=self.client_id, flow_id=flow_id)


if __name__ == "__main__":
  absltest.main()
