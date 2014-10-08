#!/usr/bin/env python
"""Tests for export converters."""



import os
import socket

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import export
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib

from grr.proto import tests_pb2


class DummyRDFValue(rdfvalue.RDFString):
  pass


class DummyRDFValue2(rdfvalue.RDFString):
  pass


class DummyRDFValue3(rdfvalue.RDFString):
  pass


class DummyRDFValue4(rdfvalue.RDFString):
  pass


class DummyRDFValue5(rdfvalue.RDFString):
  pass


class DummyRDFValueConverter(export.ExportConverter):
  input_rdf_type = "DummyRDFValue"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [rdfvalue.RDFString(str(value))]


class DummyRDFValue3ConverterA(export.ExportConverter):
  input_rdf_type = "DummyRDFValue3"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [rdfvalue.DummyRDFValue(str(value) + "A")]


class DummyRDFValue3ConverterB(export.ExportConverter):
  input_rdf_type = "DummyRDFValue3"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    if not isinstance(value, DummyRDFValue3):
      raise ValueError("Called with the wrong type")
    return [rdfvalue.DummyRDFValue2(str(value) + "B")]


class DummyRDFValue4ToMetadataConverter(export.ExportConverter):
  input_rdf_type = "DummyRDFValue4"

  def Convert(self, metadata, value, token=None):
    _ = value
    _ = token
    return [metadata]


class DummyRDFValue5Converter(export.ExportConverter):
  input_rdf_type = "DummyRDFValue5"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    if not isinstance(value, DummyRDFValue5):
      raise ValueError("Called with the wrong type")
    return [rdfvalue.DummyRDFValue5(str(value) + "C")]


