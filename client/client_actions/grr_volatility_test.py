#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""Tests for grr.client.client_actions.grr_volatility."""


import os

import logging

from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2


class GrrVolatilityTest(test_lib.EmptyActionTest):

  def SetupRequest(self, plugin):
    # Only run this test if the image file is found.
    image_path = os.path.join(self.base_path, "win7_trial_64bit.raw")
    if not os.access(image_path, os.R_OK):
      logging.warning("Unable to locate test memory image. Skipping test.")
      return False

    self.request = jobs_pb2.VolatilityRequest()

    # In this test we explicitly set the profile to use.
    self.request.profile = "Win7SP1x64"
    self.request.plugins.append(plugin)

    # Use the memory image in the pathspec.
    self.request.device.path = image_path
    self.request.device.pathtype = jobs_pb2.Path.OS

    return True

  def testPsList(self):
    """Tests that we can run a simple PsList Action."""
    if not self.SetupRequest("pslist"):
      return

    result = self.RunAction("VolatilityAction", self.request)

    # There should be 1 result back.
    self.assertEqual(len(result), 1)

    # There should be one section.
    self.assertEqual(len(result[0].sections), 1)

    rows = result[0].sections[0].table.rows
    # Pslist should have 32 results.
    self.assertEqual(len(rows), 32)

    names = [row.values[1].svalue for row in rows]

    # And should include the DumpIt binary.
    self.assertTrue("DumpIt.exe" in names)
    self.assertTrue("conhost.exe" in names)

  def testParameters(self):
    if not self.SetupRequest("pslist"):
      return

    args = {"pslist": {"pid": 2860}}

    self.request.args.MergeFrom(utils.ProtoDict(args).ToProto())

    result = self.RunAction("VolatilityAction", self.request)

    # There should be 1 result back.
    self.assertEqual(len(result), 1)

    # There should be one section.
    self.assertEqual(len(result[0].sections), 1)

    rows = result[0].sections[0].table.rows
    # Pslist should now have 1 result.
    self.assertEqual(len(rows), 1)

    name = rows[0].values[1].svalue

    self.assertTrue("DumpIt.exe" in name)

  def testDLLList(self):
    """Tests that we can run a simple DLLList Action."""
    if not self.SetupRequest("dlllist"):
      return

    result = self.RunAction("VolatilityAction", self.request)

    self.assertEqual(len(result), 1)
    sections = result[0].sections
    self.assertEqual(len(sections), 60)

    dumpit = result[0].sections[-4]
    dumpitheader = dumpit.formatted_value_list.formatted_values[1]

    self.assertEqual(dumpitheader.formatstring, "{0} pid: {1:6}\n")
    self.assertEqual(dumpitheader.data.values[0].svalue, "DumpIt.exe")
    self.assertEqual(dumpitheader.data.values[1].value, 2860)

    dumpitdlls = result[0].sections[-3]

    dlls = [entry.values[2].svalue for entry in dumpitdlls.table.rows]

    self.assertTrue(any(["DumpIt.exe" in name for name in dlls]))
    self.assertTrue(any(["ntdll.dll" in name for name in dlls]))
    self.assertTrue(any(["wow64.dll" in name for name in dlls]))
