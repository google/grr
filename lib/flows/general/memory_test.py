#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for memory related flows."""

import copy
import json
import os
import socket
import threading

from grr.client import vfs
from grr.client.client_actions import grr_rekall_test

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.rdfvalues import crypto


class DummyLoadMemoryDriverFlow(flow.GRRFlow):
  args_type = rdfvalue.LoadMemoryDriverArgs

  @flow.StateHandler()
  def Start(self):
    self.SendReply(rdfvalue.MemoryInformation(
        device=rdfvalue.PathSpec(
            path=os.path.join(config_lib.CONFIG["Test.data_dir"], "auth.log"),
            pathtype=rdfvalue.PathSpec.PathType.OS),
        runs=[rdfvalue.BufferReference(length=638976, offset=5),
              rdfvalue.BufferReference(length=145184, offset=643074)]))


class DummyDiskVolumeInfo(flow.GRRFlow):
  args_type = rdfvalue.DiskVolumeInfoArgs

  @flow.StateHandler()
  def Start(self):
    if "/opt" in self.args.path_list[0]:
      mnt = rdfvalue.UnixVolume(mount_point="/opt")
      self.SendReply(rdfvalue.Volume(unix=mnt, bytes_per_sector=4096,
                                     sectors_per_allocation_unit=1,
                                     actual_available_allocation_units=10,
                                     total_allocation_units=100))
    else:
      mnt = rdfvalue.UnixVolume(mount_point="/var")
      self.SendReply(rdfvalue.Volume(unix=mnt, bytes_per_sector=1,
                                     sectors_per_allocation_unit=1,
                                     actual_available_allocation_units=784165,
                                     total_allocation_units=78416500))


class MemoryTest(test_lib.FlowTestsBaseclass):
  pass


