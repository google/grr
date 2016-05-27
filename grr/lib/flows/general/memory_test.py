#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for memory related flows."""

import copy
import gzip
import json
import os

from grr.client.client_actions import tempfiles
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import filesystem
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import paths as rdf_paths


class DummyDiskVolumeInfo(flow.GRRFlow):
  args_type = filesystem.DiskVolumeInfoArgs

  @flow.StateHandler()
  def Start(self):
    if "/opt" in self.args.path_list[0]:
      mnt = rdf_client.UnixVolume(mount_point="/opt")
      self.SendReply(rdf_client.Volume(unixvolume=mnt,
                                       bytes_per_sector=4096,
                                       sectors_per_allocation_unit=1,
                                       actual_available_allocation_units=10,
                                       total_allocation_units=100))
    else:
      mnt = rdf_client.UnixVolume(mount_point="/var")
      self.SendReply(rdf_client.Volume(unixvolume=mnt,
                                       bytes_per_sector=1,
                                       sectors_per_allocation_unit=1,
                                       actual_available_allocation_units=784165,
                                       total_allocation_units=78416500))


class MemoryTest(test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(MemoryTest, self).setUp()
    test_lib.WriteComponent(token=self.token)


class MemoryCollectorClientMock(action_mocks.MemoryClientMock):

  def __init__(self):
    # Use this file as the mock memory image.
    self.memory_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                    "searching/auth.log")

    # The data in the file.
    with open(self.memory_file, "r") as f:
      self.memory_dump = f.read()

    super(MemoryCollectorClientMock, self).__init__("TransferBuffer",
                                                    "StatFile", "Find",
                                                    "HashBuffer",
                                                    "FingerprintFile",
                                                    "ListDirectory", "WmiQuery",
                                                    "HashFile", "LoadComponent")

  def DeleteGRRTempFiles(self, request):
    self.delete_request = request

    return []

  def RekallAction(self, request):
    self.rekall_request = request

    # Pretend Rekall returned the memory file.
    return [rdf_rekall_types.RekallResponse(json_messages="""
        [["file",{"path": "%s", "pathtype": "TMPFILE"}]]
        """ % self.memory_file,
                                            plugin="aff4acquire"),
            rdf_client.Iterator(state="FINISHED")]


