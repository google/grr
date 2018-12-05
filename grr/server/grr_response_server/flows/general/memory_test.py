#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for memory related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy
import functools
import gzip
import io
import json
import os

from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_client.client_actions import tempfiles
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.parsers import rekall_artifact_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_server import aff4
from grr_response_server import flow
from grr_response_server import server_stubs
from grr_response_server.aff4_objects import aff4_grr
# TODO(user): break the dependency cycle described in memory.py and
# and remove this import.
# pylint: disable=unused-import
from grr_response_server.flows.general import collectors
# pylint: enable=unused-import
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import memory
from grr_response_server.flows.general import transfer
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import rekall_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class DummyDiskVolumeInfo(flow.GRRFlow):
  args_type = filesystem.DiskVolumeInfoArgs

  def Start(self):
    if "/opt" in self.args.path_list[0]:
      mnt = rdf_client_fs.UnixVolume(mount_point="/opt")
      self.SendReply(
          rdf_client_fs.Volume(
              unixvolume=mnt,
              bytes_per_sector=4096,
              sectors_per_allocation_unit=1,
              actual_available_allocation_units=10,
              total_allocation_units=100))
    else:
      mnt = rdf_client_fs.UnixVolume(mount_point="/var")
      self.SendReply(
          rdf_client_fs.Volume(
              unixvolume=mnt,
              bytes_per_sector=1,
              sectors_per_allocation_unit=1,
              actual_available_allocation_units=784165,
              total_allocation_units=78416500))


class MemoryTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(MemoryTest, self).setUp()
    self.client_id = self.SetupClient(0)


class MemoryCollectorClientMock(action_mocks.MemoryClientMock):

  def __init__(self):
    # Use this file as the mock memory image.
    self.memory_file = os.path.join(config.CONFIG["Test.data_dir"],
                                    "searching/auth.log")

    # The data in the file.
    with open(self.memory_file, "rb") as f:
      self.memory_dump = f.read()

      super(MemoryCollectorClientMock, self).__init__(
          file_fingerprint.FingerprintFile, searching.Find,
          server_stubs.WmiQuery, standard.ListDirectory)

  def DeleteGRRTempFiles(self, request):
    self.delete_request = request

    return []

  def RekallAction(self, request):
    self.rekall_request = request

    # Pretend Rekall returned the memory file.
    return [
        rdf_rekall_types.RekallResponse(
            json_messages="""
        [["file",{"path": "%s", "pathtype": "TMPFILE"}]]
        """ % self.memory_file,
            plugin="aff4acquire")
    ]