class TestMemoryCollector(MemoryTest):
  """Tests the MemoryCollector flow."""

  def setUp(self):
    super(TestMemoryCollector, self).setUp()

    self.output_path = "analysis/memory_scanner"

    self.key = rdfvalue.AES128Key("1a5eafcc77d428863d4c2441ea26e5a5")
    self.iv = rdfvalue.AES128Key("2241b14c64874b1898dad4de7173d8c0")

    self.memory_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                    "auth.log")
    with open(self.memory_file, "r") as f:
      self.memory_dump = f.read()
    self.assertTrue(self.memory_dump)

    self.client_mock = action_mocks.ActionMock("TransferBuffer", "HashBuffer",
                                               "StatFile", "CopyPathToFile",
                                               "SendFile", "DeleteGRRTempFiles",
                                               "GetConfiguration", "Find",
                                               "Grep")

    self.old_driver_flow = flow.GRRFlow.classes["LoadMemoryDriver"]
    flow.GRRFlow.classes["LoadMemoryDriver"] = DummyLoadMemoryDriverFlow
    self.old_diskvolume_flow = flow.GRRFlow.classes["DiskVolumeInfo"]
    flow.GRRFlow.classes["DiskVolumeInfo"] = DummyDiskVolumeInfo

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.MEMORY] = test_lib.FakeTestDataVFSHandler

  def tearDown(self):
    super(TestMemoryCollector, self).tearDown()
    flow.GRRFlow.classes["LoadMemoryDriver"] = self.old_driver_flow
    flow.GRRFlow.classes["DiskVolumeInfo"] = self.old_diskvolume_flow

  def testCallWithDefaultArgumentsDoesNothing(self):
    for _ in test_lib.TestFlowHelper(
        "MemoryCollector", action_mocks.ActionMock(), client_id=self.client_id,
        token=self.token):
      pass

  def RunWithDownload(self, dump_option, conditions=None):
    download_action = rdfvalue.MemoryCollectorDownloadAction(
        dump_option=dump_option)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id, flow_name="MemoryCollector",
        conditions=conditions or [],
        action=rdfvalue.MemoryCollectorAction(
            action_type=rdfvalue.MemoryCollectorAction.Action.DOWNLOAD,
            download=download_action
            ), token=self.token, output=self.output_path)

    for _ in test_lib.TestFlowHelper(
        flow_urn, self.client_mock,
        client_id=self.client_id,
        token=self.token):
      pass

    return aff4.FACTORY.Open(flow_urn, token=self.token)

  def testMemoryImageLocalCopyDownload(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            gzip=False, check_disk_free_space=False))

    flow_obj = self.RunWithDownload(dump_option)
    self.assertTrue(flow_obj.state.memory_src_path is not None)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def testMemoryImageLocalCopyDiskCheck(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            gzip=False))

    flow_obj = self.RunWithDownload(dump_option)
    self.assertTrue(flow_obj.state.memory_src_path is not None)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def testMemoryImageLocalCopyNoSpace(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            gzip=False, destdir="/opt/tmp/testing"))

    self.assertRaises(RuntimeError, self.RunWithDownload, dump_option)

  def testMemoryImageLocalCopyDownloadWithOffsetAndLength(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            offset=10, length=42, gzip=False))

    flow_obj = self.RunWithDownload(dump_option)
    self.assertTrue(flow_obj.state.memory_src_path is not None)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump[10:52])

  def testMemoryImageWithoutLocalCopyDownload(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=
        rdfvalue.MemoryCollectorDumpOption.Option.WITHOUT_LOCAL_COPY)

    flow_obj = self.RunWithDownload(dump_option)
    self.assertEqual(flow_obj.state.memory_src_path.path, self.memory_file)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def RunWithSendToSocket(self, dump_option, conditions=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((socket.gethostname(), 0))
    port = sock.getsockname()[1]

    send_to_socket_action = rdfvalue.MemoryCollectorSendToSocketAction(
        host=socket.gethostname(),
        port=port,
        key=self.key,
        iv=self.iv,
        dump_option=dump_option)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id, flow_name="MemoryCollector",
        conditions=conditions or [],
        action=rdfvalue.MemoryCollectorAction(
            action_type=rdfvalue.MemoryCollectorAction.Action.SEND_TO_SOCKET,
            send_to_socket=send_to_socket_action),
        token=self.token, output=self.output_path)

    socket_data = []
    def ReadFromSocket():
      sock.listen(1)
      client_socket, _ = sock.accept()
      while 1:
        data = client_socket.recv(1024)
        if not data: break
        socket_data.append(data)
      client_socket.close()
      sock.close()
    thread = threading.Thread(target=ReadFromSocket)
    thread.daemon = True
    thread.start()

    for _ in test_lib.TestFlowHelper(
        flow_urn, self.client_mock, client_id=self.client_id, token=self.token):
      pass
    thread.join()

    encrypted_data = "".join(socket_data)
    # Data should be encrypted, so they're not equal
    self.assertNotEqual(encrypted_data, self.memory_dump)

    cipher = crypto.AES128CBCCipher(key=self.key, iv=self.iv,
                                    mode=crypto.AES128CBCCipher.OP_DECRYPT)
    decrypted_data = cipher.Update(encrypted_data) + cipher.Final()

    return flow_urn, encrypted_data, decrypted_data

  def testMemoryImageLocalCopySendToSocket(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            gzip=False))
    flow_urn, encrypted, decrypted = self.RunWithSendToSocket(dump_option)

    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    # There was a local file, so dest_path should not be empty
    self.assertTrue(flow_obj.state.memory_src_path is not None)

    # Data should be encrypted, so they're not equal
    self.assertNotEqual(encrypted, self.memory_dump)
    # Decrypted data should be equal to the memory dump
    self.assertEqual(decrypted, self.memory_dump)

  def testMemoryImageLocalCopySendToSocketWithOffsetAndLength(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            offset=10, length=42, gzip=False))
    flow_urn, encrypted, decrypted = self.RunWithSendToSocket(dump_option)

    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    # There was a local file, so dest_path should not be empty
    self.assertTrue(flow_obj.state.memory_src_path is not None)

    # Data should be encrypted, so they're not equal
    self.assertNotEqual(encrypted, self.memory_dump)
    # Decrypted data should be equal to the memory dump
    self.assertEqual(decrypted, self.memory_dump[10:52])

  def testMemoryImageWithoutLocalCopySendToSocket(self):
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=
        rdfvalue.MemoryCollectorDumpOption.Option.WITHOUT_LOCAL_COPY)
    (flow_urn, encrypted, decrypted) = self.RunWithSendToSocket(dump_option)

    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    # There was a local file, so dest_path should not be empty
    self.assertTrue(flow_obj.state.memory_src_path is not None)

    # Data should be encrypted, so they're not equal
    self.assertNotEqual(encrypted, self.memory_dump)
    # Decrypted data should be equal to the memory dump
    self.assertEqual(decrypted, self.memory_dump)

  def RunWithNoAction(self, conditions=None):
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id, flow_name="MemoryCollector",
        conditions=conditions or [],
        action=rdfvalue.MemoryCollectorAction(
            action_type=rdfvalue.MemoryCollectorAction.Action.NONE),
        token=self.token, output=self.output_path)

    for _ in test_lib.TestFlowHelper(
        flow_urn, self.client_mock, client_id=self.client_id, token=self.token):
      pass

    return aff4.FACTORY.Open(flow_urn, token=self.token)

  def testMemoryImageLiteralMatchConditionWithNoAction(self):
    literal_condition = rdfvalue.MemoryCollectorCondition(
        condition_type=rdfvalue.MemoryCollectorCondition.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchCondition(
            mode=rdfvalue.FileFinderContentsLiteralMatchCondition.Mode.ALL_HITS,
            literal="session opened for user dearjohn"))

    self.RunWithNoAction(conditions=[literal_condition])

    output = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                               aff4_type="RDFValueCollection",
                               token=self.token)
    self.assertEqual(len(output), 1)
    self.assertEqual(output[0].offset, 350)
    self.assertEqual(output[0].length, 52)
    self.assertEqual(output[0].data, "session): session opened for user "
                     "dearjohn by (uid=0")

  def testMemoryImageRegexMatchConditionWithNoAction(self):
    regex_condition = rdfvalue.MemoryCollectorCondition(
        condition_type=rdfvalue.MemoryCollectorCondition.Type.REGEX_MATCH,
        regex_match=rdfvalue.FileFinderContentsRegexMatchCondition(
            mode=rdfvalue.FileFinderContentsLiteralMatchCondition.Mode.ALL_HITS,
            regex="session opened for user .*?john"))

    self.RunWithNoAction(conditions=[regex_condition])

    output = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                               aff4_type="RDFValueCollection",
                               token=self.token)
    self.assertEqual(len(output), 1)
    self.assertEqual(output[0].offset, 350)
    self.assertEqual(output[0].length, 52)
    self.assertEqual(output[0].data, "session): session opened for user "
                     "dearjohn by (uid=0")

  def testMemoryImageLiteralMatchConditionWithDownloadAction(self):
    literal_condition = rdfvalue.MemoryCollectorCondition(
        condition_type=rdfvalue.MemoryCollectorCondition.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchCondition(
            mode=rdfvalue.FileFinderContentsLiteralMatchCondition.Mode.ALL_HITS,
            literal="session opened for user dearjohn"))
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            gzip=False))
    flow_obj = self.RunWithDownload(dump_option, conditions=[literal_condition])

    # Check that matches are in the collection
    output = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                               aff4_type="RDFValueCollection",
                               token=self.token)
    # First item of the collection is the BufferReference, second is the
    # path of the downloaded
    self.assertEqual(len(output), 2)
    self.assertEqual(output[0].offset, 350)
    self.assertEqual(output[0].length, 52)
    self.assertEqual(output[0].data, "session): session opened for user "
                     "dearjohn by (uid=0")
    self.assertTrue(isinstance(output[1], rdfvalue.StatEntry))

    self.assertTrue(flow_obj.state.memory_src_path is not None)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def testDoesNothingWhenConditionDoesNotMatch(self):
    literal_condition = rdfvalue.MemoryCollectorCondition(
        condition_type=rdfvalue.MemoryCollectorCondition.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchCondition(
            mode=rdfvalue.FileFinderContentsLiteralMatchCondition.Mode.ALL_HITS,
            literal="session opened for user foobar"))
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            gzip=False))
    flow_obj = self.RunWithDownload(dump_option, conditions=[literal_condition])

    # Check that there are no matches
    with self.assertRaises(aff4.InstantiationError):
      aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                        aff4_type="RDFValueCollection",
                        token=self.token)

    # Assert nothing got downloaded
    self.assertTrue("dest_path" not in flow_obj.state)
    self.assertTrue("downloaded_file" not in flow_obj.state)

  def testMemoryImageLiteralMatchConditionWithSendToSocketAction(self):
    literal_condition = rdfvalue.MemoryCollectorCondition(
        condition_type=rdfvalue.MemoryCollectorCondition.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchCondition(
            mode=rdfvalue.FileFinderContentsLiteralMatchCondition.Mode.ALL_HITS,
            literal="session opened for user dearjohn"))
    dump_option = rdfvalue.MemoryCollectorDumpOption(
        option_type=rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryCollectorWithLocalCopyDumpOption(
            gzip=False))
    flow_urn, encrypted, decrypted = self.RunWithSendToSocket(
        dump_option, conditions=[literal_condition])

    # Check that matches are in the collection
    output = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                               aff4_type="RDFValueCollection",
                               token=self.token)
    self.assertEqual(len(output), 1)
    self.assertEqual(output[0].offset, 350)
    self.assertEqual(output[0].length, 52)
    self.assertEqual(output[0].data, "session): session opened for user "
                     "dearjohn by (uid=0")

    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    # There was a local file, so dest_path should not be empty
    self.assertTrue(flow_obj.state.memory_src_path is not None)

    # Data should be encrypted, so they're not equal
    self.assertNotEqual(encrypted, self.memory_dump)
    # Decrypted data should be equal to the memory dump
    self.assertEqual(decrypted, self.memory_dump)


