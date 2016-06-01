#!/usr/bin/env python
"""Tests for export converters."""



import json
import os
import socket

from grr.client.components.rekall_support import grr_rekall
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import export
from grr.lib import flags
from grr.lib import flow
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import filestore
from grr.lib.checks import checks
from grr.lib.flows.general import collectors
# This test calls flows from these files. pylint: disable=unused-import
from grr.lib.flows.general import file_finder
from grr.lib.flows.general import transfer
# pylint: enable=unused-import
from grr.lib.hunts import results as hunts_results
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
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
    return [DummyRDFValue(str(value) + "A")]


class DummyRDFValue3ConverterB(export.ExportConverter):
  input_rdf_type = "DummyRDFValue3"

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    if not isinstance(value, DummyRDFValue3):
      raise ValueError("Called with the wrong type")
    return [DummyRDFValue2(str(value) + "B")]


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
    return [DummyRDFValue5(str(value) + "C")]


class ExportTest(test_lib.GRRBaseTest):
  """Tests export converters."""

  def testConverterIsCorrectlyFound(self):
    dummy_value = DummyRDFValue("result")
    result = list(export.ConvertValues(export.ExportedMetadata(), [dummy_value
                                                                  ]))
    self.assertEqual(len(result), 1)
    self.assertTrue(isinstance(result[0], rdfvalue.RDFString))
    self.assertEqual(result[0], "result")

  def testDoesNotRaiseWhenNoSpecificConverterIsDefined(self):
    dummy_value = DummyRDFValue2("some")
    export.ConvertValues(export.ExportedMetadata(), [dummy_value])

  def testDataAgnosticConverterIsUsedWhenNoSpecificConverterIsDefined(self):
    original_value = DataAgnosticConverterTestValue()

    # There's no converter defined for DataAgnosticConverterTestValue, so
    # we expect DataAgnosticExportConverter to be used.
    converted_values = list(export.ConvertValues(export.ExportedMetadata(),
                                                 [original_value]))
    self.assertEqual(len(converted_values), 1)
    converted_value = converted_values[0]

    self.assertEqual(converted_value.__class__.__name__,
                     "AutoExportedDataAgnosticConverterTestValue")

  def testConvertsSingleValueWithMultipleAssociatedConverters(self):
    dummy_value = DummyRDFValue3("some")
    result = list(export.ConvertValues(export.ExportedMetadata(), [dummy_value
                                                                  ]))
    self.assertEqual(len(result), 2)
    self.assertTrue((isinstance(result[0], DummyRDFValue) and
                     isinstance(result[1], DummyRDFValue2)) or
                    (isinstance(result[0], DummyRDFValue2) and
                     isinstance(result[1], DummyRDFValue)))
    self.assertTrue((result[0] == DummyRDFValue("someA") and
                     result[1] == DummyRDFValue2("someB")) or
                    (result[0] == DummyRDFValue2("someB") and
                     result[1] == DummyRDFValue("someA")))

  def _ConvertsCollectionWithValuesWithSingleConverter(self, coll_type):
    fd = aff4.FACTORY.Create("aff4:/testcoll", coll_type, token=self.token)
    src1 = rdf_client.ClientURN("C.0000000000000000")
    fd.AddAsMessage(DummyRDFValue("some"), src1)
    test_lib.ClientFixture(src1, token=self.token)

    src2 = rdf_client.ClientURN("C.0000000000000001")
    fd.AddAsMessage(DummyRDFValue("some2"), src2)
    test_lib.ClientFixture(src2, token=self.token)

    fd.Close()

    fd = aff4.FACTORY.Open("aff4:/testcoll",
                           aff4_type=coll_type,
                           token=self.token)

    results = export.ConvertValues(export.ExportedMetadata(), [fd],
                                   token=self.token)
    results = sorted(str(v) for v in results)

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0], "some")
    self.assertEqual(results[1], "some2")

  def testConvertsHuntResultCollectionWithValuesWithSingleConverter(self):
    self._ConvertsCollectionWithValuesWithSingleConverter(
        hunts_results.HuntResultCollection)

  def testConvertsRDFValueCollectionWithValuesWithSingleConverter(self):
    self._ConvertsCollectionWithValuesWithSingleConverter(
        collects.RDFValueCollection)

  def _ConvertsCollectionWithMultipleConverters(self, coll_type):
    fd = aff4.FACTORY.Create("aff4:/testcoll", coll_type, token=self.token)

    src1 = rdf_client.ClientURN("C.0000000000000000")
    fd.AddAsMessage(DummyRDFValue3("some1"), src1)
    test_lib.ClientFixture(src1, token=self.token)

    src2 = rdf_client.ClientURN("C.0000000000000001")
    fd.AddAsMessage(DummyRDFValue3("some2"), src2)
    test_lib.ClientFixture(src2, token=self.token)

    fd.Close()

    fd = aff4.FACTORY.Open("aff4:/testcoll",
                           aff4_type=coll_type,
                           token=self.token)

    results = export.ConvertValues(export.ExportedMetadata(), [fd],
                                   token=self.token)
    results = sorted(results, key=str)

    self.assertEqual(len(results), 4)
    self.assertEqual([str(v) for v in results if isinstance(v, DummyRDFValue)],
                     ["some1A", "some2A"])
    self.assertEqual([str(v) for v in results if isinstance(v, DummyRDFValue2)],
                     ["some1B", "some2B"])

  def testConvertsRDFValueCollectionWithValuesWithMultipleConverters(self):
    self._ConvertsCollectionWithMultipleConverters(collects.RDFValueCollection)

  def testConvertsHuntResultCollectionWithValuesWithMultipleConverters(self):
    self._ConvertsCollectionWithMultipleConverters(
        hunts_results.HuntResultCollection)

  def testStatEntryToExportedFileConverterWithMissingAFF4File(self):
    stat = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"),
        pathspec=rdf_paths.PathSpec(path="/some/path",
                                    pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), stat, token=self.token))

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

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path="/Ext2IFS_1_10b.exe",
                    pathtype=rdf_paths.PathSpec.PathType.TSK)

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashBuffer")
    for _ in test_lib.TestFlowHelper("GetFile",
                                     client_mock,
                                     token=self.token,
                                     client_id=client_id,
                                     pathspec=pathspec):
      pass

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)

    stat = fd.Get(fd.Schema.STAT)
    self.assertTrue(stat)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), stat, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].basename, "Ext2IFS_1_10b.exe")
    self.assertEqual(results[0].urn, urn)

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)

    # Convert again, now specifying export_files_contents=True in options.
    converter = export.StatEntryToExportedFileConverter(
        options=export.ExportOptions(export_files_contents=True))
    results = list(converter.Convert(export.ExportedMetadata(
    ), stat, token=self.token))
    self.assertTrue(results[0].content)
    self.assertEqual(
        results[0].content_sha256,
        "69264282ca1a3d4e7f9b1f43720f719a4ea47964f0bfd1b2ba88424f1c61395d")
    self.assertEqual("", results[0].metadata.annotations)

  def testStatEntryToExportedFileConverterWithHashedAFF4File(self):
    filestore.FileStoreInit().Run()
    client_ids = self.SetupClients(1)
    client_id = client_ids[0]

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path="/Ext2IFS_1_10b.exe",
                    pathtype=rdf_paths.PathSpec.PathType.TSK)
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id)

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashBuffer")
    for _ in test_lib.TestFlowHelper("GetFile",
                                     client_mock,
                                     token=self.token,
                                     client_id=client_id,
                                     pathspec=pathspec):
      pass

    auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
    flow.Events.PublishEvent(
        "FileStore.AddFileToStore",
        rdf_flows.GrrMessage(payload=urn, auth_state=auth_state),
        token=self.token)
    worker = test_lib.MockWorker(token=self.token)
    worker.Simulate()

    fd = aff4.FACTORY.Open(urn, token=self.token)
    hash_value = fd.Get(fd.Schema.HASH)
    self.assertTrue(hash_value)

    converter = export.StatEntryToExportedFileConverter(
        options=export.ExportOptions(export_files_hashes=True))
    results = list(converter.Convert(export.ExportedMetadata(),
                                     rdf_client.StatEntry(aff4path=urn,
                                                          pathspec=pathspec),
                                     token=self.token))

    self.assertEqual(results[0].hash_md5, "bb0a15eefe63fd41f8dc9dee01c5cf9a")
    self.assertEqual(results[0].hash_sha1,
                     "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
    self.assertEqual(
        results[0].hash_sha256,
        "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5")

  def testExportedFileConverterIgnoresRegistryKeys(self):
    stat = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), stat, token=self.token))
    self.assertFalse(results)

  def testStatEntryToExportedRegistryKeyConverter(self):
    stat = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        registry_type=rdf_client.StatEntry.RegistryType.REG_EXPAND_SZ,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY),
        registry_data=rdf_protodict.DataBlob(string="Sidebar.exe"))

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), stat, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].urn, rdfvalue.RDFURN(
        "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].type,
                     rdf_client.StatEntry.RegistryType.REG_EXPAND_SZ)
    self.assertEqual(results[0].data, "Sidebar.exe")

  def testRegistryKeyConverterIgnoresNonRegistryStatEntries(self):
    stat = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"),
        pathspec=rdf_paths.PathSpec(path="/some/path",
                                    pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), stat, token=self.token))

    self.assertFalse(results)

  def testRegistryKeyConverterWorksWithRegistryKeys(self):
    # Registry keys won't have registry_type and registry_data set.
    stat = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
            "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), stat, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].urn, rdfvalue.RDFURN(
        "aff4:/C.0000000000000000/registry/HKEY_USERS/S-1-5-20/Software/"
        "Microsoft/Windows/CurrentVersion/Run/Sidebar"))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].data, "")
    self.assertEqual(results[0].type, 0)

  def testProcessToExportedProcessConverter(self):
    process = rdf_client.Process(pid=2,
                                 ppid=1,
                                 cmdline=["cmd.exe"],
                                 exe="c:\\windows\\cmd.exe",
                                 ctime=long(1333718907.167083 * 1e6))

    converter = export.ProcessToExportedProcessConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), process, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].ppid, 1)
    self.assertEqual(results[0].cmdline, "cmd.exe")
    self.assertEqual(results[0].exe, "c:\\windows\\cmd.exe")
    self.assertEqual(results[0].ctime, long(1333718907.167083 * 1e6))

  def testProcessToExportedOpenFileConverter(self):
    process = rdf_client.Process(pid=2,
                                 ppid=1,
                                 cmdline=["cmd.exe"],
                                 exe="c:\\windows\\cmd.exe",
                                 ctime=long(1333718907.167083 * 1e6),
                                 open_files=["/some/a", "/some/b"])

    converter = export.ProcessToExportedOpenFileConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), process, token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].path, "/some/a")
    self.assertEqual(results[1].pid, 2)
    self.assertEqual(results[1].path, "/some/b")

  def testProcessToExportedNetworkConnection(self):
    conn1 = rdf_client.NetworkConnection(
        state=rdf_client.NetworkConnection.State.LISTEN,
        type=rdf_client.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client.NetworkEndpoint(ip="0.0.0.0",
                                                 port=22),
        remote_address=rdf_client.NetworkEndpoint(ip="0.0.0.0",
                                                  port=0),
        pid=2136,
        ctime=0)
    conn2 = rdf_client.NetworkConnection(
        state=rdf_client.NetworkConnection.State.LISTEN,
        type=rdf_client.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client.NetworkEndpoint(ip="192.168.1.1",
                                                 port=31337),
        remote_address=rdf_client.NetworkEndpoint(ip="1.2.3.4",
                                                  port=6667),
        pid=1,
        ctime=0)

    process = rdf_client.Process(pid=2,
                                 ppid=1,
                                 cmdline=["cmd.exe"],
                                 exe="c:\\windows\\cmd.exe",
                                 ctime=long(1333718907.167083 * 1e6),
                                 connections=[conn1, conn2])

    converter = export.ProcessToExportedNetworkConnectionConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), process, token=self.token))

    self.assertEqual(len(results), 2)
    self.assertEqual(results[0].state,
                     rdf_client.NetworkConnection.State.LISTEN)
    self.assertEqual(results[0].type,
                     rdf_client.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[0].local_address.ip, "0.0.0.0")
    self.assertEqual(results[0].local_address.port, 22)
    self.assertEqual(results[0].remote_address.ip, "0.0.0.0")
    self.assertEqual(results[0].remote_address.port, 0)
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 0)

    self.assertEqual(results[1].state,
                     rdf_client.NetworkConnection.State.LISTEN)
    self.assertEqual(results[1].type,
                     rdf_client.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[1].local_address.ip, "192.168.1.1")
    self.assertEqual(results[1].local_address.port, 31337)
    self.assertEqual(results[1].remote_address.ip, "1.2.3.4")
    self.assertEqual(results[1].remote_address.port, 6667)
    self.assertEqual(results[1].pid, 1)
    self.assertEqual(results[1].ctime, 0)

  def testRDFURNConverterWithURNPointingToFile(self):
    urn = rdfvalue.RDFURN("aff4:/C.00000000000000/some/path")

    fd = aff4.FACTORY.Create(urn, aff4_grr.VFSFile, token=self.token)
    fd.Set(fd.Schema.STAT(rdf_client.StatEntry(
        aff4path=urn,
        pathspec=rdf_paths.PathSpec(path="/some/path",
                                    pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)))
    fd.Close()

    converter = export.RDFURNConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), urn, token=self.token))

    self.assertTrue(len(results))

    exported_files = [r for r in results
                      if r.__class__.__name__ == "ExportedFile"]
    self.assertEqual(len(exported_files), 1)
    exported_file = exported_files[0]

    self.assertTrue(exported_file)
    self.assertEqual(exported_file.urn, urn)

  def testClientSummaryToExportedNetworkInterfaceConverter(self):
    client_summary = rdf_client.ClientSummary(interfaces=[rdf_client.Interface(
        mac_address="123456",
        ifname="eth0",
        addresses=[
            rdf_client.NetworkAddress(
                address_type=rdf_client.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "127.0.0.1"),),
            rdf_client.NetworkAddress(
                address_type=rdf_client.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "10.0.0.1"),),
            rdf_client.NetworkAddress(
                address_type=rdf_client.NetworkAddress.Family.INET6,
                packed_bytes=socket.inet_pton(socket.AF_INET6,
                                              "2001:720:1500:1::a100"),)
        ])])

    converter = export.ClientSummaryToExportedNetworkInterfaceConverter()
    results = list(converter.Convert(export.ExportedMetadata(),
                                     client_summary,
                                     token=self.token))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].mac_address, "123456".encode("hex"))
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")

  def testInterfaceToExportedNetworkInterfaceConverter(self):
    interface = rdf_client.Interface(
        mac_address="123456",
        ifname="eth0",
        addresses=[
            rdf_client.NetworkAddress(
                address_type=rdf_client.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "127.0.0.1"),),
            rdf_client.NetworkAddress(
                address_type=rdf_client.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "10.0.0.1"),),
            rdf_client.NetworkAddress(
                address_type=rdf_client.NetworkAddress.Family.INET6,
                packed_bytes=socket.inet_pton(socket.AF_INET6,
                                              "2001:720:1500:1::a100"),)
        ])

    converter = export.InterfaceToExportedNetworkInterfaceConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), interface, token=self.token))
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].mac_address, "123456".encode("hex"))
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")

  def testCheckResultConverter(self):
    checkresults = [
        checks.CheckResult(check_id="check-id-1"),
        checks.CheckResult(
            check_id="check-id-2",
            anomaly=[
                rdf_anomaly.Anomaly(
                    type="PARSER_ANOMALY",
                    symptom="something was wrong on the system"),
                rdf_anomaly.Anomaly(
                    type="MANUAL_ANOMALY",
                    symptom="manually found wrong stuff",
                    anomaly_reference_id=["id1", "id2"],
                    finding=["file has bad permissions: /tmp/test"]),
            ]),
    ]
    metadata = export.ExportedMetadata()

    results = list(export.ConvertValues(
        metadata, checkresults, token=self.token))
    self.assertEqual(len(results), 3)
    self.assertEqual(results[0].check_id, checkresults[0].check_id)
    self.assertFalse(results[0].HasField("anomaly"))
    self.assertEqual(results[1].check_id, checkresults[1].check_id)
    self.assertEqual(results[1].anomaly.type, checkresults[1].anomaly[0].type)
    self.assertEqual(results[1].anomaly.symptom,
                     checkresults[1].anomaly[0].symptom)
    self.assertEqual(results[2].check_id, checkresults[1].check_id)
    self.assertEqual(results[2].anomaly.type, checkresults[1].anomaly[1].type)
    self.assertEqual(results[2].anomaly.symptom,
                     checkresults[1].anomaly[1].symptom)
    self.assertEqual(results[2].anomaly.anomaly_reference_id,
                     "\n".join(checkresults[1].anomaly[1].anomaly_reference_id))
    self.assertEqual(results[2].anomaly.finding,
                     checkresults[1].anomaly[1].finding[0])

  def testGetMetadata(self):
    client_urn = rdf_client.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(client_urn, token=self.token)
    client = aff4.FACTORY.Open(client_urn, mode="rw", token=self.token)
    client.SetLabels("client-label-24")
    client.Close()

    metadata = export.GetMetadata(client_urn, token=self.token)
    self.assertEqual(metadata.os, u"Windows")
    self.assertEqual(metadata.labels, u"client-label-24")

    client = aff4.FACTORY.Open(client_urn, mode="rw", token=self.token)
    client.SetLabels("a", "b")
    client.Flush()
    metadata = export.GetMetadata(client_urn, token=self.token)
    self.assertEqual(metadata.os, u"Windows")
    self.assertEqual(metadata.labels, u"a,b")

  def testGetMetadataMissingKB(self):
    client_urn = rdf_client.ClientURN("C.0000000000000000")
    newclient = aff4.FACTORY.Create(client_urn,
                                    aff4_grr.VFSGRRClient,
                                    token=self.token,
                                    mode="rw")
    self.assertFalse(newclient.Get(newclient.Schema.KNOWLEDGE_BASE))
    newclient.Flush()

    # Expect empty usernames field due to no knowledge base.
    metadata = export.GetMetadata(client_urn, token=self.token)
    self.assertFalse(metadata.usernames)

  def testClientSummaryToExportedClientConverter(self):
    client_summary = rdf_client.ClientSummary()
    metadata = export.ExportedMetadata(hostname="ahostname")

    converter = export.ClientSummaryToExportedClientConverter()
    results = list(converter.Convert(
        metadata, client_summary, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].metadata.hostname, "ahostname")

  def testBufferReferenceToExportedMatchConverter(self):
    buffer_reference = rdf_client.BufferReference(
        offset=42,
        length=43,
        data="somedata",
        pathspec=rdf_paths.PathSpec(path="/some/path",
                                    pathtype=rdf_paths.PathSpec.PathType.OS))
    metadata = export.ExportedMetadata(client_urn="C.0000000000000001")

    converter = export.BufferReferenceToExportedMatchConverter()
    results = list(converter.Convert(
        metadata, buffer_reference, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].offset, 42)
    self.assertEqual(results[0].length, 43)
    self.assertEqual(results[0].data, "somedata")
    self.assertEqual(
        results[0].urn,
        rdfvalue.RDFURN("aff4:/C.0000000000000001/fs/os/some/path"))

  def testFileFinderResultExportConverter(self):
    pathspec = rdf_paths.PathSpec(path="/some/path",
                                  pathtype=rdf_paths.PathSpec.PathType.OS)

    match1 = rdf_client.BufferReference(offset=42,
                                        length=43,
                                        data="somedata1",
                                        pathspec=pathspec)
    match2 = rdf_client.BufferReference(offset=44,
                                        length=45,
                                        data="somedata2",
                                        pathspec=pathspec)
    stat_entry = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000001/fs/os/some/path"),
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    file_finder_result = file_finder.FileFinderResult(stat_entry=stat_entry,
                                                      matches=[match1, match2])
    metadata = export.ExportedMetadata(client_urn="C.0000000000000001")

    converter = export.FileFinderResultConverter()
    results = list(converter.Convert(metadata,
                                     file_finder_result,
                                     token=self.token))

    # We expect 1 ExportedFile instance in the results
    exported_files = [result for result in results
                      if isinstance(result, export.ExportedFile)]
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
                        if isinstance(result, export.ExportedMatch)]
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

    # Also test registry entries.
    data = rdf_protodict.DataBlob()
    data.SetValue("testdata")
    stat_entry = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN(
            "aff4:/C.00000000000001/registry/HKEY_USERS/S-1-1-1-1/Software"),
        registry_type="REG_SZ",
        registry_data=data,
        pathspec=rdf_paths.PathSpec(pathtype="REGISTRY"))
    file_finder_result = file_finder.FileFinderResult(stat_entry=stat_entry)
    metadata = export.ExportedMetadata(client_urn="C.0000000000000001")
    converter = export.FileFinderResultConverter()
    results = list(converter.Convert(metadata,
                                     file_finder_result,
                                     token=self.token))

    self.assertEqual(len(results), 1)
    self.assertIsInstance(results[0], export.ExportedRegistryKey)
    result = results[0]

    self.assertEqual(result.data, "testdata")
    self.assertEqual(
        result.urn,
        "aff4:/C.00000000000001/registry/HKEY_USERS/S-1-1-1-1/Software")

  def testFileFinderResultExportConverterConvertsHashes(self):
    pathspec = rdf_paths.PathSpec(path="/some/path",
                                  pathtype=rdf_paths.PathSpec.PathType.OS)
    pathspec2 = rdf_paths.PathSpec(path="/some/path2",
                                   pathtype=rdf_paths.PathSpec.PathType.OS)

    stat_entry = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000001/fs/os/some/path"),
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)
    hash_entry = rdf_crypto.Hash(
        sha256=("0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578"
                "e4f06017acdb5").decode("hex"),
        sha1="7dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"),
        md5="bb0a15eefe63fd41f8dc9dee01c5cf9a".decode("hex"),
        pecoff_md5="7dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"),
        pecoff_sha1="7dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"))

    stat_entry2 = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000001/fs/os/some/path2"),
        pathspec=pathspec2,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)
    hash_entry2 = rdf_crypto.Hash(
        sha256=("9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578"
                "e4f06017acdb5").decode("hex"),
        sha1="6dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"),
        md5="8b0a15eefe63fd41f8dc9dee01c5cf9a".decode("hex"),
        pecoff_md5="1dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"),
        pecoff_sha1="1dd6bee591dfcb6d75eb705405302c3eab65e21a".decode("hex"))

    file_finder_result = file_finder.FileFinderResult(stat_entry=stat_entry,
                                                      hash_entry=hash_entry)
    file_finder_result2 = file_finder.FileFinderResult(stat_entry=stat_entry2,
                                                       hash_entry=hash_entry2)

    metadata = export.ExportedMetadata(client_urn="C.0000000000000001")

    converter = export.FileFinderResultConverter()
    results = list(converter.BatchConvert([(metadata, file_finder_result), (
        metadata, file_finder_result2)],
                                          token=self.token))

    exported_files = [result for result in results
                      if isinstance(result, export.ExportedFile)]
    self.assertEqual(len(exported_files), 2)
    self.assertItemsEqual([x.basename for x in exported_files],
                          ["path", "path2"])

    for export_result in exported_files:
      if export_result.basename == "path":
        self.assertEqual(export_result.hash_sha256,
                         "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4"
                         "f06017acdb5")
        self.assertEqual(export_result.hash_sha1,
                         "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.hash_md5,
                         "bb0a15eefe63fd41f8dc9dee01c5cf9a")
        self.assertEqual(export_result.pecoff_hash_md5,
                         "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.pecoff_hash_sha1,
                         "7dd6bee591dfcb6d75eb705405302c3eab65e21a")
      elif export_result.basename == "path2":
        self.assertEqual(export_result.basename, "path2")
        self.assertEqual(export_result.hash_sha256,
                         "9e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4"
                         "f06017acdb5")
        self.assertEqual(export_result.hash_sha1,
                         "6dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.hash_md5,
                         "8b0a15eefe63fd41f8dc9dee01c5cf9a")
        self.assertEqual(export_result.pecoff_hash_md5,
                         "1dd6bee591dfcb6d75eb705405302c3eab65e21a")
        self.assertEqual(export_result.pecoff_hash_sha1,
                         "1dd6bee591dfcb6d75eb705405302c3eab65e21a")

  def testRDFURNConverterWithURNPointingToCollection(self):
    urn = rdfvalue.RDFURN("aff4:/C.00000000000000/some/collection")

    fd = aff4.FACTORY.Create(urn, collects.RDFValueCollection, token=self.token)
    fd.Add(rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/some/path"),
        pathspec=rdf_paths.PathSpec(path="/some/path",
                                    pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892))
    fd.Close()

    converter = export.RDFURNConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), urn, token=self.token))

    self.assertTrue(len(results))

    exported_files = [r for r in results
                      if r.__class__.__name__ == "ExportedFile"]
    self.assertEqual(len(exported_files), 1)
    exported_file = exported_files[0]

    self.assertTrue(exported_file)
    self.assertEqual(exported_file.urn,
                     rdfvalue.RDFURN("aff4:/C.00000000000000/some/path"))

  def testRDFBytesConverter(self):
    data = rdfvalue.RDFBytes("foobar")

    converter = export.RDFBytesToExportedBytesConverter()
    results = list(converter.Convert(export.ExportedMetadata(
    ), data, token=self.token))

    self.assertTrue(len(results))

    exported_bytes = [r for r in results
                      if r.__class__.__name__ == "ExportedBytes"]
    self.assertEqual(len(exported_bytes), 1)

    self.assertEqual(exported_bytes[0].data, data)
    self.assertEqual(exported_bytes[0].length, 6)

  def testGrrMessageConverter(self):
    payload = DummyRDFValue4("some",
                             age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg = rdf_flows.GrrMessage(payload=payload)
    msg.source = rdf_client.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg.source, token=self.token)

    metadata = export.ExportedMetadata(source_urn=rdfvalue.RDFURN(
        "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(2):
      results = list(converter.Convert(metadata, msg, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].original_timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(2))
    self.assertEqual(results[0].source_urn,
                     "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results")

  def testGrrMessageConverterWithOneMissingClient(self):
    payload1 = DummyRDFValue4(
        "some", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg1 = rdf_flows.GrrMessage(payload=payload1)
    msg1.source = rdf_client.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg1.source, token=self.token)

    payload2 = DummyRDFValue4(
        "some2", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg2 = rdf_flows.GrrMessage(payload=payload2)
    msg2.source = rdf_client.ClientURN("C.0000000000000001")

    metadata1 = export.ExportedMetadata(source_urn=rdfvalue.RDFURN(
        "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results"))
    metadata2 = export.ExportedMetadata(source_urn=rdfvalue.RDFURN(
        "aff4:/hunts/" + str(queues.HUNTS) + ":000001/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(converter.BatchConvert([(metadata1, msg1), (metadata2, msg2
                                                                )],
                                            token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].original_timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(3))
    self.assertEqual(results[0].source_urn,
                     "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results")

  def testGrrMessageConverterMultipleTypes(self):
    payload1 = DummyRDFValue3(
        "some", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg1 = rdf_flows.GrrMessage(payload=payload1)
    msg1.source = rdf_client.ClientURN("C.0000000000000000")
    test_lib.ClientFixture(msg1.source, token=self.token)

    payload2 = DummyRDFValue5(
        "some2", age=rdfvalue.RDFDatetime().FromSecondsFromEpoch(1))
    msg2 = rdf_flows.GrrMessage(payload=payload2)
    msg2.source = rdf_client.ClientURN("C.0000000000000000")

    metadata1 = export.ExportedMetadata(source_urn=rdfvalue.RDFURN(
        "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results"))
    metadata2 = export.ExportedMetadata(source_urn=rdfvalue.RDFURN(
        "aff4:/hunts/" + str(queues.HUNTS) + ":000001/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(converter.BatchConvert([(metadata1, msg1), (metadata2, msg2
                                                                )],
                                            token=self.token))

    self.assertEqual(len(results), 3)
    # RDFValue3 gets converted to RDFValue2 and RDFValue, RDFValue5 stays at 5.
    self.assertItemsEqual(["DummyRDFValue2", "DummyRDFValue", "DummyRDFValue5"],
                          [x.__class__.__name__ for x in results])

  def testDNSClientConfigurationToExportedDNSClientConfiguration(self):
    dns_servers = ["192.168.1.1", "8.8.8.8"]
    dns_suffixes = ["internal.company.com", "company.com"]
    config = rdf_client.DNSClientConfiguration(dns_server=dns_servers,
                                               dns_suffix=dns_suffixes)

    converter = export.DNSClientConfigurationToExportedDNSClientConfiguration()
    results = list(converter.Convert(export.ExportedMetadata(
    ), config, token=self.token))

    self.assertEqual(len(results), 1)
    self.assertEqual(results[0].dns_servers, " ".join(dns_servers))
    self.assertEqual(results[0].dns_suffixes, " ".join(dns_suffixes))


