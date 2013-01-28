#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

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

"""Tests for the Timelines flow."""

from grr.client import vfs
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestTimelines(test_lib.FlowTestsBaseclass):
  """Test the timelines flow."""

  client_id = "C.0000000000000005"

  def testMACTimes(self):
    """Test that the timelining works with files."""
    # Install the mock
    vfs.VFS_HANDLERS[
        rdfvalue.RDFPathSpec.Enum("OS")] = test_lib.ClientVFSHandlerFixture

    client_mock = test_lib.ActionMock("ListDirectory")
    output_path = "analysis/Timeline/MAC"

    pathspec = rdfvalue.RDFPathSpec(path="/",
                                    pathtype=rdfvalue.RDFPathSpec.Enum("OS"))

    for _ in test_lib.TestFlowHelper(
        "RecursiveListDirectory", client_mock, client_id=self.client_id,
        pathspec=pathspec, token=self.token):
      pass

    # Now make a timeline
    for _ in test_lib.TestFlowHelper(
        "MACTimes", client_mock, client_id=self.client_id, token=self.token,
        path="aff4:/%s/" % self.client_id, output=output_path):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(
        output_path), token=self.token)

    timestamp = 0
    events = list(fd.Query("event.stat.pathspec.path contains grep"))

    for event in events:
      # Check the times are monotonously increasing.
      self.assert_(event.event.timestamp >= timestamp)
      timestamp = event.event.timestamp

      self.assert_("grep" in event.event.stat.pathspec.path)

    # 9 files, each having mac times = 27 events.
    self.assertEqual(len(events), 27)