class TestMemoryAnalysis(MemoryTest, grr_rekall_test.RekallTestSuite):
  """Tests the memory analysis flows."""

  def testLoadDriverWindows(self):
    """Tests the memory driver deployment flow."""
    self.CreateSignedDriver()
    self.CreateClient()

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("LoadMemoryDriver",
                                     action_mocks.MemoryClientMock(),
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

  def testScanMemory(self):
    # Use a file in place of a memory image for simplicity
    image_path = os.path.join(self.base_path, "numbers.txt")

    self.CreateClient()
    self.CreateSignedDriver()

    class ClientMock(action_mocks.MemoryClientMock):
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


class ListVADBinariesActionMock(action_mocks.ActionMock):
  """Client with real file actions and mocked-out RekallAction."""

  def __init__(self, process_list=None):
    super(ListVADBinariesActionMock, self).__init__(
        "TransferBuffer", "StatFile", "Find", "HashBuffer", "FingerprintFile",
        "ListDirectory")
    self.process_list = process_list or []

  def RekallAction(self, _):
    ps_list_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                "rekall_vad_result.dat")
    response = rdfvalue.RekallResponse(
        json_messages=open(ps_list_file, "rb").read(),
        plugin="pslist")

    # If we are given process names here we need to craft a Rekall result
    # containing them. This is so they point to valid files in the fixture.
    if self.process_list:
      json_data = json.loads(response.json_messages)
      template = json_data[11]
      if template[1]["filename"] != ur"\Windows\System32\ntdll.dll":
        raise RuntimeError("Test data invalid.")

      json_data = []
      for process in self.process_list:
        new_entry = copy.deepcopy(template)
        new_entry[1]["filename"] = process
        json_data.append(new_entry)
      response.json_messages = json.dumps(json_data)

    return [response, rdfvalue.Iterator(state="FINISHED")]


