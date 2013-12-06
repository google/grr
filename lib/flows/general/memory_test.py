#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for Memory."""

import os

import logging

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestMemoryAnalysis(test_lib.FlowTestsBaseclass):
  """Tests the memory analysis flows."""

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
    for _ in test_lib.TestFlowHelper("LoadMemoryDriver",
                                     test_lib.MemoryClientMock(),
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

    class ClientMock(test_lib.MemoryClientMock):
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
    request.args["pslist"] = {}
    request.args["modules"] = {}

    # To speed up the test we provide these values. In real life these values
    # will be provided by the kernel driver.
    request.session = rdfvalue.Dict(
        dtb=0x187000, kdbg=0xF80002803070)

    # Allow the real VolatilityAction to run against the image.
    for _ in test_lib.TestFlowHelper(
        "AnalyzeClientMemory", ClientMock("VolatilityAction"),
        token=self.token, client_id=self.client_id,
        request=request, output="analysis/memory"):
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

  def testScanMemory(self):
    # Use a file in place of a memory image for simplicity
    image_path = os.path.join(self.base_path, "numbers.txt")

    self.CreateClient()
    self.CreateSignedDriver()

    class ClientMock(test_lib.MemoryClientMock):
      """A mock which returns the image as the driver path."""

      def GetMemoryInformation(self, _):
        """Mock out the driver loading code to pass the memory image."""
        reply = rdfvalue.MemoryInformation(
            device=rdfvalue.PathSpec(
                path=image_path,
                pathtype=rdfvalue.PathSpec.PathType.OS))

        reply.runs.Append(offset=0, length=1000000000)

        return [reply]

    args = dict(grep=rdfvalue.BareGrepSpec(
        literal="88",
        mode="ALL_HITS",
        ),
                output="analysis/grep/testing")

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "ScanMemory", ClientMock("Grep"), client_id=self.client_id,
        token=self.token, **args):
      pass

    fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("/analysis/grep/testing"),
        token=self.token)
    self.assertEqual(len(fd), 20)
    self.assertEqual(fd[0].offset, 252)
    self.assertEqual(fd[0].data, "\n85\n86\n87\n88\n89\n90\n91\n")


class ListVADBinariesActionMock(test_lib.ActionMock):
  """Client with real file actions and mocked-out VolatilityAction."""

  def __init__(self, processes_list):
    super(ListVADBinariesActionMock, self).__init__(
        "TransferBuffer", "StatFile", "Find", "HashBuffer", "HashFile")
    self.processes_list = processes_list

  def VolatilityAction(self, _):
    volatility_response = rdfvalue.VolatilityResult()

    section = rdfvalue.VolatilitySection()
    section.table.headers.Append(print_name="Protection", name="protection")
    section.table.headers.Append(print_name="start", name="start_pfn")
    section.table.headers.Append(print_name="Filename", name="filename")

    for proc in self.processes_list:
      section.table.rows.Append(values=[
          rdfvalue.VolatilityValue(
              type="__MMVAD_FLAGS", name="VadFlags",
              offset=0, vm="None", value=7,
              svalue="EXECUTE_WRITECOPY"),

          rdfvalue.VolatilityValue(
              value=42),

          rdfvalue.VolatilityValue(
              type="_UNICODE_STRING", name="FileName",
              offset=275427702111096,
              vm="AMD64PagedMemory@0x00187000 (Kernel AS@0x187000)",
              value=275427702111096, svalue=proc)
          ])
    volatility_response.sections.Append(section)

    return [volatility_response]


class ListVADBinariesTest(test_lib.FlowTestsBaseclass):
  """Tests the Volatility-powered "get processes binaries" flow."""

  def testListsBinaries(self):
    process1_exe = os.path.join(self.base_path, "test_img.dd")
    process2_exe = os.path.join(self.base_path, "winexec_img.dd")

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper(
        "ListVADBinaries",
        client_mock,
        client_id=self.client_id,
        token=self.token,
        output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)

    # Sorting output collection to make the test deterministic
    binaries = sorted(fd, key=str)
    self.assertListEqual(binaries, [process1_exe, process2_exe])

  def testFetchesAndStoresBinary(self):
    process1_exe = os.path.join(self.base_path, "test_img.dd")
    process2_exe = os.path.join(self.base_path, "winexec_img.dd")

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper(
        "ListVADBinaries",
        client_mock,
        client_id=self.client_id,
        token=self.token,
        fetch_binaries=True,
        output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)

    # Sorting output collection to make the test deterministic
    binaries = sorted(fd, key=lambda x: x.aff4path)

    self.assertEqual(len(binaries), 2)

    self.assertEqual(binaries[0].pathspec.path, process1_exe)
    self.assertEqual(binaries[0].st_size, os.stat(process1_exe).st_size)

    self.assertEqual(binaries[1].pathspec.path, process2_exe)
    self.assertEqual(binaries[1].st_size, os.stat(process2_exe).st_size)

  def testDoesNotFetchDuplicates(self):
    process_exe = os.path.join(self.base_path, "test_img.dd")
    client_mock = ListVADBinariesActionMock([process_exe, process_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper(
        "ListVADBinaries",
        client_mock,
        client_id=self.client_id,
        fetch_binaries=True,
        token=self.token,
        output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    binaries = list(fd)

    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.path, process_exe)
    self.assertEqual(binaries[0].st_size, os.stat(process_exe).st_size)

  def testFiltersOutBinariesUsingRegex(self):
    process1_exe = os.path.join(self.base_path, "test_img.dd")
    process2_exe = os.path.join(self.base_path, "empty_file")

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper(
        "ListVADBinaries",
        client_mock,
        client_id=self.client_id,
        token=self.token,
        output=output_path,
        filename_regex=".*\\.dd$",
        fetch_binaries=True):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    binaries = list(fd)

    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.path, process1_exe)
    self.assertEqual(binaries[0].st_size, os.stat(process1_exe).st_size)

  def testIgnoresMissingFiles(self):
    process1_exe = os.path.join(self.base_path, "test_img.dd")
    process2_exe = os.path.join(self.base_path, "file_that_does_not_exist")

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper(
        "ListVADBinaries",
        client_mock,
        check_flow_errors=False,
        client_id=self.client_id,
        token=self.token,
        output=output_path,
        fetch_binaries=True):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    binaries = list(fd)
    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.path, process1_exe)
    self.assertEqual(binaries[0].st_size, os.stat(process1_exe).st_size)
