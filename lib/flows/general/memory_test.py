#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for Memory."""

import os

import logging

from grr.lib import aff4
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestMemoryAnalysis(test_lib.FlowTestsBaseclass):
  """Tests the memory analysis flows."""

  class MockClient(test_lib.ActionMock):
    """A mock of client state."""

    def InstallDriver(self, _):
      return []

    def UninstallDriver(self, _):
      return []

    def GetMemoryInformation(self, _):
      reply = rdfvalue.MemoryInformation(
          device=rdfvalue.PathSpec(
              path=r"\\.\pmem",
              pathtype=rdfvalue.PathSpec.PathType.MEMORY))
      reply.runs.Append(offset=0x1000, length=0x10000)
      reply.runs.Append(offset=0x20000, length=0x10000)

      return [reply]

  def CreateSignedDriver(self):
    # Make sure there is a signed driver for our client.
    driver_path = maintenance_utils.UploadSignedDriverBlob(
        "MZ Driveeerrrrrr", file_name="winpmem.amd64.sys",
        platform="Windows", arch="i386",
        aff4_path="/config/drivers/windows/memory/{file_name}",
        token=self.token)

    logging.info("Wrote signed driver to %s", driver_path)

  def CreateClient(self):
    client = aff4.FACTORY.Create(self.client_id,
                                 "VFSGRRClient", token=self.token)
    client.Set(client.Schema.ARCH("AMD64"))
    client.Set(client.Schema.OS_RELEASE("7"))
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Close()

  def testLoadDriverWindows(self):
    """Tests the memory driver deployment flow."""
    self.CreateSignedDriver()
    self.CreateClient()

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("LoadMemoryDriver", self.MockClient(),
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    device_urn = self.client_id.Add("devices/memory")
    fd = aff4.FACTORY.Open(device_urn, mode="r", token=self.token)
    runs = fd.Get(fd.Schema.LAYOUT).runs

    self.assertEqual(runs[0].offset, 0x1000)
    self.assertEqual(runs[0].length, 0x10000)
    self.assertEqual(runs[1].offset, 0x20000)
    self.assertEqual(runs[0].length, 0x10000)

  def testVolatilityModules(self):
    """Tests the end to end volatility memory analysis."""
    image_path = os.path.join(self.base_path, "win7_trial_64bit.raw")
    if not os.access(image_path, os.R_OK):
      logging.warning("Unable to locate test memory image. Skipping test.")
      return

    self.CreateClient()
    self.CreateSignedDriver()

    class ClientMock(self.MockClient):
      """A mock which returns the image as the driver path."""

      def GetMemoryInformation(self, _):
        """Mock out the driver loading code to pass the memory image."""
        reply = rdfvalue.MemoryInformation(
            device=rdfvalue.PathSpec(
                path=image_path,
                pathtype=rdfvalue.PathSpec.PathType.OS))

        reply.runs.Append(offset=0, length=1000000000)

        return [reply]

    request = rdfvalue.VolatilityRequest()
    request.plugins.Append("pslist")
    request.plugins.Append("modules")

    # To speed up the test we provide these values. In real life these values
    # will be provided by the kernel driver.
    request.session = rdfvalue.Dict(
        dtb=0x187000, kdbg=0xF80002803070)

    # Allow the real VolatilityAction to run against the image.
    for _ in test_lib.TestFlowHelper(
        "AnalyzeClientMemory", ClientMock("VolatilityAction"),
        token=self.token, client_id=self.client_id,
        request=request, output="analysis/memory/{p}"):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add("analysis/memory/pslist"),
                           token=self.token)

    result = fd.Get(fd.Schema.RESULT)

    # Pslist should have 32 rows.
    self.assertEqual(len(result.sections[0].table.rows), 32)

    # And should include the DumpIt binary.
    self.assert_("DumpIt.exe" in str(result))

    fd = aff4.FACTORY.Open(self.client_id.Add("analysis/memory/modules"),
                           token=self.token)
    result = fd.Get(fd.Schema.RESULT)

    # Modules should have 133 lines.
    self.assertEqual(len(result.sections[0].table.rows), 133)

    # And should include the DumpIt kernel driver.
    self.assert_("DumpIt.sys" in str(result))

  def testGrepMemory(self):
    # Use a file in place of a memory image for simplicity
    image_path = os.path.join(self.base_path, "numbers.txt")

    self.CreateClient()
    self.CreateSignedDriver()

    class ClientMock(self.MockClient):
      """A mock which returns the image as the driver path."""

      def GetMemoryInformation(self, _):
        """Mock out the driver loading code to pass the memory image."""
        reply = rdfvalue.MemoryInformation(
            device=rdfvalue.PathSpec(
                path=image_path,
                pathtype=rdfvalue.PathSpec.PathType.OS))

        reply.runs.Append(offset=0, length=1000000000)

        return [reply]

    args = {"request": rdfvalue.GrepSpec(
        literal="88",
        mode=rdfvalue.GrepSpec.Mode.ALL_HITS
        ),
            "output": "analysis/grep/testing"}

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "GrepMemory", ClientMock("Grep"), client_id=self.client_id,
        token=self.token, **args):
      pass

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("/analysis/grep/testing"),
        token=self.token)
    self.assertEqual(len(fd), 20)
    self.assertEqual(fd[0].offset, 252)
    self.assertEqual(fd[0].data, "\n85\n86\n87\n88\n89\n90\n91\n")