class ExportTest(test_lib.GRRBaseTest):
  """Tests export converters."""

  def testConverterIsCorrectlyFound(self):
    dummy_value = DummyRDFValue("result")
    result = list(export.ConvertValues(rdfvalue.ExportedMetadata(),
                                       [dummy_value]))
    self.assertEqual(len(result), 1)
    self.assertTrue(isinstance(result[0], rdfvalue.RDFString))
    self.assertEqual(result[0], "result")

  def testDoesNotRaiseWhenNoSpecificConverterIsDefined(self):
    dummy_value = DummyRDFValue2("some")
    export.ConvertValues(rdfvalue.ExportedMetadata(),
                         [dummy_value])

  def testDataAgnosticConverterIsUsedWhenNoSpecificConverterIsDefined(self):
    original_value = rdfvalue.DataAgnosticConverterTestValue()

    # There's no converter defined for DataAgnosticConverterTestValue, so
    # we expect DataAgnosticExportConverter to be used.
    converted_values = list(export.ConvertValues(rdfvalue.ExportedMetadata(),
                                                 [original_value]))
    self.assertEqual(len(converted_values), 1)
    converted_value = converted_values[0]

    self.assertEqual(converted_value.__class__.__name__,
                     "ExportedDataAgnosticConverterTestValue")

  def testConvertsSingleValueWithMultipleAssociatedConverters(self):
    dummy_value = DummyRDFValue3("some")
    result = list(export.ConvertValues(rdfvalue.ExportedMetadata(),
                                       [dummy_value]))
    self.assertEqual(len(result), 2)
    self.assertTrue((isinstance(result[0], rdfvalue.DummyRDFValue) and
                     isinstance(result[1], rdfvalue.DummyRDFValue2)) or
                    (isinstance(result[0], rdfvalue.DummyRDFValue2) and
                     isinstance(result[1], rdfvalue.DummyRDFValue)))
    self.assertTrue((result[0] == rdfvalue.DummyRDFValue("someA") and
                     result[1] == rdfvalue.DummyRDFValue2("someB")) or
                    (result[0] == rdfvalue.DummyRDFValue2("someB") and
                     result[1] == rdfvalue.DummyRDFValue("someA")))

  def testConvertsHuntCollectionWithValuesWithSingleConverter(self):
    fd = aff4.FACTORY.Create("aff4:/testcoll", "RDFValueCollection",
                             token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue("some"))
    msg.source = rdfvalue.ClientURN("C.0000000000000000")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue("some2"))
    msg.source = rdfvalue.ClientURN("C.0000000000000001")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    fd.Close()

    fd = aff4.FACTORY.Open("aff4:/testcoll", aff4_type="RDFValueCollection",
                           token=self.token)

    results = export.ConvertValues(rdfvalue.ExportedMetadata(), [fd],
                                   token=self.token)
    results = sorted(str(v) for v in results)

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0], "some")
    self.assertEqual(results[1], "some2")

  def testConvertsHuntCollectionWithValuesWithMultipleConverters(self):
    fd = aff4.FACTORY.Create("aff4:/testcoll", "RDFValueCollection",
                             token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue3("some1"))
    msg.source = rdfvalue.ClientURN("C.0000000000000000")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    msg = rdfvalue.GrrMessage(payload=DummyRDFValue3("some2"))
    msg.source = rdfvalue.ClientURN("C.0000000000000001")
    fd.Add(msg)
    test_lib.ClientFixture(msg.source, token=self.token)

    fd.Close()

    fd = aff4.FACTORY.Open("aff4:/testcoll", aff4_type="RDFValueCollection",
                           token=self.token)

    results = export.ConvertValues(rdfvalue.ExportedMetadata(), [fd],
                                   token=self.token)
    results = sorted(results, key=str)

    self.assertEqual(len(results), 4)
    self.assertEqual([str(v) for v in results
                      if isinstance(v, rdfvalue.DummyRDFValue)],
                     ["some1A", "some2A"])
    self.assertEqual([str(v) for v in results
                      if isinstance(v, rdfvalue.DummyRDFValue2)],
                     ["some1B", "some2B"])

  def testStatEntryToExportedFileConverterWithMissingAFF4File(self):
    stat = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"),
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].basename, "path")
    self.assertEqual(results[0].urn,
                     rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"))
    self.assertEqual(results[0].st_mode, 33184)
    self.assertEqual(results[0].st_ino, 1063090)
    self.assertEqual(results[0].st_atime, 1336469177)
    self.assertEqual(results[0].st_mtime, 1336129892)
    self.assertEqual(results[0].st_ctime, 1336129892)

    self.assertFalse(results[0].HasField("content"))
    self.assertFalse(results[0].HasField("content_sha256"))
    self.assertFalse(results[0].HasField("hash_md5"))
    self.assertFalse(results[0].HasField("hash_sha1"))
    self.assertFalse(results[0].HasField("hash_sha256"))

  def testStatEntryToExportedFileConverterWithFetchedAFF4File(self):
    client_ids = self.SetupClients(1)
    client_id = client_ids[0]

    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path="/Ext2IFS_1_10b.exe",
                    pathtype=rdfvalue.PathSpec.PathType.TSK)

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashBuffer")
    for _ in test_lib.TestFlowHelper(
        "GetFile", client_mock, token=self.token,
        client_id=client_id, pathspec=pathspec):
      pass

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)

    stat = fd.Get(fd.Schema.STAT)
    self.assertTrue(stat)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].basename, "Ext2IFS_1_10b.exe")
    self.assertEqual(results[0].urn, urn)

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)

    # Convert again, now specifying export_files_contents=True in options.
    converter = export.StatEntryToExportedFileConverter(
        options=rdfvalue.ExportOptions(
            export_files_contents=True))
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))
    self.assertTrue(results[0].content)
    self.assertEqual(
        results[0].content_sha256,
        "69264282ca1a3d4e7f9b1f43720f719a4ea47964f0bfd1b2ba88424f1c61395d")
    self.assertEqual("", results[0].metadata.annotations)

  def testStatEntryToExportedFileConverterWithHashedAFF4File(self):
    client_ids = self.SetupClients(1)
    client_id = client_ids[0]

    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path="/Ext2IFS_1_10b.exe",
                    pathtype=rdfvalue.PathSpec.PathType.TSK)
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id)

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashBuffer")
    for _ in test_lib.TestFlowHelper(
        "GetFile", client_mock, token=self.token,
        client_id=client_id, pathspec=pathspec):
      pass

    auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED
    flow.Events.PublishEvent(
        "FileStore.AddFileToStore",
        rdfvalue.GrrMessage(payload=urn, auth_state=auth_state),
        token=self.token)
    worker = test_lib.MockWorker(token=self.token)
    worker.Simulate()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    hash_value = fd.Get(fd.Schema.HASH)
    self.assertTrue(hash_value)

    converter = export.StatEntryToExportedFileConverter(
        options=rdfvalue.ExportOptions(export_files_hashes=True,
                                       annotations=["test1", "test2"]))
    results = list(converter.Convert(rdfvalue.ExportedMetadata(),
                                     rdfvalue.StatEntry(aff4path=urn,
                                                        pathspec=pathspec),
                                     token=self.token))

    self.assertEqual(results[0].hash_md5,
                     "bb0a15eefe63fd41f8dc9dee01c5cf9a")
    self.assertEqual(results[0].hash_sha1,
                     "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    self.assertEqual(
        results[0].hash_sha256,
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5")
    for result in results:
      self.assertItemsEqual(["test1", "test2"],
                            result.metadata.annotations.split(","))

  def testExportedFileConverterIgnoresRegistryKeys(self):
    stat = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdfvalue.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdfvalue.PathSpec.PathType.REGISTRY))

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))
    self.assertFalse(results)

  def testStatEntryToExportedRegistryKeyConverter(self):
    stat = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        registry_type=rdfvalue.StatEntry.RegistryType.REG_EXPAND_SZ,
        pathspec=rdfvalue.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdfvalue.PathSpec.PathType.REGISTRY),
        registry_data=rdfvalue.DataBlob(string="Sidebar.exe"))

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].urn, rdfvalue.RDFURN(
        "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].type,
                     rdfvalue.StatEntry.RegistryType.REG_EXPAND_SZ)
    self.assertEqual(results[0].data, "Sidebar.exe")

  def testRegistryKeyConverterIgnoresNonRegistryStatEntries(self):
    stat = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"),
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertFalse(results)

  def testRegistryKeyConverterWorksWithRegistryKeys(self):
    # Registry keys won't have registry_type and registry_data set.
    stat = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdfvalue.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdfvalue.PathSpec.PathType.REGISTRY))

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), stat,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].urn, rdfvalue.RDFURN(
        "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].data, "")
    self.assertEqual(results[0].type, 0)

  def testProcessToExportedProcessConverter(self):
    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6))

    converter = export.ProcessToExportedProcessConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), process,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].ppid, 1)
    self.assertEqual(results[0].cmdline, "cmd.exe")
    self.assertEqual(results[0].exe, "c:\\windows\\cmd.exe")
    self.assertEqual(results[0].ctime, long(1333718907.167083 * 1e6))

  def testProcessToExportedOpenFileConverter(self):
    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6),
        open_files=["/some/a", "/some/b"])

    converter = export.ProcessToExportedOpenFileConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), process,
                                     token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].path, "/some/a")
    self.assertEqual(results[1].pid, 2)
    self.assertEqual(results[1].path, "/some/b")

  def testProcessToExportedNetworkConnection(self):
    conn1 = rdfvalue.NetworkConnection(
        state=rdfvalue.NetworkConnection.State.LISTEN,
        type=rdfvalue.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdfvalue.NetworkEndpoint(
            ip="0.0.0.0",
            port=22),
        remote_address=rdfvalue.NetworkEndpoint(
            ip="0.0.0.0",
            port=0),
        pid=2136,
        ctime=0)
    conn2 = rdfvalue.NetworkConnection(
        state=rdfvalue.NetworkConnection.State.LISTEN,
        type=rdfvalue.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdfvalue.NetworkEndpoint(
            ip="192.168.1.1",
            port=31337),
        remote_address=rdfvalue.NetworkEndpoint(
            ip="1.2.3.4",
            port=6667),
        pid=1,
        ctime=0)

    process = rdfvalue.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6),
        connections=[conn1, conn2])

    converter = export.ProcessToExportedNetworkConnectionConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), process,
                                     token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].state, rdfvalue.NetworkConnection.State.LISTEN)
    self.assertEqual(results[0].type,
                     rdfvalue.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[0].local_address.ip, "0.0.0.0")
    self.assertEqual(results[0].local_address.port, 22)
    self.assertEqual(results[0].remote_address.ip, "0.0.0.0")
    self.assertEqual(results[0].remote_address.port, 0)
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 0)

    self.assertEqual(results[1].state, rdfvalue.NetworkConnection.State.LISTEN)
    self.assertEqual(results[1].type,
                     rdfvalue.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[1].local_address.ip, "192.168.1.1")
    self.assertEqual(results[1].local_address.port, 31337)
    self.assertEqual(results[1].remote_address.ip, "1.2.3.4")
    self.assertEqual(results[1].remote_address.port, 6667)
    self.assertEqual(results[1].pid, 1)
    self.assertEqual(results[1].ctime, 0)

  def testRDFURNConverterWithURNPointingToFile(self):
    urn = rdfvalue.RDFURN("aff4:/C.00000000000000/some/path")

    fd = aff4.FACTORY.Create(urn, "VFSFile", token=self.token)
    fd.Set(fd.Schema.STAT(rdfvalue.StatEntry(
        aff4path=urn,
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)))
    fd.Close()

    converter = export.RDFURNConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), urn,
                                     token=self.token))

    self.assertTrue(len(results))

    exported_files = [r for r in results
                      if r.__class__.__name__ == "ExportedFile"]
    self.assertEqual(len(exported_files), 1)
    exported_file = exported_files[0]

    self.assertTrue(exported_file)
    self.assertEqual(exported_file.urn, urn)

  def testClientSummaryToExportedNetworkInterfaceConverter(self):
    client_summary = rdfvalue.ClientSummary(
        interfaces=[rdfvalue.Interface(
            mac_address="123456",
            ifname="eth0",
            addresses=[
                rdfvalue.NetworkAddress(
                    address_type=rdfvalue.NetworkAddress.Family.INET,
                    packed_bytes=socket.inet_aton("127.0.0.1"),
                ),
                rdfvalue.NetworkAddress(
                    address_type=rdfvalue.NetworkAddress.Family.INET,
                    packed_bytes=socket.inet_aton("10.0.0.1"),
                    ),
                rdfvalue.NetworkAddress(
                    address_type=rdfvalue.NetworkAddress.Family.INET6,
                    packed_bytes=socket.inet_pton(socket.AF_INET6,
                                                  "2001:720:1500:1::a100"),
                    )
                ]
            )]
        )

    converter = export.ClientSummaryToExportedNetworkInterfaceConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(),
                                     client_summary,
                                     token=self.token))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].mac_address, "123456".encode("hex"))
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")

  def testInterfaceToExportedNetworkInterfaceConverter(self):
    interface = rdfvalue.Interface(
        mac_address="123456",
        ifname="eth0",
        addresses=[
            rdfvalue.NetworkAddress(
                address_type=rdfvalue.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_aton("127.0.0.1"),
            ),
            rdfvalue.NetworkAddress(
                address_type=rdfvalue.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_aton("10.0.0.1"),
                ),
            rdfvalue.NetworkAddress(
                address_type=rdfvalue.NetworkAddress.Family.INET6,
                packed_bytes=socket.inet_pton(socket.AF_INET6,
                                              "2001:720:1500:1::a100"),
                )
            ]
        )

    converter = export.InterfaceToExportedNetworkInterfaceConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(),
                                     interface,
                                     token=self.token))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].mac_address, "123456".encode("hex"))
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")

  def testGetMetadata(self):
    client_urn = rdfvalue.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(client_urn, token=self.token)
    metadata = export.GetMetadata(client_urn, token=self.token)
    self.assertEqual(metadata.os, u"Windows")
    self.assertEqual(metadata.labels, u"")

    # Now set CLIENT_INFO with labels
    client_info = rdfvalue.ClientInformation(client_name="grr",
                                             labels=["a", "b"])
    client = aff4.FACTORY.Open(client_urn, mode="rw", token=self.token)
    client.Set(client.Schema.CLIENT_INFO(client_info))
    client.Flush()
    metadata = export.GetMetadata(client_urn, token=self.token)
    self.assertEqual(metadata.os, u"Windows")
    self.assertEqual(metadata.labels, u"a,b")

  def testClientSummaryToExportedClientConverter(self):
    client_summary = rdfvalue.ClientSummary()
    metadata = rdfvalue.ExportedMetadata(hostname="ahostname")

    converter = export.ClientSummaryToExportedClientConverter()
    results = list(converter.Convert(metadata, client_summary,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].metadata.hostname, "ahostname")

  def testBufferReferenceToExportedMatchConverter(self):
    buffer_reference = rdfvalue.BufferReference(
        offset=42, length=43, data="somedata",
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS))
    metadata = rdfvalue.ExportedMetadata(client_urn="C.0000000000000001")

    converter = export.BufferReferenceToExportedMatchConverter()
    results = list(converter.Convert(metadata, buffer_reference,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].offset, 42)
    self.assertEqual(results[0].length, 43)
    self.assertEqual(results[0].data, "somedata")
    self.assertEqual(
        results[0].urn,
        rdfvalue.RDFURN("aff4:/C.0000000000000001/fs/os/some/path"))

  def testFileFinderResultExportConverter(self):
    pathspec = rdfvalue.PathSpec(path="/some/path",
                                 pathtype=rdfvalue.PathSpec.PathType.OS)

    match1 = rdfvalue.BufferReference(
        offset=42, length=43, data="somedata1", pathspec=pathspec)
    match2 = rdfvalue.BufferReference(
        offset=44, length=45, data="somedata2", pathspec=pathspec)
    stat_entry = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000001/fs/os/some/path"),
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    file_finder_result = rdfvalue.FileFinderResult(stat_entry=stat_entry,
                                                   matches=[match1, match2])
    metadata = rdfvalue.ExportedMetadata(client_urn="C.0000000000000001")

    converter = export.FileFinderResultConverter()
    results = list(converter.Convert(metadata, file_finder_result,
                                     token=self.token))

    # We expect 1 ExportedFile instance in the results
    exported_files = [result for result in results
                      if isinstance(result, rdfvalue.ExportedFile)]
    self.assertEqual(len(exported_files), 1)

    self.assertEqual(exported_files[0].basename, "path")
    self.assertEqual(exported_files[0].urn,
                     rdfvalue.RDFURN("aff4:/C.00000000000001/fs/os/some/path"))
    self.assertEqual(exported_files[0].st_mode, 33184)
    self.assertEqual(exported_files[0].st_ino, 1063090)
    self.assertEqual(exported_files[0].st_atime, 1336469177)
    self.assertEqual(exported_files[0].st_mtime, 1336129892)
    self.assertEqual(exported_files[0].st_ctime, 1336129892)

    self.assertFalse(exported_files[0].HasField("content"))
    self.assertFalse(exported_files[0].HasField("content_sha256"))
    self.assertFalse(exported_files[0].HasField("hash_md5"))
    self.assertFalse(exported_files[0].HasField("hash_sha1"))
    self.assertFalse(exported_files[0].HasField("hash_sha256"))

    # We expect 2 ExportedMatch instances in the results
    exported_matches = [result for result in results
                        if isinstance(result, rdfvalue.ExportedMatch)]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertEqual(len(exported_matches), 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, "somedata1")
    self.assertEqual(
        exported_matches[0].urn,
        rdfvalue.RDFURN("aff4:/C.0000000000000001/fs/os/some/path"))

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, "somedata2")
    self.assertEqual(
        exported_matches[1].urn,
        rdfvalue.RDFURN("aff4:/C.0000000000000001/fs/os/some/path"))

  def testFileFinderResultExportConverterConvertsHashes(self):
    pathspec = rdfvalue.PathSpec(path="/some/path",
                                 pathtype=rdfvalue.PathSpec.PathType.OS)

    stat_entry = rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000001/fs/os/some/path"),
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)
    hash_entry = rdfvalue.Hash(
        sha256=("0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578"
                "e4f06017acdb5").decode("hex"),
        sha1="7dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"),
        md5="bb0a15eefe63fd41f8dc9dee01c5cf9a".decode("hex"),
        pecoff_md5="7dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"),
        pecoff_sha1="7dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"))

    file_finder_result = rdfvalue.FileFinderResult(stat_entry=stat_entry,
                                                   hash_entry=hash_entry)
    metadata = rdfvalue.ExportedMetadata(client_urn="C.0000000000000001")

    converter = export.FileFinderResultConverter()
    results = list(converter.Convert(metadata, file_finder_result,
                                     token=self.token))

    # We expect 1 ExportedFile instance in the results
    exported_files = [result for result in results
                      if isinstance(result, rdfvalue.ExportedFile)]
    self.assertEqual(len(exported_files), 1)

    self.assertEqual(exported_files[0].basename, "path")
    self.assertEqual(exported_files[0].hash_sha256,
                     "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4"
                     "f06017acdb5")
    self.assertEqual(exported_files[0].hash_sha1,
                     "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    self.assertEqual(exported_files[0].hash_md5,
                     "bb0a15eefe63fd41f8dc9dee01c5cf9a")
    self.assertEqual(exported_files[0].pecoff_hash_md5,
                     "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    self.assertEqual(exported_files[0].pecoff_hash_sha1,
                     "7dd6bee591dfcb6d75eb705405302c3eab65e21a")

  def testRDFURNConverterWithURNPointingToCollection(self):
    urn = rdfvalue.RDFURN("aff4:/C.00000000000000/some/collection")

    fd = aff4.FACTORY.Create(urn, "RDFValueCollection", token=self.token)
    fd.Add(rdfvalue.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/some/path"),
        pathspec=rdfvalue.PathSpec(path="/some/path",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892))
    fd.Close()

    converter = export.RDFURNConverter()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), urn,
                                     token=self.token))

    self.assertTrue(len(results))

    exported_files = [r for r in results
                      if r.__class__.__name__ == "ExportedFile"]
    self.assertEqual(len(exported_files), 1)
    exported_file = exported_files[0]

    self.assertTrue(exported_file)
    self.assertEqual(exported_file.urn,
                     rdfvalue.RDFURN("aff4:/C.00000000000000/some/path"))

  def testGrrMessageConverter(self):
    payload = DummyRDFValue4(
        "some", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg = rdfvalue.GrrMessage(payload=payload)
    msg.source = rdfvalue.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg.source, token=self.token)

    metadata = rdfvalue.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000000/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(2):
      results = list(converter.Convert(metadata, msg, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].original_timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(2))
    self.assertEqual(results[0].source_urn, "aff4:/hunts/W:000000/Results")

  def testGrrMessageConverterWithOneMissingClient(self):
    payload1 = DummyRDFValue4(
        "some", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg1 = rdfvalue.GrrMessage(payload=payload1)
    msg1.source = rdfvalue.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg1.source, token=self.token)

    payload2 = DummyRDFValue4(
        "some2", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg2 = rdfvalue.GrrMessage(payload=payload2)
    msg2.source = rdfvalue.ClientURN("C.0000000000000001")

    metadata1 = rdfvalue.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000000/Results"))
    metadata2 = rdfvalue.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000001/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(converter.BatchConvert(
          [(metadata1, msg1), (metadata2, msg2)], token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].original_timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(3))
    self.assertEqual(results[0].source_urn, "aff4:/hunts/W:000000/Results")

  def testGrrMessageConverterMultipleTypes(self):
    payload1 = DummyRDFValue3(
        "some", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg1 = rdfvalue.GrrMessage(payload=payload1)
    msg1.source = rdfvalue.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg1.source, token=self.token)

    payload2 = DummyRDFValue5(
        "some2", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg2 = rdfvalue.GrrMessage(payload=payload2)
    msg2.source = rdfvalue.ClientURN("C.0000000000000000")

    metadata1 = rdfvalue.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000000/Results"))
    metadata2 = rdfvalue.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/W:000001/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(converter.BatchConvert(
          [(metadata1, msg1), (metadata2, msg2)], token=self.token))

    self.assertEqual(len(results), 3)
    # RDFValue3 gets converted to RDFValue2 and RDFValue, RDFValue5 stays at 5.
    self.assertItemsEqual(["DummyRDFValue2", "DummyRDFValue", "DummyRDFValue5"],
                          [x.__class__.__name__ for x in results])

  def testDNSClientConfigurationToExportedDNSClientConfiguration(self):
    dns_servers = ["192.168.1.1", "8.8.8.8"]
    dns_suffixes = ["internal.company.com", "company.com"]
    config = rdfvalue.DNSClientConfiguration(
        dns_server=dns_servers,
        dns_suffix=dns_suffixes)

    converter = export.DNSClientConfigurationToExportedDNSClientConfiguration()
    results = list(converter.Convert(rdfvalue.ExportedMetadata(), config,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].dns_servers, " ".join(dns_servers))
    self.assertEqual(results[0].dns_suffixes, " ".join(dns_suffixes))


class DataAgnosticConverterTestValue(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.DataAgnosticConverterTestValue


class DataAgnosticConverterTestValueWithMetadata(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.DataAgnosticConverterTestValueWithMetadata


class DataAgnosticExportConverterTest(test_lib.GRRBaseTest):
  """Tests for DataAgnosticExportConverter."""

  def ConvertOriginalValue(self, original_value):
    converted_values = list(export.DataAgnosticExportConverter().Convert(
        rdfvalue.ExportedMetadata(source_urn=rdfvalue.RDFURN("aff4:/foo")),
        original_value))
    self.assertEqual(len(converted_values), 1)
    return converted_values[0]

  def testAddsMetadataAndIgnoresRepeatedAndMessagesFields(self):
    original_value = rdfvalue.DataAgnosticConverterTestValue()
    converted_value = self.ConvertOriginalValue(original_value)

    # No 'metadata' field in the original value.
    self.assertListEqual(sorted([t.name for t in original_value.type_infos]),
                         sorted(["string_value",
                                 "int_value",
                                 "repeated_string_value",
                                 "message_value",
                                 "enum_value",
                                 "urn_value",
                                 "datetime_value"]))
    # But there's one in the converted value.
    self.assertListEqual(sorted([t.name for t in converted_value.type_infos]),
                         sorted(["metadata",
                                 "string_value",
                                 "int_value",
                                 "enum_value",
                                 "urn_value",
                                 "datetime_value"]))

    # Metadata value is correctly initialized from user-supplied metadata.
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))

  def testIgnoresPredefinedMetadataField(self):
    original_value = rdfvalue.DataAgnosticConverterTestValueWithMetadata(
        metadata=42, value="value")
    converted_value = self.ConvertOriginalValue(original_value)

    self.assertListEqual(sorted([t.name for t in converted_value.type_infos]),
                         ["metadata", "value"])
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))
    self.assertEqual(converted_value.value, "value")

  def testProcessesPrimitiveTypesCorrectly(self):
    original_value = rdfvalue.DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        enum_value=rdfvalue.DataAgnosticConverterTestValue.EnumOption.OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))
    converted_value = self.ConvertOriginalValue(original_value)

    self.assertEqual(converted_value.string_value.__class__,
                     original_value.string_value.__class__)
    self.assertEqual(converted_value.string_value, "string value")

    self.assertEqual(converted_value.int_value.__class__,
                     original_value.int_value.__class__)
    self.assertEqual(converted_value.int_value, 42)

    self.assertEqual(converted_value.enum_value.__class__,
                     original_value.enum_value.__class__)
    self.assertEqual(converted_value.enum_value,
                     converted_value.EnumOption.OPTION_2)

    self.assertTrue(isinstance(converted_value.urn_value, rdfvalue.RDFURN))
    self.assertEqual(converted_value.urn_value, rdfvalue.RDFURN("aff4:/bar"))

    self.assertTrue(isinstance(converted_value.datetime_value,
                               rdfvalue.RDFDatetime))
    self.assertEqual(converted_value.datetime_value,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))

  def testConvertedValuesCanBeSerializedAndDeserialized(self):
    original_value = rdfvalue.DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        enum_value=rdfvalue.DataAgnosticConverterTestValue.EnumOption.OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))
    converted_value = self.ConvertOriginalValue(original_value)

    serialized = converted_value.SerializeToString()
    unserialized_converted_value = converted_value.__class__(serialized)

    self.assertEqual(converted_value, unserialized_converted_value)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