class TestMemoryCollector(MemoryTest):
  """Tests the MemoryCollector flow."""

  def setUp(self):
    super(TestMemoryCollector, self).setUp()

    self.key = rdf_crypto.AES128Key.FromHex("1a5eafcc77d428863d4c2441ea26e5a5")
    self.iv = rdf_crypto.AES128Key.FromHex("2241b14c64874b1898dad4de7173d8c0")

    self.memory_file = os.path.join(config.CONFIG["Test.data_dir"],
                                    "searching/auth.log")
    with open(self.memory_file, "rb") as f:
      self.memory_dump = f.read()
    self.assertTrue(self.memory_dump)

    self.client_mock = MemoryCollectorClientMock()

    # Ensure there is some data in the memory dump.
    self.assertTrue(self.client_mock.memory_dump)

    self.config_overrider = test_lib.ConfigOverrider({
        "Rekall.profile_server":
            rekall_test_lib.TestRekallRepositoryProfileServer.__name__
    })
    self.config_overrider.Start()

  def tearDown(self):
    super(TestMemoryCollector, self).tearDown()
    self.config_overrider.Stop()

  def testMemoryCollectorIsDisabledByDefault(self):
    with self.assertRaisesRegexp(RuntimeError, "Rekall flows are disabled"):
      flow.StartAFF4Flow(
          client_id=self.client_id,
          flow_name=memory.MemoryCollector.__name__,
          token=self.token)

  def RunWithDownload(self):
    with test_lib.ConfigOverrider({"Rekall.enabled": True}):
      self.flow_urn = flow.StartAFF4Flow(
          client_id=self.client_id,
          flow_name=memory.MemoryCollector.__name__,
          token=self.token)

      flow_test_lib.TestFlowHelper(
          self.flow_urn,
          self.client_mock,
          client_id=self.client_id,
          token=self.token)

      return aff4.FACTORY.Open(self.flow_urn, token=self.token)

  def testMemoryImageLocalCopyDownload(self):
    flow_obj = self.RunWithDownload()

    self.assertEqual(flow_obj.state.output_urn,
                     self.client_id.Add("temp").Add(self.memory_file))

    fd = aff4.FACTORY.Open(flow_obj.state.output_urn, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def testChecksDiskSpace(self):
    client = aff4.FACTORY.Create(
        self.client_id, aff4_grr.VFSGRRClient, token=self.token)
    client.Set(client.Schema.SYSTEM("Linux"))
    client.Set(client.Schema.MEMORY_SIZE(64 * 1024 * 1024 * 1024))
    client.Close()

    class ClientMock(MemoryCollectorClientMock):
      """A mock which returns low disk space."""

      def CheckFreeGRRTempSpace(self, _):
        """Mock out the driver loading code to pass the memory image."""
        path = tempfiles.GetDefaultGRRTempDirectory()
        reply = rdf_client_fs.DiskUsage(
            path=path,
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

  def testM2CryptoCipherCompatibility(self):
    path = os.path.join(self.base_path, "m2crypto/send_file_data")
    with io.open(path, "rb") as fd:
      m2crypto_ciphertext = fd.read()

    key = rdf_crypto.EncryptionKey(b"x" * 16)
    iv = rdf_crypto.EncryptionKey(b"y" * 16)

    cipher = rdf_crypto.AES128CBCCipher(key, iv)
    plaintext = cipher.Decrypt(m2crypto_ciphertext)

    self.assertEqual(plaintext, self.memory_dump)


class ListVADBinariesActionMock(action_mocks.MemoryClientMock):
  """Client with real file actions and mocked-out RekallAction."""

  def __init__(self, process_list=None):
    super(ListVADBinariesActionMock, self).__init__(
        file_fingerprint.FingerprintFile, searching.Find,
        standard.ListDirectory, server_stubs.WmiQuery)
    self.process_list = process_list or []

  def RekallAction(self, _):
    ps_list_file = os.path.join(config.CONFIG["Test.data_dir"],
                                "rekall_vad_result.dat.gz")
    response = rdf_rekall_types.RekallResponse(
        json_messages=gzip.open(ps_list_file, "rb").read(), plugin="pslist")

    # If we are given process names here we need to craft a Rekall result
    # containing them. This is so they point to valid files in the fixture.
    if self.process_list:
      json_data = json.loads(response.json_messages)
      template = json_data[7]
      if template[1]["filename"] != u"\\Windows\\System32\\ntdll.dll":
        raise RuntimeError("Test data invalid.")

      json_data = []
      for process in self.process_list:
        new_entry = copy.deepcopy(template)
        new_entry[1]["filename"] = process
        json_data.append(new_entry)
      response.json_messages = json.dumps(json_data)

    return [response]


class ListVADBinariesTest(MemoryTest):
  """Tests the Rekall-powered "get processes binaries" flow."""

  def setUp(self):
    super(ListVADBinariesTest, self).setUp()
    self.SetupClient(0, system="Windows", os_version="6.2", arch="AMD64")
    self.os_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.ClientVFSHandlerFixture)
    self.reg_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.REGISTRY,
        vfs_test_lib.FakeRegistryVFSHandler)
    self.os_overrider.Start()
    self.reg_overrider.Start()

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
    kb.environ_systemdrive = "C:"
    kb.MergeOrAddUser(
        rdf_client.User(
            username="LocalService",
            userdomain="testing-PC",
            # TODO(hanuszczak): Issues with raw unicode literals and escaping
            # '\u' in Python 2. Refactor this once support for it is dropped.
            homedir="C:\\Users\\localservice",
            sid="S-1-5-20"))
    fd.Set(kb)
    fd.Close()

  def tearDown(self):
    super(ListVADBinariesTest, self).tearDown()
    self.os_overrider.Stop()
    self.reg_overrider.Stop()

  @parser_test_lib.WithParser("VAD", rekall_artifact_parser.RekallVADParser)
  def testListVADBinariesIsDisabledByDefault(self):
    with self.assertRaisesRegexp(RuntimeError, "Rekall flows are disabled"):
      flow.StartAFF4Flow(
          client_id=self.client_id,
          flow_name=memory.ListVADBinaries.__name__,
          token=self.token)

  @parser_test_lib.WithParser("VAD", rekall_artifact_parser.RekallVADParser)
  def testListsBinaries(self):
    client_mock = ListVADBinariesActionMock()

    with test_lib.ConfigOverrider({"Rekall.enabled": True}):
      session_id = flow_test_lib.TestFlowHelper(
          memory.ListVADBinaries.__name__,
          client_mock,
          client_id=self.client_id,
          token=self.token)

    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    # Sorting output collection to make the test deterministic
    paths = sorted([x.CollapsePath() for x in fd])
    self.assertIn(u"C:\\Windows\\System32\\wintrust.dll", paths)
    self.assertIn(u"C:\\Program Files\\Internet Explorer\\ieproxy.dll", paths)

  @parser_test_lib.WithParser("VAD", rekall_artifact_parser.RekallVADParser)
  def testFetchesAndStoresBinary(self):
    process1_exe = "\\WINDOWS\\bar.exe"
    process2_exe = "\\WINDOWS\\foo.exe"

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])

    with test_lib.ConfigOverrider({"Rekall.enabled": True}):
      session_id = flow_test_lib.TestFlowHelper(
          memory.ListVADBinaries.__name__,
          client_mock,
          client_id=self.client_id,
          token=self.token,
          fetch_binaries=True)

    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    # Sorting output collection to make the test deterministic
    binaries = sorted(fd, key=lambda x: x.pathspec.path)

    self.assertLen(binaries, 2)

    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    self.assertEqual(binaries[1].pathspec.CollapsePath(), "/C:/WINDOWS/foo.exe")

    fd = aff4.FACTORY.Open(
        binaries[0].AFF4Path(self.client_id), token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")
    fd = aff4.FACTORY.Open(
        binaries[1].AFF4Path(self.client_id), token=self.token)
    self.assertEqual(fd.Read(1024), "this is foo")

  @parser_test_lib.WithParser("VAD", rekall_artifact_parser.RekallVADParser)
  def testDoesNotFetchDuplicates(self):
    process = "\\WINDOWS\\bar.exe"
    client_mock = ListVADBinariesActionMock([process, process])

    with test_lib.ConfigOverrider({"Rekall.enabled": True}):
      session_id = flow_test_lib.TestFlowHelper(
          memory.ListVADBinaries.__name__,
          client_mock,
          client_id=self.client_id,
          fetch_binaries=True,
          token=self.token)

    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    binaries = list(fd)

    self.assertLen(binaries, 1)
    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(
        binaries[0].AFF4Path(self.client_id), token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")

  @parser_test_lib.WithParser("VAD", rekall_artifact_parser.RekallVADParser)
  def testConditionsOutBinariesUsingRegex(self):
    process1_exe = "\\WINDOWS\\bar.exe"
    process2_exe = "\\WINDOWS\\foo.exe"

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])

    with test_lib.ConfigOverrider({"Rekall.enabled": True}):
      session_id = flow_test_lib.TestFlowHelper(
          memory.ListVADBinaries.__name__,
          client_mock,
          client_id=self.client_id,
          token=self.token,
          filename_regex=".*bar\\.exe$",
          fetch_binaries=True)

    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    binaries = list(fd)

    self.assertLen(binaries, 1)
    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(
        binaries[0].AFF4Path(self.client_id), token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")

  @parser_test_lib.WithParser("VAD", rekall_artifact_parser.RekallVADParser)
  def testIgnoresMissingFiles(self):
    process1_exe = "\\WINDOWS\\bar.exe"

    client_mock = ListVADBinariesActionMock([process1_exe])

    with test_lib.ConfigOverrider({"Rekall.enabled": True}):
      session_id = flow_test_lib.TestFlowHelper(
          memory.ListVADBinaries.__name__,
          client_mock,
          check_flow_errors=False,
          client_id=self.client_id,
          token=self.token,
          fetch_binaries=True)

    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    binaries = list(fd)

    self.assertLen(binaries, 1)
    self.assertEqual(binaries[0].pathspec.CollapsePath(), "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(
        binaries[0].AFF4Path(self.client_id), token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")


def RequireTestImage(f):
  """Decorator that skips tests if we don't have the memory image."""

  @functools.wraps(f)
  def Decorator(testinstance):
    image_path = os.path.join(testinstance.base_path, "win7_trial_64bit.raw")
    if os.access(image_path, os.R_OK):
      return f(testinstance)
    else:
      return testinstance.skipTest("No win7_trial_64bit.raw memory image,"
                                   "skipping test. Download it here: "
                                   "goo.gl/19AJGl and put it in test_data.")

  return Decorator


class TestAnalyzeClientMemory(rekall_test_lib.RekallTestBase):
  """Tests for AnalyzeClientMemory flow."""

  def testAnalyzeClientMemoryIsDisabledByDefault(self):
    with self.assertRaisesRegexp(RuntimeError, "Rekall flows are disabled"):
      flow.StartAFF4Flow(
          client_id=self.client_id,
          flow_name=memory.AnalyzeClientMemory.__name__,
          token=self.token)

  @RequireTestImage
  def testRekallModules(self):
    """Tests the end to end Rekall memory analysis."""
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdf_rekall_types.PluginRequest(
            plugin="pslist",
            args=dict(method=["PsActiveProcessHead", "CSRSS"])),
        rdf_rekall_types.PluginRequest(plugin="modules")
    ]
    session_id = self.LaunchRekallPlugin(request)

    # Get the result collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    # Ensure that the client_id is set on each message. This helps us demux
    # messages from different clients, when analyzing the collection from a
    # hunt.
    json_blobs = []
    for x in fd:
      self.assertEqual(x.client_urn, self.client_id)
      json_blobs.append(x.json_messages)

    json_blobs = "".join(json_blobs)

    for knownresult in ["DumpIt.exe", "DumpIt.sys"]:
      self.assertIn(knownresult, json_blobs)

  @RequireTestImage
  def testFileOutput(self):
    """Tests that a file can be written by a plugin and retrieved."""
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Run procdump to create one file.
        rdf_rekall_types.PluginRequest(
            plugin="procdump", args=dict(pids=[2860]))
    ]

    with test_lib.Instrument(transfer.MultiGetFileMixin,
                             "StoreStat") as storestat_instrument:
      self.LaunchRekallPlugin(request)
      # Expect one file to be downloaded.
      self.assertEqual(storestat_instrument.call_count, 1)

  @RequireTestImage
  def testParameters(self):
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdf_rekall_types.PluginRequest(
            plugin="pslist",
            args=dict(pids=[4, 2860], method="PsActiveProcessHead")),
    ]

    session_id = self.LaunchRekallPlugin(request)

    # Get the result collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    json_blobs = [x.json_messages for x in fd]
    json_blobs = "".join(json_blobs)

    for knownresult in ["System", "DumpIt.exe"]:
      self.assertIn(knownresult, json_blobs)

  @RequireTestImage
  def testDLLList(self):
    """Tests that we can run a simple DLLList Action."""
    request = rdf_rekall_types.RekallRequest()
    request.plugins = [
        # Only use these methods for listing processes.
        rdf_rekall_types.PluginRequest(
            plugin="dlllist",
            args=dict(proc_regex="dumpit", method="PsActiveProcessHead")),
    ]

    session_id = self.LaunchRekallPlugin(request)

    # Get the result collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    json_blobs = [x.json_messages for x in fd]
    json_blobs = "".join(json_blobs)

    for knownresult in ["DumpIt", "wow64win", "wow64", "wow64cpu", "ntdll"]:
      self.assertIn(knownresult, json_blobs)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
