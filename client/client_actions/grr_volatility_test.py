#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Tests for grr.client.client_actions.grr_volatility."""


import os

import logging

from grr.lib import rdfvalue
from grr.lib import test_lib


class GrrVolatilityTest(test_lib.EmptyActionTest):

  def SetupRequest(self, plugin):
    # Only run this test if the image file is found.
    image_path = os.path.join(self.base_path, "win7_trial_64bit.raw")
    if not os.access(image_path, os.R_OK):
      logging.warning("Unable to locate test memory image. Skipping test.")
      return False

    self.request = rdfvalue.VolatilityRequest(
        device=rdfvalue.PathSpec(path=image_path,
                                 pathtype=rdfvalue.PathSpec.PathType.OS),
        # To speed up the test we provide these values. In real life these
        # values will be provided by the kernel driver.
        session=rdfvalue.Dict(
            dtb=0x187000, kdbg=0xF80002803070))

    # In this test we explicitly do not set the profile to use so we can see if
    # the profile autodetection works.

    # Add the plugin to the request.
    self.request.args[plugin] = None

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

    self.request.args = rdfvalue.Dict(args)

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