class ListVADBinariesTest(MemoryTest):
  """Tests the Rekall-powered "get processes binaries" flow."""

  def setUp(self):
    super(ListVADBinariesTest, self).setUp()

    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.FakeRegistryVFSHandler

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = fd.Schema.USER()
    users.Append(rdfvalue.User(
        username="LocalService", domain="testing-PC",
        homedir=r"C:\Users\localservice", sid="S-1-5-20"))
    fd.Set(users)
    fd.Close()

    self.old_driver_flow = flow.GRRFlow.classes["LoadMemoryDriver"]
    flow.GRRFlow.classes["LoadMemoryDriver"] = DummyLoadMemoryDriverFlow

  def tearDown(self):
    super(ListVADBinariesTest, self).tearDown()

    flow.GRRFlow.classes["LoadMemoryDriver"] = self.old_driver_flow

  def testListsBinaries(self):
    client_mock = ListVADBinariesActionMock()
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
    paths = sorted([x.CollapsePath() for x in fd])
    self.assertIn(u"C:\\Windows\\System32\\wintrust.dll", paths)
    self.assertIn(u"C:\\Program Files\\Internet Explorer\\ieproxy.dll", paths)

  def testFetchesAndStoresBinary(self):
    process1_exe = "\\WINDOWS\\bar.exe"
    process2_exe = "\\WINDOWS\\foo.exe"

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

    self.assertEqual(binaries[0].pathspec.CollapsePath(),
                     "/C:/WINDOWS/bar.exe")
    self.assertEqual(binaries[1].pathspec.CollapsePath(),
                     "/C:/WINDOWS/foo.exe")

    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")
    fd = aff4.FACTORY.Open(binaries[1].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "this is foo")

  def testDoesNotFetchDuplicates(self):
    process = "\\WINDOWS\\bar.exe"
    client_mock = ListVADBinariesActionMock([process, process])
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
    self.assertEqual(binaries[0].pathspec.CollapsePath(),
                     "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")

  def testConditionsOutBinariesUsingRegex(self):
    process1_exe = "\\WINDOWS\\bar.exe"
    process2_exe = "\\WINDOWS\\foo.exe"

    client_mock = ListVADBinariesActionMock([process1_exe, process2_exe])
    output_path = "analysis/ListVADBinariesTest1"

    for _ in test_lib.TestFlowHelper(
        "ListVADBinaries",
        client_mock,
        client_id=self.client_id,
        token=self.token,
        output=output_path,
        filename_regex=".*bar\\.exe$",
        fetch_binaries=True):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    binaries = list(fd)

    self.assertEqual(len(binaries), 1)
    self.assertEqual(binaries[0].pathspec.CollapsePath(),
                     "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")

  def testIgnoresMissingFiles(self):
    process1_exe = "\\WINDOWS\\bar.exe"

    client_mock = ListVADBinariesActionMock([process1_exe])
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
    self.assertEqual(binaries[0].pathspec.CollapsePath(),
                     "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = MemoryTest


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
