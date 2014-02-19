#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Tests for memory related flows."""

import os
import socket
import threading

import logging

from grr.client import vfs

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.rdfvalues import crypto
from grr.parsers import volatility_artifact_parser_test


class DummyLoadMemoryDriverFlow(flow.GRRFlow):
  args_type = rdfvalue.LoadMemoryDriverArgs

  @flow.StateHandler()
  def Start(self):
    self.SendReply(rdfvalue.MemoryInformation(
        device=rdfvalue.PathSpec(
            path=os.path.join(config_lib.CONFIG["Test.data_dir"],
                              "auth.log"),
            pathtype=rdfvalue.PathSpec.PathType.OS)))


class TestMemoryScanner(test_lib.FlowTestsBaseclass):
  """Tests the MemoryScanner flow."""

  def setUp(self):
    super(TestMemoryScanner, self).setUp()

    self.output_path = "analysis/memory_scanner"

    self.key = rdfvalue.AES128Key("1a5eafcc77d428863d4c2441ea26e5a5")
    self.iv = rdfvalue.AES128Key("2241b14c64874b1898dad4de7173d8c0")

    self.memory_file = os.path.join(config_lib.CONFIG["Test.data_dir"],
                                    "auth.log")
    with open(self.memory_file, "r") as f:
      self.memory_dump = f.read()
    self.assertTrue(self.memory_dump)

    self.client_mock = test_lib.ActionMock("TransferBuffer", "HashBuffer",
                                           "StatFile", "CopyPathToFile",
                                           "SendFile", "DeleteGRRTempFiles",
                                           "Find", "Grep")

    self.old_driver_flow = flow.GRRFlow.classes["LoadMemoryDriver"]
    flow.GRRFlow.classes["LoadMemoryDriver"] = DummyLoadMemoryDriverFlow

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.MEMORY] = test_lib.ClientTestDataVFSFixture

  def tearDown(self):
    super(TestMemoryScanner, self).tearDown()

    flow.GRRFlow.classes["LoadMemoryDriver"] = self.old_driver_flow

  def testCallWithDefaultArgumentsDoesNothing(self):
    for _ in test_lib.TestFlowHelper(
        "MemoryScanner", test_lib.ActionMock(), client_id=self.client_id,
        token=self.token):
      pass

  def RunWithDownload(self, dump_option, filters=None):
    download_action = rdfvalue.MemoryScannerDownloadAction(
        dump_option=dump_option)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id, flow_name="MemoryScanner",
        filters=filters or [],
        action=rdfvalue.MemoryScannerAction(
            action_type=rdfvalue.MemoryScannerAction.Action.DOWNLOAD,
            download=download_action
            ), token=self.token, output=self.output_path)

    for _ in test_lib.TestFlowHelper(
        flow_urn, self.client_mock, client_id=self.client_id, token=self.token):
      pass

    return aff4.FACTORY.Open(flow_urn, token=self.token)

  def testMemoryImageLocalCopyDownload(self):
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryScannerWithLocalCopyDumpOption(
            gzip=False))

    flow_obj = self.RunWithDownload(dump_option)
    self.assertTrue(flow_obj.state.memory_src_path is not None)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def testMemoryImageLocalCopyDownloadWithOffsetAndLength(self):
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryScannerWithLocalCopyDumpOption(
            offset=10, length=42, gzip=False))

    flow_obj = self.RunWithDownload(dump_option)
    self.assertTrue(flow_obj.state.memory_src_path is not None)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump[10:52])

  def testMemoryImageWithoutLocalCopyDownload(self):
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITHOUT_LOCAL_COPY)

    flow_obj = self.RunWithDownload(dump_option)
    self.assertEqual(flow_obj.state.memory_src_path.path, self.memory_file)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def RunWithSendToSocket(self, dump_option, filters=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((socket.gethostname(), 0))
    port = sock.getsockname()[1]

    send_to_socket_action = rdfvalue.MemoryScannerSendToSocketAction(
        host=socket.gethostname(),
        port=port,
        key=self.key,
        iv=self.iv,
        dump_option=dump_option)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id, flow_name="MemoryScanner",
        filters=filters or [],
        action=rdfvalue.MemoryScannerAction(
            action_type=rdfvalue.MemoryScannerAction.Action.SEND_TO_SOCKET,
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
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryScannerWithLocalCopyDumpOption(
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
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryScannerWithLocalCopyDumpOption(
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
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITHOUT_LOCAL_COPY)
    (flow_urn, encrypted, decrypted) = self.RunWithSendToSocket(dump_option)

    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    # There was a local file, so dest_path should not be empty
    self.assertTrue(flow_obj.state.memory_src_path is not None)

    # Data should be encrypted, so they're not equal
    self.assertNotEqual(encrypted, self.memory_dump)
    # Decrypted data should be equal to the memory dump
    self.assertEqual(decrypted, self.memory_dump)

  def RunWithNoAction(self, filters=None):
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id, flow_name="MemoryScanner",
        filters=filters or [],
        action=rdfvalue.MemoryScannerAction(
            action_type=rdfvalue.MemoryScannerAction.Action.NONE),
        token=self.token, output=self.output_path)

    for _ in test_lib.TestFlowHelper(
        flow_urn, self.client_mock, client_id=self.client_id, token=self.token):
      pass

    return aff4.FACTORY.Open(flow_urn, token=self.token)

  def testMemoryImageLiteralMatchFilterWithNoAction(self):
    literal_filter = rdfvalue.MemoryScannerFilter(
        filter_type=rdfvalue.MemoryScannerFilter.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchFilter(
            mode=rdfvalue.FileFinderContentsLiteralMatchFilter.Mode.ALL_HITS,
            literal="session opened for user dearjohn"))

    self.RunWithNoAction(filters=[literal_filter])

    output = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                               aff4_type="RDFValueCollection",
                               token=self.token)
    self.assertEqual(len(output), 1)
    self.assertEqual(output[0].offset, 350)
    self.assertEqual(output[0].length, 52)
    self.assertEqual(output[0].data, "session): session opened for user "
                     "dearjohn by (uid=0")

  def testMemoryImageRegexMatchFilterWithNoAction(self):
    regex_filter = rdfvalue.MemoryScannerFilter(
        filter_type=rdfvalue.MemoryScannerFilter.Type.REGEX_MATCH,
        regex_match=rdfvalue.FileFinderContentsRegexMatchFilter(
            mode=rdfvalue.FileFinderContentsLiteralMatchFilter.Mode.ALL_HITS,
            regex="session opened for user .*?john"))

    self.RunWithNoAction(filters=[regex_filter])

    output = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                               aff4_type="RDFValueCollection",
                               token=self.token)
    self.assertEqual(len(output), 1)
    self.assertEqual(output[0].offset, 350)
    self.assertEqual(output[0].length, 52)
    self.assertEqual(output[0].data, "session): session opened for user "
                     "dearjohn by (uid=0")

  def testMemoryImageLiteralMatchFilterWithDownloadAction(self):
    literal_filter = rdfvalue.MemoryScannerFilter(
        filter_type=rdfvalue.MemoryScannerFilter.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchFilter(
            mode=rdfvalue.FileFinderContentsLiteralMatchFilter.Mode.ALL_HITS,
            literal="session opened for user dearjohn"))
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryScannerWithLocalCopyDumpOption(
            gzip=False))
    flow_obj = self.RunWithDownload(dump_option, filters=[literal_filter])

    # Check that matches are in the collection
    output = aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                               aff4_type="RDFValueCollection",
                               token=self.token)
    # First item of the collection is the BufferReference, second is the
    # path of the downloaded
    self.assertEqual(len(output), 1)
    self.assertEqual(output[0].offset, 350)
    self.assertEqual(output[0].length, 52)
    self.assertEqual(output[0].data, "session): session opened for user "
                     "dearjohn by (uid=0")

    self.assertTrue(flow_obj.state.memory_src_path is not None)
    self.assertEqual(
        flow_obj.state.downloaded_file,
        self.client_id.Add("fs/os").Add(flow_obj.state.memory_src_path.path))

    fd = aff4.FACTORY.Open(flow_obj.state.downloaded_file, token=self.token)
    self.assertEqual(fd.Read(1024 * 1024), self.memory_dump)

  def testDoesNothingWhenFilterDoesNotMatch(self):
    literal_filter = rdfvalue.MemoryScannerFilter(
        filter_type=rdfvalue.MemoryScannerFilter.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchFilter(
            mode=rdfvalue.FileFinderContentsLiteralMatchFilter.Mode.ALL_HITS,
            literal="session opened for user foobar"))
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryScannerWithLocalCopyDumpOption(
            gzip=False))
    flow_obj = self.RunWithDownload(dump_option, filters=[literal_filter])

    # Check that there are no matches
    with self.assertRaises(aff4.InstantiationError):
      aff4.FACTORY.Open(self.client_id.Add(self.output_path),
                        aff4_type="RDFValueCollection",
                        token=self.token)

    # Assert nothing got downloaded
    self.assertTrue("dest_path" not in flow_obj.state)
    self.assertTrue("downloaded_file" not in flow_obj.state)

  def testMemoryImageLiteralMatchFilterWithSendToSocketAction(self):
    literal_filter = rdfvalue.MemoryScannerFilter(
        filter_type=rdfvalue.MemoryScannerFilter.Type.LITERAL_MATCH,
        literal_match=rdfvalue.FileFinderContentsLiteralMatchFilter(
            mode=rdfvalue.FileFinderContentsLiteralMatchFilter.Mode.ALL_HITS,
            literal="session opened for user dearjohn"))
    dump_option = rdfvalue.MemoryScannerDumpOption(
        option_type=rdfvalue.MemoryScannerDumpOption.Option.WITH_LOCAL_COPY,
        with_local_copy=rdfvalue.MemoryScannerWithLocalCopyDumpOption(
            gzip=False))
    flow_urn, encrypted, decrypted = self.RunWithSendToSocket(
        dump_option, filters=[literal_filter])

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

  def __init__(self, process_list):
    super(ListVADBinariesActionMock, self).__init__(
        "TransferBuffer", "StatFile", "Find", "HashBuffer", "HashFile",
        "ListDirectory")
    self.process_list = process_list

  def VolatilityAction(self, _):
    vad_parser_test = volatility_artifact_parser_test.VolatilityVADParserTest
    return [vad_parser_test.GenerateVADVolatilityResult(self.process_list)]