class TestMemoryCollector(MemoryTest):
  """Tests the MemoryCollector flow."""

  def setUp(self):
    super(TestMemoryCollector, self).setUp()

    self.output_path = "analysis/memory_scanner"

    self.key = rdf_crypto.AES128Key("1a5eafcc77d428863d4c2441ea26e5a5")
    self.iv = rdf_crypto.AES128Key("2241b14c64874b1898dad4de7173d8c0")

    self.memory_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                    "searching/auth.log")
    with open(self.memory_file, "r") as f:
      self.memory_dump = f.read()
    self.assertTrue(self.memory_dump)

    self.client_mock = MemoryCollectorClientMock()

    # Ensure there is some data in the memory dump.
    self.assertTrue(self.client_mock.memory_dump)

    self.old_diskvolume_flow = flow.GRRFlow.classes["DiskVolumeInfo"]
    flow.GRRFlow.classes["DiskVolumeInfo"] = DummyDiskVolumeInfo

  def tearDown(self):
    super(TestMemoryCollector, self).tearDown()
    flow.GRRFlow.classes["DiskVolumeInfo"] = self.old_diskvolume_flow

  def RunWithDownload(self):
    self.flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                           flow_name="MemoryCollector",
                                           token=self.token,
                                           output=self.output_path)

    for _ in test_lib.TestFlowHelper(self.flow_urn,
                                     self.client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    return aff4.FACTORY.Open(self.flow_urn, token=self.token)

  def testMemoryImageLocalCopyDownload(self):
    flow_obj = self.RunWithDownload()

    self.assertEqual(flow_obj.state.output_urn,
                     self.client_id.Add("temp").Add(self.memory_file))

    fd = aff4.FACTORY.Open(flow_obj.state.output_urn, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def testChecksDiskSpace(self):
    client = aff4.FACTORY.Create(self.client_id,
                                 aff4_grr.VFSGRRClient,
                                 token=self.token)
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Set(client.Schema.MEMORY_SIZE(64 * 1024 * 1024 * 1024))
    client.Close()

    class ClientMock(MemoryCollectorClientMock):
      """A mock which returns low disk space."""

      def CheckFreeGRRTempSpace(self, _):
        """Mock out the driver loading code to pass the memory image."""
        path = tempfiles.GetDefaultGRRTempDirectory()
        reply = rdf_client.DiskUsage(path=path,
                                     total=10 * 1024 * 1024 * 1024,
                                     used=5 * 1024 * 1024 * 1024,
                                     free=5 * 1024 * 1024 * 1024)
        return [reply]

    self.client_mock = ClientMock()

    e = self.assertRaises(RuntimeError)
    with e:
      self.RunWithDownload()

    self.assertIn("Free space may be too low", str(e.exception))

    # Make sure the flow didnt actually download anything.
    flow_obj = aff4.FACTORY.Open(self.flow_urn, token=self.token)
    self.assertEqual(flow_obj.state.output_urn, None)


class ListVADBinariesActionMock(action_mocks.MemoryClientMock):
  """Client with real file actions and mocked-out RekallAction."""

  def __init__(self, process_list=None):
    super(ListVADBinariesActionMock, self).__init__("TransferBuffer",
                                                    "StatFile", "Find",
                                                    "HashBuffer",
                                                    "FingerprintFile",
                                                    "ListDirectory", "WmiQuery",
                                                    "HashFile", "LoadComponent")
    self.process_list = process_list or []

  def RekallAction(self, _):
    ps_list_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                "rekall_vad_result.dat.gz")
    response = rdf_rekall_types.RekallResponse(
        json_messages=gzip.open(ps_list_file, "rb").read(),
        plugin="pslist")

    # If we are given process names here we need to craft a Rekall result
    # containing them. This is so they point to valid files in the fixture.
    if self.process_list:
      json_data = json.loads(response.json_messages)
      template = json_data[7]
      if template[1]["filename"] != ur"\Windows\System32\ntdll.dll":
        raise RuntimeError("Test data invalid.")

      json_data = []
      for process in self.process_list:
        new_entry = copy.deepcopy(template)
        new_entry[1]["filename"] = process
        json_data.append(new_entry)
      response.json_messages = json.dumps(json_data)

    return [response, rdf_client.Iterator(state="FINISHED")]


class ListVADBinariesTest(MemoryTest):
  """Tests the Rekall-powered "get processes binaries" flow."""

  def setUp(self):
    super(ListVADBinariesTest, self).setUp()
    self.SetupClients(1, system="Windows", os_version="6.2", arch="AMD64")
    self.os_overrider = test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                              test_lib.ClientVFSHandlerFixture)
    self.reg_overrider = test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY, test_lib.FakeRegistryVFSHandler)
    self.os_overrider.Start()
    self.reg_overrider.Start()

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
    kb.environ_systemdrive = "C:"
    kb.MergeOrAddUser(rdf_client.User(username="LocalService",
                                      userdomain="testing-PC",
                                      homedir=r"C:\Users\localservice",
                                      sid="S-1-5-20"))
    fd.Set(kb)
    fd.Close()

  def tearDown(self):
    super(ListVADBinariesTest, self).tearDown()
    self.os_overrider.Stop()
    self.reg_overrider.Stop()

  def testListsBinaries(self):
    client_mock = ListVADBinariesActionMock()
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper("ListVADBinaries",
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token,
                                     output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)

    # Sorting output collection to make the test deterministic
    paths = sorted([x.CollapsePath() for x in fd])
    self.assertIn(u"C:\\Windows\\System32\\wintrust.dll", paths)
    self.assertIn(u"C:\\Program Files\\Internet Explorer\\ieproxy.dll", paths)

  def testFetchesAndStoresBinary(self):
    process1_exe = "\\WINDOWS\\bar.exe"
    process2_exe = "\\WINDOWS\\foo.exe"

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper("ListVADBinaries",
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token,
                                     fetch_binaries=True,
                                     output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)

    # Sorting output collection to make the test deterministic
    binaries = sorted(fd, key=lambda x: x.aff4path)

    self.assertEqual(len(binaries), 2)

    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    self.assertEqual(binaries[1].pathspec.CollapsePath(), "/C:/WINDOWS/foo.exe")

    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")
    fd = aff4.FACTORY.Open(binaries[1].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "this is foo")

  def testDoesNotFetchDuplicates(self):
    process = "\\WINDOWS\\bar.exe"
    client_mock = ListVADBinariesActionMock([process, process])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper("ListVADBinaries",
                                     client_mock,
                                     client_id=self.client_id,
                                     fetch_binaries=True,
                                     token=self.token,
                                     output=output_path):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)
    binaries = list(fd)

    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")

  def testConditionsOutBinariesUsingRegex(self):
    process1_exe = "\\WINDOWS\\bar.exe"
    process2_exe = "\\WINDOWS\\foo.exe"

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper("ListVADBinaries",
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token,
                                     output=output_path,
                                     filename_regex=".*bar\\.exe$",
                                     fetch_binaries=True):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)
    binaries = list(fd)

    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")

  def testIgnoresMissingFiles(self):
    process1_exe = "\\WINDOWS\\bar.exe"

    client_mock = ListVADBinariesActionMock([process1_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper("ListVADBinaries",
                                     client_mock,
                                     check_flow_errors=False,
                                     client_id=self.client_id,
                                     token=self.token,
                                     output=output_path,
                                     fetch_binaries=True):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)
    binaries = list(fd)

    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