class ArtifactFilesDownloaderResultConverterTest(test_lib.GRRBaseTest):
  """Tests for ArtifactFilesDownloaderResultConverter."""

  def setUp(self):
    super(ArtifactFilesDownloaderResultConverterTest, self).setUp()

    self.registry_stat = rdf_client.StatEntry(
        registry_type=rdf_client.StatEntry.RegistryType.REG_SZ,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY),
        registry_data=rdf_protodict.DataBlob(string="C:\\Windows\\Sidebar.exe"))

    self.file_stat = rdf_client.StatEntry(pathspec=rdf_paths.PathSpec(
        path="/tmp/bar.exe",
        pathtype=rdf_paths.PathSpec.PathType.OS))

  def testExportsOriginalResultAnywayIfItIsNotStatEntry(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=DataAgnosticConverterTestValue())

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(export.ExportedMetadata(
    ), result, token=self.token))

    # Test that something gets exported and that this something wasn't
    # produced by ArtifactFilesDownloaderResultConverter.
    self.assertEqual(len(converted), 1)
    self.assertFalse(isinstance(converted[0],
                                export.ExportedArtifactFilesDownloaderResult))

  def testExportsOriginalResultIfOriginalResultIsNotRegistryOrFileStatEntry(
      self):
    stat = rdf_client.StatEntry(
        aff4path=rdfvalue.RDFURN("aff4:/C.00000000000000/fs/os/some/path"),
        pathspec=rdf_paths.PathSpec(
            path="some/path",
            pathtype=rdf_paths.PathSpec.PathType.MEMORY))
    result = collectors.ArtifactFilesDownloaderResult(original_result=stat)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(export.ExportedMetadata(
    ), result, token=self.token))

    # Test that something gets exported and that this something wasn't
    # produced by ArtifactFilesDownloaderResultConverter.
    self.assertEqual(len(converted), 1)
    self.assertFalse(isinstance(converted[0],
                                export.ExportedArtifactFilesDownloaderResult))

  def testYieldsOneResultAndOneOriginalValueForFileStatEntry(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.file_stat)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(export.ExportedMetadata(
    ), result, token=self.token))

    default_exports = [
        v for v in converted
        if not isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertEquals(len(default_exports), 1)
    self.assertEquals(len(default_exports), 1)

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertEquals(len(downloader_exports), 1)
    self.assertEquals(downloader_exports[0].original_file.basename, "bar.exe")

  def testYieldsOneResultForRegistryStatEntryIfNoPathspecsWereFound(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(export.ExportedMetadata(
    ), result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertEquals(len(downloader_exports), 1)
    self.assertEquals(downloader_exports[0].original_registry_key.type,
                      "REG_SZ")
    self.assertEquals(downloader_exports[0].original_registry_key.data,
                      "C:\\Windows\\Sidebar.exe")

  def testIncludesRegistryStatEntryFoundPathspecIntoYieldedResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat,
        found_pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS"))

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(export.ExportedMetadata(
    ), result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertEquals(len(downloader_exports), 1)
    self.assertEquals(downloader_exports[0].found_path, "foo")

  def testIncludesFileStatEntryFoundPathspecIntoYieldedResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.file_stat,
        found_pathspec=self.file_stat.pathspec)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(export.ExportedMetadata(
    ), result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertEquals(len(downloader_exports), 1)
    self.assertEquals(downloader_exports[0].found_path, "/tmp/bar.exe")

  def testIncludesDownloadedFileIntoResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat,
        found_pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS"),
        downloaded_file=rdf_client.StatEntry(
            pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS")))

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(export.ExportedMetadata(
    ), result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertEquals(len(downloader_exports), 1)
    self.assertEquals(downloader_exports[0].downloaded_file.basename, "foo")


class DataAgnosticConverterTestValue(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DataAgnosticConverterTestValue


class DataAgnosticConverterTestValueWithMetadata(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.DataAgnosticConverterTestValueWithMetadata


class DataAgnosticExportConverterTest(test_lib.GRRBaseTest):
  """Tests for DataAgnosticExportConverter."""

  def ConvertOriginalValue(self, original_value):
    converted_values = list(export.DataAgnosticExportConverter().Convert(
        export.ExportedMetadata(source_urn=rdfvalue.RDFURN("aff4:/foo")),
        original_value))
    self.assertEqual(len(converted_values), 1)
    return converted_values[0]

  def testAddsMetadataAndIgnoresRepeatedAndMessagesFields(self):
    original_value = DataAgnosticConverterTestValue()
    converted_value = self.ConvertOriginalValue(original_value)

    # No 'metadata' field in the original value.
    self.assertItemsEqual([t.name for t in original_value.type_infos],
                          ["string_value", "int_value", "bool_value",
                           "repeated_string_value", "message_value",
                           "enum_value", "another_enum_value", "urn_value",
                           "datetime_value"])
    # But there's one in the converted value.
    self.assertItemsEqual([t.name for t in converted_value.type_infos],
                          ["metadata", "string_value", "int_value",
                           "bool_value", "enum_value", "another_enum_value",
                           "urn_value", "datetime_value"])

    # Metadata value is correctly initialized from user-supplied metadata.
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))

  def testIgnoresPredefinedMetadataField(self):
    original_value = DataAgnosticConverterTestValueWithMetadata(metadata=42,
                                                                value="value")
    converted_value = self.ConvertOriginalValue(original_value)

    self.assertItemsEqual([t.name for t in converted_value.type_infos],
                          ["metadata", "value"])
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))
    self.assertEqual(converted_value.value, "value")

  def testProcessesPrimitiveTypesCorrectly(self):
    original_value = DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        bool_value=True,
        enum_value=DataAgnosticConverterTestValue.EnumOption.OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))
    converted_value = self.ConvertOriginalValue(original_value)

    self.assertEqual(converted_value.string_value.__class__,
                     original_value.string_value.__class__)
    self.assertEqual(converted_value.string_value, "string value")

    self.assertEqual(converted_value.int_value.__class__,
                     original_value.int_value.__class__)
    self.assertEqual(converted_value.int_value, 42)

    self.assertEqual(converted_value.bool_value.__class__,
                     original_value.bool_value.__class__)
    self.assertEqual(converted_value.bool_value, True)

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
    original_value = DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        bool_value=True,
        enum_value=DataAgnosticConverterTestValue.EnumOption.OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))
    converted_value = self.ConvertOriginalValue(original_value)

    serialized = converted_value.SerializeToString()
    unserialized_converted_value = converted_value.__class__(serialized)

    self.assertEqual(converted_value, unserialized_converted_value)