class ListVADBinariesTest(test_lib.FlowTestsBaseclass):
  """Tests the Volatility-powered "get processes binaries" flow."""

  def setUp(self):
    super(ListVADBinariesTest, self).setUp()

    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.ClientRegistryVFSFixture

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
    process1_exe = "\\WINDOWS\\bar.exe"
    process2_exe = "\\WINDOWS\\foo.exe"

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
    binaries = sorted(fd, key=lambda x: x.CollapsePath())
    self.assertListEqual(binaries, [
        rdfvalue.PathSpec(path="C:" + process1_exe,
                          pathtype=rdfvalue.PathSpec.PathType.OS),
        rdfvalue.PathSpec(path="C:" + process2_exe,
                          pathtype=rdfvalue.PathSpec.PathType.OS)])

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
    process_exe = "\\WINDOWS\\bar.exe"
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
    self.assertEqual(binaries[0].pathspec.CollapsePath(),
                     "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")

  def testFiltersOutBinariesUsingRegex(self):
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
    process2_exe = "\\WINDOWS\\missing.exe"

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
    self.assertEqual(binaries[0].pathspec.CollapsePath(),
                     "/C:/WINDOWS/bar.exe")
    fd = aff4.FACTORY.Open(binaries[0].aff4path, token=self.token)
    self.assertEqual(fd.Read(1024), "just bar")