class DynamicRekallResponseConverterTest(test_lib.GRRBaseTest):

  def SendReply(self, response_msg):
    self.messages.append(response_msg)

  def _ResetState(self):
    self.messages = []
    inventory = rdf_rekall_types.RekallProfile(
        name="inventory",
        data=('{"$INVENTORY": {},'
              '"$METADATA": {"ProfileClass":"Inventory", "Type":"Inventory"}}'),
        version="1",
        compression=0)

    self.rekall_session = grr_rekall.GrrRekallSession(
        action=self, initial_profiles=[inventory])
    self.renderer = self.rekall_session.GetRenderer()

    self.converter = export.DynamicRekallResponseConverter()

  def setUp(self):
    super(DynamicRekallResponseConverterTest, self).setUp()
    self._ResetState()

  def testSingleTableIsExported(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(42, "0x0", "data")
    self.renderer.flush()

    self.assertEqual(len(self.messages), 1)

    converted_values = list(self.converter.Convert(
        export.ExportedMetadata(source_urn="aff4:/foo/bar"),
        self.messages[0],
        token=self.token))

    self.assertEqual(len(converted_values), 1)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar_sample")
    self.assertEqual(converted_values[0].offset, "42")
    self.assertEqual(converted_values[0].hex, "0x0")
    self.assertEqual(converted_values[0].data, "data")

  def testCurrentSectionNameIsNotExportedWhenNotPresent(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(42, "0x0", "data")
    self.renderer.flush()

    converted_values = list(self.converter.Convert(
        export.ExportedMetadata(source_urn="aff4:/foo/bar"),
        self.messages[0],
        token=self.token))
    self.assertEqual(len(converted_values), 1)
    self.assertFalse(converted_values[0].HasField("section_name"))

  def testCurrentSectionNameIsExportedWhenPresent(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.section(name="some section")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(42, "0x0", "data")
    self.renderer.flush()

    converted_values = list(self.converter.Convert(
        export.ExportedMetadata(source_urn="aff4:/foo/bar"),
        self.messages[0],
        token=self.token))
    self.assertEqual(len(converted_values), 1)
    self.assertEqual(converted_values[0].section_name, "some section")

  def testTwoTablesAreExportedUsingValuesOfTheSameClass(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(42, "0x0", "data")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(43, "0x1", "otherdata")
    self.renderer.flush()

    converted_values = list(self.converter.Convert(
        export.ExportedMetadata(source_urn="aff4:/foo/bar"),
        self.messages[0],
        token=self.token))
    self.assertEqual(len(converted_values), 2)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar_sample")
    self.assertEqual(converted_values[0].offset, "42")
    self.assertEqual(converted_values[0].hex, "0x0")
    self.assertEqual(converted_values[0].data, "data")

    self.assertEqual(converted_values[1].__class__.__name__,
                     "RekallExport_foo_bar_sample")
    self.assertEqual(converted_values[1].offset, "43")
    self.assertEqual(converted_values[1].hex, "0x1")
    self.assertEqual(converted_values[1].data, "otherdata")

  def testTwoTablesHaveProperSectionNamesSet(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.section(name="some section")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(42, "0x0", "data")

    self.renderer.section(name="some other section")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(43, "0x1", "otherdata")
    self.renderer.flush()

    converted_values = list(self.converter.Convert(
        export.ExportedMetadata(source_urn="aff4:/foo/bar"),
        self.messages[0],
        token=self.token))
    self.assertEqual(converted_values[0].section_name, "some section")
    self.assertEqual(converted_values[1].section_name, "some other section")

  def testObjectRenderersAreAppliedCorrectly(self):
    messages = [
        ["t", [{"cname": "Address"}, {"cname": "Pointer"},
               {"cname": "PaddedAddress"}, {"cname": "AddressSpace"},
               {"cname": "Enumeration"}, {"cname": "Literal"},
               {"cname": "NativeType"}, {"cname": "NoneObject"},
               {"cname": "BaseObject"}, {"cname": "Struct"},
               {"cname": "UnixTimeStamp"}, {"cname": "_EPROCESS"},
               {"cname": "int"}, {"cname": "str"}], {}],
        ["r", {"Address": {"mro": ["Address"],
                           "value": 42},
               "Pointer": {"mro": ["Pointer"],
                           "target": 43},
               "PaddedAddress": {"mro": ["PaddedAddress"],
                                 "value": 44},
               "AddressSpace": {"mro": ["AddressSpace"],
                                "name": "some_address_space"},
               "Enumeration": {"mro": ["Enumeration"],
                               "enum": "ENUM",
                               "value": 42},
               "Literal": {"mro": ["Literal"],
                           "value": "some literal"},
               "NativeType": {"mro": ["NativeType"],
                              "value": "some"},
               "NoneObject": {"mro": ["NoneObject"]},
               "BaseObject": {"mro": ["BaseObject"],
                              "offset": 42},
               "Struct": {"mro": ["Struct"],
                          "offset": 42},
               "UnixTimeStamp": {"mro": ["UnixTimeStamp"],
                                 "epoch": 42},
               "_EPROCESS": {"mro": ["_EPROCESS"],
                             "Cybox": {"PID": 4,
                                       "Name": "System"}},
               "int": 42,
               "str": "some string"}]
    ]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="object_renderer_sample",
        json_messages=json.dumps(messages),
        json_context_messages=json.dumps([]))
    converted_values = list(self.converter.Convert(
        export.ExportedMetadata(source_urn="aff4:/foo/bar"),
        rekall_response,
        token=self.token))
    self.assertEqual(len(converted_values), 1)
    self.assertEqual(converted_values[0].Address, "0x2a")
    self.assertEqual(converted_values[0].Pointer, "0x0000000000002b")
    self.assertEqual(converted_values[0].PaddedAddress, "0x0000000000002c")
    self.assertEqual(converted_values[0].AddressSpace, "some_address_space")
    self.assertEqual(converted_values[0].Enumeration, "ENUM (42)")
    self.assertEqual(converted_values[0].Literal, "some literal")
    self.assertEqual(converted_values[0].NativeType, "some")
    self.assertEqual(converted_values[0].NoneObject, "-")
    self.assertEqual(converted_values[0].BaseObject, "@0x2a")
    self.assertEqual(converted_values[0].Struct, "0x2a")
    self.assertEqual(converted_values[0].UnixTimeStamp, "1970-01-01 00:00:42")
    self.assertEqual(converted_values[0]._EPROCESS, "System (4)")
    self.assertEqual(converted_values[0].int, "42")
    self.assertEqual(converted_values[0].str, "some string")

  def testSamePluginWithDifferentColumnsIsExportedCorrectly(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.table_header([("a", "a", "")])
    self.renderer.table_row(42)
    self.renderer.flush()
    self.assertEqual(len(self.messages), 1)

    converted_values = list(self.converter.Convert(
        export.ExportedMetadata(source_urn="aff4:/foo/bar1"),
        self.messages[0],
        token=self.token))

    self.assertEqual(len(converted_values), 1)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar1_sample")
    self.assertEqual(converted_values[0].a, "42")

    self._ResetState()

    self.renderer.start(plugin_name="sample")
    self.renderer.table_header([("b", "b", "")])
    self.renderer.table_row(43)
    self.renderer.flush()
    self.assertEqual(len(self.messages), 1)

    converted_values = list(self.converter.Convert(
        # It's important for the source_urn to be different as we rely on
        # different source_urns to generate different class names.
        export.ExportedMetadata(source_urn="aff4:/foo/bar2"),
        self.messages[0],
        token=self.token))

    self.assertEqual(len(converted_values), 1)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar2_sample")
    self.assertEqual(converted_values[0].b, "43")


class RekallResponseToExportedRekallProcessConverterTest(test_lib.GRRBaseTest):
  """Tests for RekallResponseToExportedRekallProcessConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallProcessConverterTest, self).setUp()
    self.converter = export.RekallResponseToExportedRekallProcessConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r", {"_EPROCESS": {
            "Cybox": {
                "Creation_Time": {
                    "epoch": 1281506799,
                },
                "Image_Info": {
                    "Command_Line": "\"C:\\Program Files\\VMware\\VMware "
                                    "Tools\\TPAutoConnSvc.exe\"",
                    "Path": "C:\\Program Files\\VMware\\VMware "
                            "Tools\\TPAutoConnSvc.exe",
                    "TrustedPath": "C:\\Program Files\\VMware\\VMware "
                                   "Tools\\Trusted\\TPAutoConnSvc.exe",
                    "type": "ProcessObj:ImageInfoType"
                },
                "Name": "TPAutoConnSvc.e",
                "PID": 1968,
                "Parent_PID": 676,
            },
        },}
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="handles", json_messages=json.dumps(messages))
    metadata = export.ExportedMetadata()
    converted_values = list(self.converter.Convert(
        metadata, rekall_response, token=self.token))

    self.assertEqual(len(converted_values), 1)

    model = export.ExportedRekallProcess(
        metadata=metadata,
        commandline="\"C:\\Program Files\\VMware\\VMware Tools"
        "\\TPAutoConnSvc.exe\"",
        creation_time=1281506799000000,
        fullpath="C:\\Program Files\\VMware\\VMware Tools"
        "\\TPAutoConnSvc.exe",
        trusted_fullpath="C:\\Program Files\\VMware\\VMware Tools"
        "\\Trusted\\TPAutoConnSvc.exe",
        name="TPAutoConnSvc.e",
        parent_pid=676,
        pid=1968)
    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="handles", json_messages=json.dumps(messages))
    converted_values = list(self.converter.Convert(export.ExportedMetadata(),
                                                   rekall_response,
                                                   token=self.token))

    self.assertEqual(len(converted_values), 0)


class RekallResponseToExportedRekallWindowsLoadedModuleConverterTest(
    test_lib.GRRBaseTest):
  """Tests for RekallResponseToExportedRekallProcessConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallWindowsLoadedModuleConverterTest,
          self).setUp()
    # pyformat: disable
    self.converter = export.RekallResponseToExportedRekallWindowsLoadedModuleConverter()  # pylint: disable=line-too-long
    # pyformat: enable

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r", {
            "_EPROCESS": {
                "Cybox": {
                    "Creation_Time": {
                        "epoch": 1281506799,
                    },
                    "Image_Info": {
                        "Command_Line": "C:\\WINDOWS\\System32\\alg.exe",
                        "File_Name": "\\Device\\HarddiskVolume1\\WINDOWS\\"
                                     "system32\\alg.exe",
                        "Path": "C:\\WINDOWS\\System32\\alg.exe",
                        "TrustedPath": "C:\\WINDOWS\\system32\\alg.exe",
                        "type": "ProcessObj:ImageInfoType"
                    },
                    "Name": "alg.exe",
                    "PID": 216,
                    "Parent_PID": 676,
                    "type": "ProcessObj:ProcessObjectType"
                },
            },
            "base_address": 1991507968,
            "in_init": True,
            "in_init_path": "C:\\WINDOWS\\System32\\WINMM.dll",
            "in_load": True,
            "in_load_path": "C:\\WINDOWS\\System32\\WINMM.dll",
            "in_mem": True,
            "in_mem_path": {
                "id": 25042,
                "mro": "NoneObject:object",
                "reason": "None Object"
            },
            "mapped_filename": "\\WINDOWS\\system32\\winmm.dll"
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="handles", json_messages=json.dumps(messages))
    metadata = export.ExportedMetadata()
    converted_values = list(self.converter.Convert(
        metadata, rekall_response, token=self.token))

    self.assertEqual(len(converted_values), 1)

    model = export.ExportedRekallWindowsLoadedModule(
        metadata=metadata,
        process=export.ExportedRekallProcess(
            metadata=metadata,
            commandline="C:\\WINDOWS\\System32\\alg.exe",
            creation_time=1281506799000000,
            fullpath="C:\\WINDOWS\\System32\\alg.exe",
            trusted_fullpath="C:\\WINDOWS\\system32\\alg.exe",
            name="alg.exe",
            parent_pid=676,
            pid=216),
        address=1991507968,
        fullpath="\\WINDOWS\\system32\\winmm.dll",
        in_init_fullpath="C:\\WINDOWS\\System32\\WINMM.dll",
        in_load_fullpath="C:\\WINDOWS\\System32\\WINMM.dll",
        is_in_init_list=True,
        is_in_load_list=True,
        is_in_mem_list=True)
    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="handles", json_messages=json.dumps(messages))
    converted_values = list(self.converter.Convert(export.ExportedMetadata(),
                                                   rekall_response,
                                                   token=self.token))

    self.assertEqual(len(converted_values), 0)


class ExportedLinuxSyscallTableEntryConverterTest(test_lib.GRRBaseTest):
  """Tests for ExportedLinuxSyscallTableEntryConverter."""

  def setUp(self):
    super(ExportedLinuxSyscallTableEntryConverterTest, self).setUp()
    self.converter = export.ExportedLinuxSyscallTableEntryConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r", {
            u"address": {
                u"id": 9062,
                u"mro": u"Pointer:NativeType:NumericProxyMixIn:"
                        "BaseObject:object",
                u"name": u"Array[198] ",
                u"offset": 281472854434512,
                u"target": 281472847827136,
                u"target_obj": {
                    u"id": 9069,
                    u"mro": u"Function:BaseAddressComparisonMixIn:"
                            "BaseObject:object",
                    u"name": u"Array[198] ",
                    u"offset": 281472847827136,
                    u"type_name": u"Function",
                    u"vm": u"AMD64PagedMemory"
                },
                u"type_name": u"Pointer",
                u"vm": u"AMD64PagedMemory"
            },
            u"highlight": None,
            u"index": 198,
            u"symbol": u"linux!SyS_lchown",
            u"table": u"ia32_sys_call_table"
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_syscall",
        json_messages=json.dumps(messages))
    metadata = export.ExportedMetadata()
    converted_values = list(self.converter.Convert(
        metadata, rekall_response, token=self.token))

    self.assertEqual(len(converted_values), 1)

    model = export.ExportedLinuxSyscallTableEntry(
        metadata=metadata,
        table="ia32_sys_call_table",
        index=198,
        handler_address=281472847827136,
        symbol="linux!SyS_lchown")
    self.assertEqual(list(converted_values)[0], model)

  def testConvertsSyscallEntriesWithMultipleSymbolNames(self):
    messages = [[
        "r", {
            u"address": {
                u"id": 33509,
                u"mro": u"Pointer:NativeType:NumericProxyMixIn:"
                        "BaseObject:object",
                u"name": u"Array[354] ",
                u"offset": 281472854435760,
                u"target": 281472847114896,
                u"target_obj": {
                    u"id": 33516,
                    u"mro": u"Function:BaseAddressComparisonMixIn:"
                            "BaseObject:object",
                    u"name": u"Array[354] ",
                    u"offset": 281472847114896,
                    u"type_name": u"Function",
                    u"vm": u"AMD64PagedMemory"
                },
                u"type_name": u"Pointer",
                u"vm": u"AMD64PagedMemory"
            },
            u"highlight": None,
            u"index": 354,
            u"symbol": [u"linux!SyS_seccomp", u"linux!sys_seccomp"],
            u"table": u"ia32_sys_call_table"
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_syscall",
        json_messages=json.dumps(messages))
    metadata = export.ExportedMetadata()
    converted_values = list(self.converter.Convert(
        metadata, rekall_response, token=self.token))
    self.assertEqual(len(converted_values), 2)

    model = export.ExportedLinuxSyscallTableEntry(
        metadata=metadata,
        table="ia32_sys_call_table",
        index=354,
        handler_address=281472847114896,
        symbol="linux!SyS_seccomp")
    self.assertEqual(converted_values[0], model)

    model = export.ExportedLinuxSyscallTableEntry(
        metadata=metadata,
        table="ia32_sys_call_table",
        index=354,
        handler_address=281472847114896,
        symbol="linux!sys_seccomp")
    self.assertEqual(converted_values[1], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_task_fops",
        json_messages=json.dumps(messages))
    converted_values = list(self.converter.Convert(export.ExportedMetadata(),
                                                   rekall_response,
                                                   token=self.token))
    self.assertEqual(len(converted_values), 0)


class RekallResponseToExportedRekallLinuxTaskOpConverterTest(
    test_lib.GRRBaseTest):
  """Tests for RekallResponseToExportedRekallLinuxTaskOpConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallLinuxTaskOpConverterTest, self).setUp()
    self.converter = export.RekallResponseToExportedRekallLinuxTaskOpConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
            u"address": {
                u"id": 12331,
                u"mro":
                    u"Function:BaseAddressComparisonMixIn:BaseObject:object",
                u"name": u"write",
                u"offset": 281472847829584,
                u"type_name": u"Function",
                u"vm": u"AMD64PagedMemory"},
            u"comm": u"init",
            u"highlight": None,
            u"member": u"write",
            u"module": u"linux",
            u"pid": 1
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_task_fops",
        json_messages=json.dumps(messages))
    metadata = export.ExportedMetadata()
    converted_values = list(self.converter.Convert(
        metadata, rekall_response, token=self.token))

    self.assertEqual(len(converted_values), 1)

    task = export.ExportedRekallLinuxTask(metadata=metadata, pid=1, name="init")

    model = export.ExportedRekallLinuxTaskOp(metadata=metadata,
                                             operation="write",
                                             handler_address=281472847829584,
                                             module="linux",
                                             task=task)
    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_task_fops",
        json_messages=json.dumps(messages))
    converted_values = list(self.converter.Convert(export.ExportedMetadata(),
                                                   rekall_response,
                                                   token=self.token))
    self.assertEqual(len(converted_values), 0)


class RekallResponseToExportedRekallLinuxProcOpConverterTest(
    test_lib.GRRBaseTest):
  """Tests for RekallResponseToExportedRekallLinuxProcOpConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallLinuxProcOpConverterTest, self).setUp()
    self.converter = export.RekallResponseToExportedRekallLinuxProcOpConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
            u"address": {
                u"id": 11447,
                u"mro":
                    u"Function:BaseAddressComparisonMixIn:BaseObject:object",
                u"name": u"read",
                u"offset": 281472847976656,
                u"type_name": u"Function",
                u"vm": u"AMD64PagedMemory"},
            u"highlight": None,
            u"member": u"read",
            u"module": u"linux",
            u"path": u"/proc/fb",
            u"proc_dir_entry": {
                u"id": 11343,
                u"mro": u"proc_dir_entry:Struct:BaseAddressComparisonMixIn:"
                        "BaseObject:object",
                u"name": u"next",
                u"offset": 149567999345408,
                u"type_name": u"proc_dir_entry",
                u"vm": u"AMD64PagedMemory"}
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_proc_fops",
        json_messages=json.dumps(messages))
    metadata = export.ExportedMetadata()
    converted_values = list(self.converter.Convert(
        metadata, rekall_response, token=self.token))

    self.assertEqual(len(converted_values), 1)

    model = export.ExportedRekallLinuxProcOp(metadata=metadata,
                                             operation="read",
                                             handler_address=281472847976656,
                                             module="linux",
                                             fullpath="/proc/fb")
    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_task_fops",
        json_messages=json.dumps(messages))
    converted_values = list(self.converter.Convert(export.ExportedMetadata(),
                                                   rekall_response,
                                                   token=self.token))
    self.assertEqual(len(converted_values), 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
