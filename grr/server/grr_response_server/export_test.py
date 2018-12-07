#!/usr/bin/env python
"""Tests for export converters."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json
import os
import socket

from grr_response_client.components.rekall_support import grr_rekall
from grr_response_core.lib import flags
from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import rdf_yara
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import export
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import filestore
from grr_response_server.check_lib import checks
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import transfer
from grr_response_server.hunts import results as hunts_results
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import export_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


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


class ExportTestBase(test_lib.GRRBaseTest):
  """Base class for the export tests."""

  def setUp(self):
    super(ExportTestBase, self).setUp()
    self.client_id = self.SetupClient(0)
    self.metadata = export.ExportedMetadata(client_urn=self.client_id)


@db_test_lib.DualDBTest
class ExportTest(ExportTestBase):
  """Tests export converters."""

  def testConverterIsCorrectlyFound(self):
    dummy_value = DummyRDFValue("result")
    result = list(export.ConvertValues(self.metadata, [dummy_value]))
    self.assertLen(result, 1)
    self.assertIsInstance(result[0], rdfvalue.RDFString)
    self.assertEqual(result[0], "result")

  def testDoesNotRaiseWhenNoSpecificConverterIsDefined(self):
    dummy_value = DummyRDFValue2("some")
    export.ConvertValues(self.metadata, [dummy_value])

  def testDataAgnosticConverterIsUsedWhenNoSpecificConverterIsDefined(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue()

    # There's no converter defined for
    # export_test_lib.DataAgnosticConverterTestValue,
    # so we expect DataAgnosticExportConverter to be used.
    converted_values = list(
        export.ConvertValues(self.metadata, [original_value]))
    self.assertLen(converted_values, 1)
    converted_value = converted_values[0]

    self.assertEqual(converted_value.__class__.__name__,
                     "AutoExportedDataAgnosticConverterTestValue")

  def testConvertsSingleValueWithMultipleAssociatedConverters(self):
    dummy_value = DummyRDFValue3("some")
    result = list(export.ConvertValues(self.metadata, [dummy_value]))
    self.assertLen(result, 2)
    self.assertTrue((isinstance(result[0], DummyRDFValue) and
                     isinstance(result[1], DummyRDFValue2)) or
                    (isinstance(result[0], DummyRDFValue2) and
                     isinstance(result[1], DummyRDFValue)))
    self.assertTrue((result[0] == DummyRDFValue("someA") and
                     result[1] == DummyRDFValue2("someB")) or
                    (result[0] == DummyRDFValue2("someB") and
                     result[1] == DummyRDFValue("someA")))

  def _ConvertsCollectionWithValuesWithSingleConverter(self, coll_type):
    with data_store.DB.GetMutationPool() as pool:
      fd = coll_type(rdfvalue.RDFURN("aff4:/testcoll"))
      src1 = rdf_client.ClientURN("C.0000000000000000")
      fd.AddAsMessage(DummyRDFValue("some"), src1, mutation_pool=pool)
      fixture_test_lib.ClientFixture(src1, token=self.token)

      src2 = rdf_client.ClientURN("C.0000000000000001")
      fd.AddAsMessage(DummyRDFValue("some2"), src2, mutation_pool=pool)
      fixture_test_lib.ClientFixture(src2, token=self.token)

    results = export.ConvertValues(self.metadata, [fd], token=self.token)
    results = sorted(str(v) for v in results)

    self.assertLen(results, 2)
    self.assertEqual(results[0], "some")
    self.assertEqual(results[1], "some2")

  def testConvertsHuntResultCollectionWithValuesWithSingleConverter(self):
    self._ConvertsCollectionWithValuesWithSingleConverter(
        hunts_results.HuntResultCollection)

  def _ConvertsCollectionWithMultipleConverters(self, coll_type):
    fd = coll_type(rdfvalue.RDFURN("aff4:/testcoll"))

    with data_store.DB.GetMutationPool() as pool:
      src1 = rdf_client.ClientURN("C.0000000000000000")
      fd.AddAsMessage(DummyRDFValue3("some1"), src1, mutation_pool=pool)
      fixture_test_lib.ClientFixture(src1, token=self.token)

      src2 = rdf_client.ClientURN("C.0000000000000001")
      fd.AddAsMessage(DummyRDFValue3("some2"), src2, mutation_pool=pool)
      fixture_test_lib.ClientFixture(src2, token=self.token)

    results = export.ConvertValues(self.metadata, [fd], token=self.token)
    results = sorted(results, key=str)

    self.assertLen(results, 4)
    self.assertEqual([str(v) for v in results if isinstance(v, DummyRDFValue)],
                     ["some1A", "some2A"])
    self.assertEqual([str(v) for v in results if isinstance(v, DummyRDFValue2)],
                     ["some1B", "some2B"])

  def testConvertsHuntResultCollectionWithValuesWithMultipleConverters(self):
    self._ConvertsCollectionWithMultipleConverters(
        hunts_results.HuntResultCollection)

  def testStatEntryToExportedFileConverterWithMissingAFF4File(self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].basename, "path")
    self.assertEqual(results[0].urn, self.client_id.Add("fs/os/some/path"))
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
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(
        path="/Ext2IFS_1_10b.exe", pathtype=rdf_paths.PathSpec.PathType.TSK)

    client_mock = action_mocks.GetFileClientMock()
    flow_test_lib.TestFlowHelper(
        transfer.GetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        pathspec=pathspec)

    urn = pathspec.AFF4Path(self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)

    stat = fd.Get(fd.Schema.STAT)
    self.assertTrue(stat)

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].basename, "Ext2IFS_1_10b.exe")
    self.assertEqual(results[0].urn, urn)

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)

    # Convert again, now specifying export_files_contents=True in options.
    converter = export.StatEntryToExportedFileConverter(
        options=export.ExportOptions(export_files_contents=True))
    results = list(converter.Convert(self.metadata, stat, token=self.token))
    self.assertTrue(results[0].content)
    self.assertEqual(
        results[0].content_sha256,
        "69264282ca1a3d4e7f9b1f43720f719a4ea47964f0bfd1b2ba88424f1c61395d")
    self.assertEqual("", results[0].metadata.annotations)

  def testStatEntryToExportedFileConverterWithHashedAFF4File(self):
    filestore.FileStoreInit().Run()

    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(
        path="/Ext2IFS_1_10b.exe", pathtype=rdf_paths.PathSpec.PathType.TSK)
    urn = pathspec.AFF4Path(self.client_id)

    client_mock = action_mocks.GetFileClientMock()
    flow_test_lib.TestFlowHelper(
        transfer.GetFile.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        pathspec=pathspec)

    if data_store.RelationalDBReadEnabled(
        category="vfs") and data_store.RelationalDBReadEnabled(
            category="filestore"):
      path_info = rdf_objects.PathInfo.FromPathSpec(pathspec)
      path_info = data_store.REL_DB.ReadPathInfo(self.client_id.Basename(),
                                                 path_info.path_type,
                                                 tuple(path_info.components))
      hash_value = path_info.hash_entry
    else:
      events.Events.PublishEvent(
          "LegacyFileStore.AddFileToStore", urn, token=self.token)
      fd = aff4.FACTORY.Open(urn, token=self.token)
      hash_value = fd.Get(fd.Schema.HASH)

    self.assertTrue(hash_value)

    converter = export.StatEntryToExportedFileConverter()
    results = list(
        converter.Convert(
            self.metadata,
            rdf_client_fs.StatEntry(pathspec=pathspec),
            token=self.token))

    # Even though the file has a hash, it's not stored in StatEntry and
    # doesn't influence the result. Note: this is a change in behavior.
    # Previously StatEntry exporter was opening corresponding file objects
    # and reading hashes from these objects. This approach was questionable
    # at best, since there was no guarantee that hashes actually corresponded
    # to files in question.
    self.assertFalse(results[0].hash_md5)
    self.assertFalse(results[0].hash_sha1)
    self.assertFalse(results[0].hash_sha256)

  def testExportedFileConverterIgnoresRegistryKeys(self):
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

    converter = export.StatEntryToExportedFileConverter()
    results = list(converter.Convert(self.metadata, stat, token=self.token))
    self.assertFalse(results)

  def testStatEntryToExportedRegistryKeyConverter(self):
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        registry_type=rdf_client_fs.StatEntry.RegistryType.REG_EXPAND_SZ,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY),
        registry_data=rdf_protodict.DataBlob(string="Sidebar.exe"))

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn,
        self.client_id.Add("registry/HKEY_USERS/S-1-5-20/Software/"
                           "Microsoft/Windows/CurrentVersion/Run/Sidebar"))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].type,
                     rdf_client_fs.StatEntry.RegistryType.REG_EXPAND_SZ)
    self.assertEqual(results[0].data, "Sidebar.exe")

  def testRegistryKeyConverterIgnoresNonRegistryStatEntries(self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS),
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat, token=self.token))

    self.assertFalse(results)

  def testRegistryKeyConverterWorksWithRegistryKeys(self):
    # Registry keys won't have registry_type and registry_data set.
    stat = rdf_client_fs.StatEntry(
        st_mode=32768,
        st_size=51,
        st_mtime=1247546054,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY))

    converter = export.StatEntryToExportedRegistryKeyConverter()
    results = list(converter.Convert(self.metadata, stat, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(
        results[0].urn,
        rdfvalue.RDFURN(
            self.client_id.Add("registry/HKEY_USERS/S-1-5-20/Software/"
                               "Microsoft/Windows/CurrentVersion/Run/Sidebar")))
    self.assertEqual(results[0].last_modified,
                     rdfvalue.RDFDatetimeSeconds(1247546054))
    self.assertEqual(results[0].data, "")
    self.assertEqual(results[0].type, 0)

  def testProcessToExportedProcessConverter(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083)

    converter = export.ProcessToExportedProcessConverter()
    results = list(converter.Convert(self.metadata, process, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].ppid, 1)
    self.assertEqual(results[0].cmdline, "cmd.exe")
    self.assertEqual(results[0].exe, "c:\\windows\\cmd.exe")
    self.assertEqual(results[0].ctime, 1333718907167083)

  def testProcessToExportedOpenFileConverter(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        open_files=["/some/a", "/some/b"])

    converter = export.ProcessToExportedOpenFileConverter()
    results = list(converter.Convert(self.metadata, process, token=self.token))

    self.assertLen(results, 2)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].path, "/some/a")
    self.assertEqual(results[1].pid, 2)
    self.assertEqual(results[1].path, "/some/b")

  def testProcessToExportedNetworkConnection(self):
    conn1 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.LISTEN,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=0),
        pid=2136,
        ctime=0)
    conn2 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.LISTEN,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(
            ip="192.168.1.1", port=31337),
        remote_address=rdf_client_network.NetworkEndpoint(
            ip="1.2.3.4", port=6667),
        pid=1,
        ctime=0)

    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        connections=[conn1, conn2])

    converter = export.ProcessToExportedNetworkConnectionConverter()
    results = list(converter.Convert(self.metadata, process, token=self.token))

    self.assertLen(results, 2)
    self.assertEqual(results[0].state,
                     rdf_client_network.NetworkConnection.State.LISTEN)
    self.assertEqual(results[0].type,
                     rdf_client_network.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[0].local_address.ip, "0.0.0.0")
    self.assertEqual(results[0].local_address.port, 22)
    self.assertEqual(results[0].remote_address.ip, "0.0.0.0")
    self.assertEqual(results[0].remote_address.port, 0)
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 0)

    self.assertEqual(results[1].state,
                     rdf_client_network.NetworkConnection.State.LISTEN)
    self.assertEqual(results[1].type,
                     rdf_client_network.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[1].local_address.ip, "192.168.1.1")
    self.assertEqual(results[1].local_address.port, 31337)
    self.assertEqual(results[1].remote_address.ip, "1.2.3.4")
    self.assertEqual(results[1].remote_address.port, 6667)
    self.assertEqual(results[1].pid, 1)
    self.assertEqual(results[1].ctime, 0)

  def testRDFURNConverterWithURNPointingToFile(self):
    urn = self.client_id.Add("fs/os/some/path")

    stat_entry = rdf_client_fs.StatEntry()
    stat_entry.pathspec.path = "/some/path"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    stat_entry.st_mode = 33184
    stat_entry.st_ino = 1063090
    stat_entry.st_atime = 1336469177
    stat_entry.st_mtime = 1336129892
    stat_entry.st_ctime = 1336129892

    with aff4.FACTORY.Create(urn, aff4_grr.VFSFile, token=self.token) as fd:
      fd.Set(fd.Schema.STAT(stat_entry))

    if data_store.RelationalDBWriteEnabled():
      path_info = rdf_objects.PathInfo.OS(
          components=["some", "path"], stat_entry=stat_entry)
      data_store.REL_DB.WritePathInfos(self.client_id.Basename(), [path_info])

    converter = export.RDFURNConverter()
    results = list(converter.Convert(self.metadata, urn, token=self.token))

    self.assertTrue(len(results))

    exported_files = [
        r for r in results if r.__class__.__name__ == "ExportedFile"
    ]
    self.assertLen(exported_files, 1)
    exported_file = exported_files[0]

    self.assertTrue(exported_file)
    self.assertEqual(exported_file.urn, urn)

  def testClientSummaryToExportedNetworkInterfaceConverter(self):
    client_summary = rdf_client.ClientSummary(interfaces=[
        rdf_client_network.Interface(
            mac_address=b"123456",
            ifname="eth0",
            addresses=[
                rdf_client_network.NetworkAddress(
                    address_type=rdf_client_network.NetworkAddress.Family.INET,
                    packed_bytes=socket.inet_pton(socket.AF_INET, "127.0.0.1"),
                ),
                rdf_client_network.NetworkAddress(
                    address_type=rdf_client_network.NetworkAddress.Family.INET,
                    packed_bytes=socket.inet_pton(socket.AF_INET, "10.0.0.1"),
                ),
                rdf_client_network.NetworkAddress(
                    address_type=rdf_client_network.NetworkAddress.Family.INET6,
                    packed_bytes=socket.inet_pton(socket.AF_INET6,
                                                  "2001:720:1500:1::a100"),
                )
            ])
    ])

    converter = export.ClientSummaryToExportedNetworkInterfaceConverter()
    results = list(
        converter.Convert(self.metadata, client_summary, token=self.token))
    self.assertLen(results, 1)
    self.assertEqual(results[0].mac_address, "123456".encode("hex"))
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")

  def testInterfaceToExportedNetworkInterfaceConverter(self):
    interface = rdf_client_network.Interface(
        mac_address=b"123456",
        ifname="eth0",
        addresses=[
            rdf_client_network.NetworkAddress(
                address_type=rdf_client_network.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "127.0.0.1"),
            ),
            rdf_client_network.NetworkAddress(
                address_type=rdf_client_network.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "10.0.0.1"),
            ),
            rdf_client_network.NetworkAddress(
                address_type=rdf_client_network.NetworkAddress.Family.INET6,
                packed_bytes=socket.inet_pton(socket.AF_INET6,
                                              "2001:720:1500:1::a100"),
            )
        ])

    converter = export.InterfaceToExportedNetworkInterfaceConverter()
    results = list(
        converter.Convert(self.metadata, interface, token=self.token))
    self.assertLen(results, 1)
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
    metadata = self.metadata

    results = list(
        export.ConvertValues(metadata, checkresults, token=self.token))
    self.assertLen(results, 3)
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

  def testClientSummaryToExportedClientConverter(self):
    client_summary = rdf_client.ClientSummary()
    metadata = export.ExportedMetadata(hostname="ahostname")

    converter = export.ClientSummaryToExportedClientConverter()
    results = list(
        converter.Convert(metadata, client_summary, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].metadata.hostname, "ahostname")

  def testBufferReferenceToExportedMatchConverter(self):
    buffer_reference = rdf_client.BufferReference(
        offset=42,
        length=43,
        data=b"somedata",
        pathspec=rdf_paths.PathSpec(
            path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS))

    converter = export.BufferReferenceToExportedMatchConverter()
    results = list(
        converter.Convert(self.metadata, buffer_reference, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].offset, 42)
    self.assertEqual(results[0].length, 43)
    self.assertEqual(results[0].data, b"somedata")
    self.assertEqual(results[0].urn, self.client_id.Add("fs/os/some/path"))

  def testFileFinderResultExportConverter(self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS)

    match1 = rdf_client.BufferReference(
        offset=42, length=43, data=b"somedata1", pathspec=pathspec)
    match2 = rdf_client.BufferReference(
        offset=44, length=45, data=b"somedata2", pathspec=pathspec)
    stat_entry = rdf_client_fs.StatEntry(
        pathspec=pathspec,
        st_mode=33184,
        st_ino=1063090,
        st_atime=1336469177,
        st_mtime=1336129892,
        st_ctime=1336129892)

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, matches=[match1, match2])

    converter = export.FileFinderResultConverter()
    results = list(
        converter.Convert(self.metadata, file_finder_result, token=self.token))

    # We expect 1 ExportedFile instance in the results
    exported_files = [
        result for result in results if isinstance(result, export.ExportedFile)
    ]
    self.assertLen(exported_files, 1)

    self.assertEqual(exported_files[0].basename, "path")
    self.assertEqual(exported_files[0].urn,
                     self.client_id.Add("fs/os/some/path"))
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
    exported_matches = [
        result for result in results if isinstance(result, export.ExportedMatch)
    ]
    exported_matches = sorted(exported_matches, key=lambda x: x.offset)
    self.assertLen(exported_matches, 2)

    self.assertEqual(exported_matches[0].offset, 42)
    self.assertEqual(exported_matches[0].length, 43)
    self.assertEqual(exported_matches[0].data, b"somedata1")
    self.assertEqual(exported_matches[0].urn,
                     self.client_id.Add("fs/os/some/path"))

    self.assertEqual(exported_matches[1].offset, 44)
    self.assertEqual(exported_matches[1].length, 45)
    self.assertEqual(exported_matches[1].data, b"somedata2")
    self.assertEqual(exported_matches[1].urn,
                     self.client_id.Add("fs/os/some/path"))

    # Also test registry entries.
    data = rdf_protodict.DataBlob()
    data.SetValue(b"testdata")
    stat_entry = rdf_client_fs.StatEntry(
        registry_type="REG_SZ",
        registry_data=data,
        pathspec=rdf_paths.PathSpec(
            path="HKEY_USERS/S-1-1-1-1/Software", pathtype="REGISTRY"))
    file_finder_result = rdf_file_finder.FileFinderResult(stat_entry=stat_entry)
    converter = export.FileFinderResultConverter()
    results = list(
        converter.Convert(self.metadata, file_finder_result, token=self.token))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export.ExportedRegistryKey)
    result = results[0]

    self.assertEqual(result.data, b"testdata")
    self.assertEqual(
        result.urn,
        self.client_id.Add("registry/HKEY_USERS/S-1-1-1-1/Software"))

  def testFileFinderResultExportConverterConvertsHashes(self):
    pathspec = rdf_paths.PathSpec(
        path="/some/path", pathtype=rdf_paths.PathSpec.PathType.OS)
    pathspec2 = rdf_paths.PathSpec(
        path="/some/path2", pathtype=rdf_paths.PathSpec.PathType.OS)

    stat_entry = rdf_client_fs.StatEntry(
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

    stat_entry2 = rdf_client_fs.StatEntry(
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

    file_finder_result = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry, hash_entry=hash_entry)
    file_finder_result2 = rdf_file_finder.FileFinderResult(
        stat_entry=stat_entry2, hash_entry=hash_entry2)

    converter = export.FileFinderResultConverter()
    results = list(
        converter.BatchConvert([(self.metadata, file_finder_result),
                                (self.metadata, file_finder_result2)],
                               token=self.token))

    exported_files = [
        result for result in results if isinstance(result, export.ExportedFile)
    ]
    self.assertLen(exported_files, 2)
    self.assertCountEqual([x.basename for x in exported_files],
                          ["path", "path2"])

    for export_result in exported_files:
      if export_result.basename == "path":
        self.assertEqual(
            export_result.hash_sha256,
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
        self.assertEqual(
            export_result.hash_sha256,
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

  def testRDFBytesConverter(self):
    data = rdfvalue.RDFBytes(b"foobar")

    converter = export.RDFBytesToExportedBytesConverter()
    results = list(converter.Convert(self.metadata, data, token=self.token))

    self.assertTrue(len(results))

    exported_bytes = [
        r for r in results if r.__class__.__name__ == "ExportedBytes"
    ]
    self.assertLen(exported_bytes, 1)

    self.assertEqual(exported_bytes[0].data, data)
    self.assertEqual(exported_bytes[0].length, 6)

  def testRDFStringConverter(self):
    data = rdfvalue.RDFString("foobar")

    converters = export.ExportConverter.GetConvertersByValue(data)
    self.assertTrue(converters)
    for converter in converters:
      converted_data = list(converter().Convert(
          self.metadata, data, token=self.token))
      self.assertLen(converted_data, 1)
      for converted in converted_data:
        self.assertIsInstance(converted, export.ExportedString)
        self.assertEqual(converted.data, unicode(data))

  def testGrrMessageConverter(self):
    payload = DummyRDFValue4(
        "some", age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
    msg = rdf_flows.GrrMessage(payload=payload)
    msg.source = self.client_id
    fixture_test_lib.ClientFixture(msg.source, token=self.token)

    metadata = export.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000000/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(2):
      results = list(converter.Convert(metadata, msg, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].original_timestamp,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2))
    self.assertEqual(results[0].source_urn,
                     "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results")

  def testGrrMessageConverterWithOneMissingClient(self):
    payload1 = DummyRDFValue4(
        "some", age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
    msg1 = rdf_flows.GrrMessage(payload=payload1)
    msg1.source = rdf_client.ClientURN("C.0000000000000000")
    fixture_test_lib.ClientFixture(msg1.source, token=self.token)

    payload2 = DummyRDFValue4(
        "some2", age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
    msg2 = rdf_flows.GrrMessage(payload=payload2)
    msg2.source = rdf_client.ClientURN("C.0000000000000001")

    metadata1 = export.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000000/Results"))
    metadata2 = export.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000001/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(
          converter.BatchConvert([(metadata1, msg1), (metadata2, msg2)],
                                 token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].original_timestamp,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
    self.assertEqual(results[0].timestamp,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3))
    self.assertEqual(results[0].source_urn,
                     "aff4:/hunts/" + str(queues.HUNTS) + ":000000/Results")

  def testGrrMessageConverterMultipleTypes(self):
    payload1 = DummyRDFValue3(
        "some", age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
    msg1 = rdf_flows.GrrMessage(payload=payload1)
    msg1.source = rdf_client.ClientURN("C.0000000000000000")
    fixture_test_lib.ClientFixture(msg1.source, token=self.token)

    payload2 = DummyRDFValue5(
        "some2", age=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1))
    msg2 = rdf_flows.GrrMessage(payload=payload2)
    msg2.source = rdf_client.ClientURN("C.0000000000000000")

    metadata1 = export.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000000/Results"))
    metadata2 = export.ExportedMetadata(
        source_urn=rdfvalue.RDFURN("aff4:/hunts/" + str(queues.HUNTS) +
                                   ":000001/Results"))

    converter = export.GrrMessageConverter()
    with test_lib.FakeTime(3):
      results = list(
          converter.BatchConvert([(metadata1, msg1), (metadata2, msg2)],
                                 token=self.token))

    self.assertLen(results, 3)
    # RDFValue3 gets converted to RDFValue2 and RDFValue, RDFValue5 stays at 5.
    self.assertCountEqual(["DummyRDFValue2", "DummyRDFValue", "DummyRDFValue5"],
                          [x.__class__.__name__ for x in results])

  def testDNSClientConfigurationToExportedDNSClientConfiguration(self):
    dns_servers = ["192.168.1.1", "8.8.8.8"]
    dns_suffixes = ["internal.company.com", "company.com"]
    config = rdf_client_network.DNSClientConfiguration(
        dns_server=dns_servers, dns_suffix=dns_suffixes)

    converter = export.DNSClientConfigurationToExportedDNSClientConfiguration()
    results = list(converter.Convert(self.metadata, config, token=self.token))

    self.assertLen(results, 1)
    self.assertEqual(results[0].dns_servers, " ".join(dns_servers))
    self.assertEqual(results[0].dns_suffixes, " ".join(dns_suffixes))


class DictToExportedDictItemsConverterTest(ExportTestBase):
  """Tests for DictToExportedDictItemsConverter."""

  def setUp(self):
    super(DictToExportedDictItemsConverterTest, self).setUp()
    self.converter = export.DictToExportedDictItemsConverter()

  def testConvertsDictWithPrimitiveValues(self):
    source = rdf_protodict.Dict()
    source["foo"] = "bar"
    source["bar"] = 42

    # Serialize/unserialize to make sure we deal with the object that is
    # similar to what we may get from the datastore.
    source = rdf_protodict.Dict.FromSerializedString(source.SerializeToString())

    converted = list(
        self.converter.Convert(self.metadata, source, token=self.token))

    self.assertLen(converted, 2)

    # Output should be stable sorted by dict's keys.
    self.assertEqual(converted[0].key, "bar")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "foo")
    self.assertEqual(converted[1].value, "bar")

  def testConvertsDictWithNestedSetListOrTuple(self):
    # Note that set's contents will be sorted on export.
    variants = [set([43, 42, 44]), (42, 43, 44), [42, 43, 44]]

    for variant in variants:
      source = rdf_protodict.Dict()
      source["foo"] = "bar"
      source["bar"] = variant

      # Serialize/unserialize to make sure we deal with the object that is
      # similar to what we may get from the datastore.
      source = rdf_protodict.Dict.FromSerializedString(
          source.SerializeToString())

      converted = list(
          self.converter.Convert(self.metadata, source, token=self.token))

      self.assertLen(converted, 4)
      self.assertEqual(converted[0].key, "bar[0]")
      self.assertEqual(converted[0].value, "42")
      self.assertEqual(converted[1].key, "bar[1]")
      self.assertEqual(converted[1].value, "43")
      self.assertEqual(converted[2].key, "bar[2]")
      self.assertEqual(converted[2].value, "44")
      self.assertEqual(converted[3].key, "foo")
      self.assertEqual(converted[3].value, "bar")

  def testConvertsDictWithNestedDict(self):
    source = rdf_protodict.Dict()
    source["foo"] = "bar"
    source["bar"] = {"a": 42, "b": 43}

    # Serialize/unserialize to make sure we deal with the object that is
    # similar to what we may get from the datastore.
    source = rdf_protodict.Dict.FromSerializedString(source.SerializeToString())

    converted = list(
        self.converter.Convert(self.metadata, source, token=self.token))

    self.assertLen(converted, 3)

    # Output should be stable sorted by dict's keys.
    self.assertEqual(converted[0].key, "bar.a")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "bar.b")
    self.assertEqual(converted[1].value, "43")
    self.assertEqual(converted[2].key, "foo")
    self.assertEqual(converted[2].value, "bar")

  def testConvertsDictWithNestedDictAndIterables(self):
    source = rdf_protodict.Dict()
    source["foo"] = "bar"
    # pyformat: disable
    source["bar"] = {
        "a": {
            "c": [42, 43, 44, {"x": "y"}],
            "d": "oh"
        },
        "b": 43
    }
    # pyformat: enable

    # Serialize/unserialize to make sure we deal with the object that is
    # similar to what we may get from the datastore.
    source = rdf_protodict.Dict.FromSerializedString(source.SerializeToString())

    converted = list(
        self.converter.Convert(self.metadata, source, token=self.token))

    self.assertLen(converted, 7)

    # Output should be stable sorted by dict's keys.
    self.assertEqual(converted[0].key, "bar.a.c[0]")
    self.assertEqual(converted[0].value, "42")
    self.assertEqual(converted[1].key, "bar.a.c[1]")
    self.assertEqual(converted[1].value, "43")
    self.assertEqual(converted[2].key, "bar.a.c[2]")
    self.assertEqual(converted[2].value, "44")
    self.assertEqual(converted[3].key, "bar.a.c[3].x")
    self.assertEqual(converted[3].value, "y")
    self.assertEqual(converted[4].key, "bar.a.d")
    self.assertEqual(converted[4].value, "oh")
    self.assertEqual(converted[5].key, "bar.b")
    self.assertEqual(converted[5].value, "43")
    self.assertEqual(converted[6].key, "foo")
    self.assertEqual(converted[6].value, "bar")


class ArtifactFilesDownloaderResultConverterTest(ExportTestBase):
  """Tests for ArtifactFilesDownloaderResultConverter."""

  def setUp(self):
    super(ArtifactFilesDownloaderResultConverterTest, self).setUp()

    self.registry_stat = rdf_client_fs.StatEntry(
        registry_type=rdf_client_fs.StatEntry.RegistryType.REG_SZ,
        pathspec=rdf_paths.PathSpec(
            path="/HKEY_USERS/S-1-5-20/Software/Microsoft/Windows/"
            "CurrentVersion/Run/Sidebar",
            pathtype=rdf_paths.PathSpec.PathType.REGISTRY),
        registry_data=rdf_protodict.DataBlob(string="C:\\Windows\\Sidebar.exe"))

    self.file_stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="/tmp/bar.exe", pathtype=rdf_paths.PathSpec.PathType.OS))

  def testExportsOriginalResultAnywayIfItIsNotStatEntry(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=export_test_lib.DataAgnosticConverterTestValue())

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    # Test that something gets exported and that this something wasn't
    # produced by ArtifactFilesDownloaderResultConverter.
    self.assertLen(converted, 1)
    self.assertFalse(
        isinstance(converted[0], export.ExportedArtifactFilesDownloaderResult))

  def testExportsOriginalResultIfOriginalResultIsNotRegistryOrFileStatEntry(
      self):
    stat = rdf_client_fs.StatEntry(
        pathspec=rdf_paths.PathSpec(
            path="some/path", pathtype=rdf_paths.PathSpec.PathType.TMPFILE))
    result = collectors.ArtifactFilesDownloaderResult(original_result=stat)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    # Test that something gets exported and that this something wasn't
    # produced by ArtifactFilesDownloaderResultConverter.
    self.assertLen(converted, 1)
    self.assertFalse(
        isinstance(converted[0], export.ExportedArtifactFilesDownloaderResult))

  def testYieldsOneResultAndOneOriginalValueForFileStatEntry(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.file_stat)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    default_exports = [
        v for v in converted
        if not isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(default_exports, 1)
    self.assertLen(default_exports, 1)

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].original_file.basename, "bar.exe")

  def testYieldsOneResultForRegistryStatEntryIfNoPathspecsWereFound(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].original_registry_key.type, "REG_SZ")
    self.assertEqual(downloader_exports[0].original_registry_key.data,
                     "C:\\Windows\\Sidebar.exe")

  def testIncludesRegistryStatEntryFoundPathspecIntoYieldedResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat,
        found_pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS"))

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].found_path, "foo")

  def testIncludesFileStatEntryFoundPathspecIntoYieldedResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.file_stat, found_pathspec=self.file_stat.pathspec)

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].found_path, "/tmp/bar.exe")

  def testIncludesDownloadedFileIntoResult(self):
    result = collectors.ArtifactFilesDownloaderResult(
        original_result=self.registry_stat,
        found_pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS"),
        downloaded_file=rdf_client_fs.StatEntry(
            pathspec=rdf_paths.PathSpec(path="foo", pathtype="OS")))

    converter = export.ArtifactFilesDownloaderResultConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    downloader_exports = [
        v for v in converted
        if isinstance(v, export.ExportedArtifactFilesDownloaderResult)
    ]
    self.assertLen(downloader_exports, 1)
    self.assertEqual(downloader_exports[0].downloaded_file.basename, "foo")


class YaraProcessScanResponseConverterTest(ExportTestBase):
  """Tests for YaraProcessScanResponseConverter."""

  def GenerateSample(self, match):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083)
    return rdf_yara.YaraProcessScanMatch(
        process=process, match=match, scan_time_us=42)

  def testExportsSingleMatchCorrectly(self):
    sample = self.GenerateSample([rdf_yara.YaraMatch(rule_name="foo")])

    converter = export.YaraProcessScanResponseConverter()
    converted = list(converter.Convert(self.metadata, sample, token=self.token))

    self.assertLen(converted, 1)

    self.assertEqual(converted[0].process.pid, 2)
    self.assertEqual(converted[0].process.ppid, 1)
    self.assertEqual(converted[0].process.cmdline, "cmd.exe")
    self.assertEqual(converted[0].process.exe, "c:\\windows\\cmd.exe")
    self.assertEqual(converted[0].process.ctime, 1333718907167083)

    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[0].scan_time_us, 42)

  def testExportsOneEntryForTheSameRuleMatchingSameProcessTwice(self):
    sample = self.GenerateSample([
        rdf_yara.YaraMatch(rule_name="foo"),
        rdf_yara.YaraMatch(rule_name="foo")
    ])

    converter = export.YaraProcessScanResponseConverter()
    converted = list(converter.Convert(self.metadata, sample, token=self.token))

    self.assertLen(converted, 1)

    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[0].scan_time_us, 42)

  def testExportsTwoEntriesForTwoRulesMatchingSameProcess(self):
    sample = self.GenerateSample([
        rdf_yara.YaraMatch(rule_name="foo"),
        rdf_yara.YaraMatch(rule_name="bar")
    ])

    converter = export.YaraProcessScanResponseConverter()
    converted = list(converter.Convert(self.metadata, sample, token=self.token))

    self.assertLen(converted, 2)

    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[1].rule_name, "bar")


class DataAgnosticExportConverterTest(ExportTestBase):
  """Tests for DataAgnosticExportConverter."""

  def ConvertOriginalValue(self, original_value):
    converted_values = list(export.DataAgnosticExportConverter().Convert(
        export.ExportedMetadata(source_urn=rdfvalue.RDFURN("aff4:/foo")),
        original_value))
    self.assertLen(converted_values, 1)
    return converted_values[0]

  def testAddsMetadataAndIgnoresRepeatedAndMessagesFields(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue()
    converted_value = self.ConvertOriginalValue(original_value)

    # No 'metadata' field in the original value.
    self.assertCountEqual([t.name for t in original_value.type_infos], [
        "string_value", "int_value", "bool_value", "repeated_string_value",
        "message_value", "enum_value", "another_enum_value", "urn_value",
        "datetime_value"
    ])
    # But there's one in the converted value.
    self.assertCountEqual([t.name for t in converted_value.type_infos], [
        "metadata", "string_value", "int_value", "bool_value", "enum_value",
        "another_enum_value", "urn_value", "datetime_value"
    ])

    # Metadata value is correctly initialized from user-supplied metadata.
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))

  def testIgnoresPredefinedMetadataField(self):
    original_value = export_test_lib.DataAgnosticConverterTestValueWithMetadata(
        metadata=42, value="value")
    converted_value = self.ConvertOriginalValue(original_value)

    self.assertCountEqual([t.name for t in converted_value.type_infos],
                          ["metadata", "value"])
    self.assertEqual(converted_value.metadata.source_urn,
                     rdfvalue.RDFURN("aff4:/foo"))
    self.assertEqual(converted_value.value, "value")

  def testProcessesPrimitiveTypesCorrectly(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        bool_value=True,
        enum_value=export_test_lib.DataAgnosticConverterTestValue.EnumOption
        .OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
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

    self.assertIsInstance(converted_value.urn_value, rdfvalue.RDFURN)
    self.assertEqual(converted_value.urn_value, rdfvalue.RDFURN("aff4:/bar"))

    self.assertTrue(
        isinstance(converted_value.datetime_value, rdfvalue.RDFDatetime))
    self.assertEqual(converted_value.datetime_value,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

  def testConvertedValuesCanBeSerializedAndDeserialized(self):
    original_value = export_test_lib.DataAgnosticConverterTestValue(
        string_value="string value",
        int_value=42,
        bool_value=True,
        enum_value=export_test_lib.DataAgnosticConverterTestValue.EnumOption
        .OPTION_2,
        urn_value=rdfvalue.RDFURN("aff4:/bar"),
        datetime_value=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
    converted_value = self.ConvertOriginalValue(original_value)

    serialized = converted_value.SerializeToString()
    deserialized = converted_value.__class__.FromSerializedString(serialized)

    self.assertEqual(converted_value, deserialized)


class DynamicRekallResponseConverterTest(ExportTestBase):

  def SendReply(self, response_msg):
    self.messages.append(response_msg)

  def _ResetState(self):
    self.messages = []
    data = """{
       "$INVENTORY": {},
       "$METADATA": {"ProfileClass":"Inventory", "Type":"Inventory"}
    }"""
    inventory = rdf_rekall_types.RekallProfile(
        name="inventory", data=data.encode("utf-8"), version="1", compression=0)

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

    self.assertLen(self.messages, 1)

    converted_values = list(
        self.converter.Convert(
            export.ExportedMetadata(source_urn="aff4:/foo/bar"),
            self.messages[0],
            token=self.token))

    self.assertLen(converted_values, 1)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar_sample")
    self.assertEqual(converted_values[0].Offset, "42")
    self.assertEqual(converted_values[0].Hex, "0x0")
    self.assertEqual(converted_values[0].Data, "data")

  def testCurrentSectionNameIsNotExportedWhenNotPresent(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(42, "0x0", "data")
    self.renderer.flush()

    converted_values = list(
        self.converter.Convert(
            export.ExportedMetadata(source_urn="aff4:/foo/bar"),
            self.messages[0],
            token=self.token))
    self.assertLen(converted_values, 1)
    self.assertFalse(converted_values[0].HasField("section_name"))

  def testCurrentSectionNameIsExportedWhenPresent(self):
    self.renderer.start(plugin_name="sample")
    self.renderer.section(name="some section")
    self.renderer.table_header([("Offset", "offset", ""), ("Hex", "hex", ""),
                                ("Data", "data", "")])

    self.renderer.table_row(42, "0x0", "data")
    self.renderer.flush()

    converted_values = list(
        self.converter.Convert(
            export.ExportedMetadata(source_urn="aff4:/foo/bar"),
            self.messages[0],
            token=self.token))
    self.assertLen(converted_values, 1)
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

    converted_values = list(
        self.converter.Convert(
            export.ExportedMetadata(source_urn="aff4:/foo/bar"),
            self.messages[0],
            token=self.token))
    self.assertLen(converted_values, 2)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar_sample")

    self.assertEqual(converted_values[0].Offset, "42")
    self.assertEqual(converted_values[0].Hex, "0x0")
    self.assertEqual(converted_values[0].Data, "data")

    self.assertEqual(converted_values[1].__class__.__name__,
                     "RekallExport_foo_bar_sample")
    self.assertEqual(converted_values[1].Offset, "43")
    self.assertEqual(converted_values[1].Hex, "0x1")
    self.assertEqual(converted_values[1].Data, "otherdata")

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

    converted_values = list(
        self.converter.Convert(
            export.ExportedMetadata(source_urn="aff4:/foo/bar"),
            self.messages[0],
            token=self.token))
    self.assertEqual(converted_values[0].section_name, "some section")
    self.assertEqual(converted_values[1].section_name, "some other section")

  def testObjectRenderersAreAppliedCorrectly(self):
    messages = [[
        "t",
        [{
            "cname": "Address"
        }, {
            "cname": "Pointer"
        }, {
            "cname": "PaddedAddress"
        }, {
            "cname": "AddressSpace"
        }, {
            "cname": "Enumeration"
        }, {
            "cname": "Literal"
        }, {
            "cname": "NativeType"
        }, {
            "cname": "NoneObject"
        }, {
            "cname": "BaseObject"
        }, {
            "cname": "Struct"
        }, {
            "cname": "UnixTimeStamp"
        }, {
            "cname": "_EPROCESS"
        }, {
            "cname": "int"
        }, {
            "cname": "str"
        }], {}
    ],
                [
                    "r",
                    {
                        "Address": {
                            "mro": ["Address"],
                            "value": 42
                        },
                        "Pointer": {
                            "mro": ["Pointer"],
                            "target": 43
                        },
                        "PaddedAddress": {
                            "mro": ["PaddedAddress"],
                            "value": 44
                        },
                        "AddressSpace": {
                            "mro": ["AddressSpace"],
                            "name": "some_address_space"
                        },
                        "Enumeration": {
                            "mro": ["Enumeration"],
                            "enum": "ENUM",
                            "value": 42
                        },
                        "Literal": {
                            "mro": ["Literal"],
                            "value": "some literal"
                        },
                        "NativeType": {
                            "mro": ["NativeType"],
                            "value": "some"
                        },
                        "NoneObject": {
                            "mro": ["NoneObject"]
                        },
                        "BaseObject": {
                            "mro": ["BaseObject"],
                            "offset": 42
                        },
                        "Struct": {
                            "mro": ["Struct"],
                            "offset": 42
                        },
                        "UnixTimeStamp": {
                            "mro": ["UnixTimeStamp"],
                            "epoch": 42
                        },
                        "_EPROCESS": {
                            "mro": ["_EPROCESS"],
                            "Cybox": {
                                "PID": 4,
                                "Name": "System"
                            }
                        },
                        "int": 42,
                        "str": "some string"
                    }
                ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="object_renderer_sample",
        json_messages=json.dumps(messages),
        json_context_messages=json.dumps([]))
    converted_values = list(
        self.converter.Convert(
            export.ExportedMetadata(source_urn="aff4:/foo/bar"),
            rekall_response,
            token=self.token))
    self.assertLen(converted_values, 1)
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
    self.assertLen(self.messages, 1)

    converted_values = list(
        self.converter.Convert(
            export.ExportedMetadata(source_urn="aff4:/foo/bar1"),
            self.messages[0],
            token=self.token))

    self.assertLen(converted_values, 1)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar1_sample")
    self.assertEqual(converted_values[0].a, "42")

    self._ResetState()

    self.renderer.start(plugin_name="sample")
    self.renderer.table_header([("b", "b", "")])
    self.renderer.table_row(43)
    self.renderer.flush()
    self.assertLen(self.messages, 1)

    converted_values = list(
        self.converter.Convert(
            # It's important for the source_urn to be different as we rely on
            # different source_urns to generate different class names.
            export.ExportedMetadata(source_urn="aff4:/foo/bar2"),
            self.messages[0],
            token=self.token))

    self.assertLen(converted_values, 1)
    self.assertEqual(converted_values[0].__class__.__name__,
                     "RekallExport_foo_bar2_sample")
    self.assertEqual(converted_values[0].b, "43")


class RekallResponseToExportedYaraSignatureMatchConverterTest(ExportTestBase):
  """Tests for RekallResponseToExportedRekallProcessConverter."""

  def setUp(self):
    super(RekallResponseToExportedYaraSignatureMatchConverterTest, self).setUp()
    self.converter = (
        export.RekallResponseToExportedYaraSignatureMatchConverter())

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
            "HexDump": {
                "highlights": None,
                "mro": "HexDumpedString:AttributedString:object",
                "id": 1435655,
                "value": "74657374737472696e67"
            },
            "Context": {
                "Process": {
                    "name": "Pointer",
                    "type_name": "_EPROCESS",
                    "vm": "WindowsAMD64PagedMemory",
                    "mro": "_EPROCESS:Struct:BaseAddressComparisonMixIn:"
                           "BaseObject:object",
                    "Cybox": {
                        "Parent_PID": 2080,
                        "Name": "python.exe",
                        "Creation_Time": {
                            "epoch": 1478513999,
                            "mro": "WinFileTime:UnixTimeStamp:NativeType:"
                                   "NumericProxyMixIn:BaseObject:object",
                            "string_value": "2016-11-07 10:19:59Z",
                            "id": 1435802
                        },
                        "PID": 8108,
                        "Image_Info": {
                            "File_Name":
                                r"\\Device\\HarddiskVolume4\\python_27_amd64"
                                r"\\files\\python.exe",
                            "Path":
                                r"C:\\python_27_amd64\\files\\python.exe",
                            "type":
                                "ProcessObj:ImageInfoType",
                            "Command_Line":
                                "python  yaratest.py",
                            "TrustedPath":
                                r"C:\\python_27_amd64\\files\\python.exe"
                        },
                        "type": "ProcessObj:ProcessObjectType"
                    },
                    "offset": 246298002579584,
                    "id": 1435800
                },
                "mro": "PhysicalAddressContext:object",
                "phys_offset": 15702315008
            },
            "Rule": "SOME_yara_rule",
            "Offset": 42
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="handles", json_messages=json.dumps(messages))
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))

    self.assertLen(converted_values, 1)

    model_process = export.ExportedRekallProcess(
        commandline="python  yaratest.py",
        creation_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1478513999),
        fullpath=r"C:\\python_27_amd64\\files\\python.exe",
        name="python.exe",
        parent_pid=2080,
        pid=8108,
        trusted_fullpath=r"C:\\python_27_amd64\\files\\python.exe")
    model = export.ExportedYaraSignatureMatch(
        metadata=metadata,
        process=model_process,
        rule="SOME_yara_rule",
        hex_dump="74657374737472696e67")

    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="handles", json_messages=json.dumps(messages))
    converted_values = list(
        self.converter.Convert(
            self.metadata, rekall_response, token=self.token))

    self.assertEmpty(converted_values)


class RekallResponseToExportedRekallProcessConverterTest(ExportTestBase):
  """Tests for RekallResponseToExportedRekallProcessConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallProcessConverterTest, self).setUp()
    self.converter = export.RekallResponseToExportedRekallProcessConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
            "_EPROCESS": {
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
            },
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="handles", json_messages=json.dumps(messages))
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))

    self.assertLen(converted_values, 1)

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
    converted_values = list(
        self.converter.Convert(
            self.metadata, rekall_response, token=self.token))

    self.assertEmpty(converted_values)


class RekallResponseToExportedRekallWindowsLoadedModuleConverterTest(
    ExportTestBase):
  """Tests for RekallResponseToExportedRekallProcessConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallWindowsLoadedModuleConverterTest,
          self).setUp()
    # pyformat: disable
    self.converter = export.RekallResponseToExportedRekallWindowsLoadedModuleConverter()  # pylint: disable=line-too-long
    # pyformat: enable

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
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
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))

    self.assertLen(converted_values, 1)

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
    converted_values = list(
        self.converter.Convert(
            self.metadata, rekall_response, token=self.token))

    self.assertEmpty(converted_values)


class ExportedLinuxSyscallTableEntryConverterTest(ExportTestBase):
  """Tests for ExportedLinuxSyscallTableEntryConverter."""

  def setUp(self):
    super(ExportedLinuxSyscallTableEntryConverterTest, self).setUp()
    self.converter = export.ExportedLinuxSyscallTableEntryConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
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
        plugin="check_syscall", json_messages=json.dumps(messages))
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))

    self.assertLen(converted_values, 1)

    model = export.ExportedLinuxSyscallTableEntry(
        metadata=metadata,
        table="ia32_sys_call_table",
        index=198,
        handler_address=281472847827136,
        symbol="linux!SyS_lchown")
    self.assertEqual(list(converted_values)[0], model)

  def testConvertsSyscallEntriesWithMultipleSymbolNames(self):
    messages = [[
        "r",
        {
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
        plugin="check_syscall", json_messages=json.dumps(messages))
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))
    self.assertLen(converted_values, 2)

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
        plugin="check_task_fops", json_messages=json.dumps(messages))
    converted_values = list(
        self.converter.Convert(
            self.metadata, rekall_response, token=self.token))
    self.assertEmpty(converted_values)


class RekallResponseToExportedRekallLinuxTaskOpConverterTest(ExportTestBase):
  """Tests for RekallResponseToExportedRekallLinuxTaskOpConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallLinuxTaskOpConverterTest, self).setUp()
    self.converter = export.RekallResponseToExportedRekallLinuxTaskOpConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
            u"address": {
                u"id":
                    12331,
                u"mro":
                    u"Function:BaseAddressComparisonMixIn:BaseObject:object",
                u"name":
                    u"write",
                u"offset":
                    281472847829584,
                u"type_name":
                    u"Function",
                u"vm":
                    u"AMD64PagedMemory"
            },
            u"comm": u"init",
            u"highlight": None,
            u"member": u"write",
            u"module": u"linux",
            u"pid": 1
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_task_fops", json_messages=json.dumps(messages))
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))

    self.assertLen(converted_values, 1)

    task = export.ExportedRekallLinuxTask(metadata=metadata, pid=1, name="init")

    model = export.ExportedRekallLinuxTaskOp(
        metadata=metadata,
        operation="write",
        handler_address=281472847829584,
        module="linux",
        task=task)
    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_task_fops", json_messages=json.dumps(messages))
    converted_values = list(
        self.converter.Convert(
            self.metadata, rekall_response, token=self.token))
    self.assertEmpty(converted_values)


class RekallResponseToExportedRekallLinuxProcOpConverterTest(ExportTestBase):
  """Tests for RekallResponseToExportedRekallLinuxProcOpConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallLinuxProcOpConverterTest, self).setUp()
    self.converter = export.RekallResponseToExportedRekallLinuxProcOpConverter()

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
            u"address": {
                u"id":
                    11447,
                u"mro":
                    u"Function:BaseAddressComparisonMixIn:BaseObject:object",
                u"name":
                    u"read",
                u"offset":
                    281472847976656,
                u"type_name":
                    u"Function",
                u"vm":
                    u"AMD64PagedMemory"
            },
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
                u"vm": u"AMD64PagedMemory"
            }
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_proc_fops", json_messages=json.dumps(messages))
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))

    self.assertLen(converted_values, 1)

    model = export.ExportedRekallLinuxProcOp(
        metadata=metadata,
        operation="read",
        handler_address=281472847976656,
        module="linux",
        fullpath="/proc/fb")
    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="check_task_fops", json_messages=json.dumps(messages))
    converted_values = list(
        self.converter.Convert(
            self.metadata, rekall_response, token=self.token))
    self.assertEmpty(converted_values)


class RekallResponseToExportedRekallKernelObjectConverterTest(ExportTestBase):
  """Tests for RekallResponseToExportedRekallKernelObjectConverter."""

  def setUp(self):
    super(RekallResponseToExportedRekallKernelObjectConverterTest, self).setUp()
    self.converter = export.RekallResponseToExportedRekallKernelObjectConverter(
    )

  def testConvertsCompatibleMessage(self):
    messages = [[
        "r",
        {
            u"type": u"Directory",
            "_OBJECT_HEADER": {
                u"name": u"_OBJECT_HEADER",
                u"type_name": u"_OBJECT_HEADER",
                u"vm": u"WindowsAMD64PagedMemory",
            },
            u"name": u"ObjectTypes"
        }
    ]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="object_tree", json_messages=json.dumps(messages))
    metadata = self.metadata
    converted_values = list(
        self.converter.Convert(metadata, rekall_response, token=self.token))

    self.assertLen(converted_values, 1)

    model = export.ExportedRekallKernelObject(
        metadata=metadata, type="Directory", name="ObjectTypes")
    self.assertEqual(converted_values[0], model)

  def testIgnoresIncompatibleMessage(self):
    messages = [["r", {"baseaddress": 0}]]

    rekall_response = rdf_rekall_types.RekallResponse(
        plugin="object_tree", json_messages=json.dumps(messages))
    converted_values = list(
        self.converter.Convert(
            self.metadata, rekall_response, token=self.token))
    self.assertEmpty(converted_values)


class GetMetadataLegacyTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(GetMetadataLegacyTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def testGetMetadataLegacy(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    with aff4.FACTORY.Open(
        self.client_id, mode="rw", token=self.token) as client:
      client.SetLabel("client-label-24")

    metadata = export.GetMetadataLegacy(self.client_id, token=self.token)
    self.assertEqual(metadata.os, "Windows")
    self.assertEqual(metadata.labels, "client-label-24")
    self.assertEqual(metadata.user_labels, "client-label-24")
    self.assertEqual(metadata.system_labels, "")
    self.assertEqual(metadata.hardware_info.bios_version, "Version 1.23v")

    with aff4.FACTORY.Open(
        self.client_id, mode="rw", token=self.token) as client:
      client.SetLabels(["a", "b"])

    metadata = export.GetMetadataLegacy(self.client_id, token=self.token)
    self.assertEqual(metadata.os, "Windows")
    self.assertEqual(metadata.labels, "a,b")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "")

  def testGetMetadataLegacyWithSystemLabels(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    with aff4.FACTORY.Open(
        self.client_id, mode="rw", token=self.token) as client:
      client.SetLabels(["a", "b"])
      client.AddLabel("c", owner="GRR")

    metadata = export.GetMetadataLegacy(self.client_id, token=self.token)
    self.assertEqual(metadata.labels, "a,b,c")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "c")

  def testGetMetadataLegacyMissingKB(self):
    # We do not want to use `self.client_id` in this test because we need an
    # uninitialized client.
    client_id = rdf_client.ClientURN("C.4815162342108108")

    newclient = aff4.FACTORY.Create(
        client_id, aff4_grr.VFSGRRClient, token=self.token, mode="rw")
    self.assertFalse(newclient.Get(newclient.Schema.KNOWLEDGE_BASE))
    newclient.Flush()

    # Expect empty usernames field due to no knowledge base.
    metadata = export.GetMetadataLegacy(client_id, token=self.token)
    self.assertFalse(metadata.usernames)


class GetMetadataTest(db_test_lib.RelationalDBEnabledMixin,
                      test_lib.GRRBaseTest):

  def setUp(self):
    super(GetMetadataTest, self).setUp()
    self.client_id = "C.4815162342108107"

  def testGetMetadataWithSingleUserLabel(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    self.AddClientLabel(self.client_id, self.token.username, "client-label-24")

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.os, "Windows")
    self.assertEqual(metadata.labels, "client-label-24")
    self.assertEqual(metadata.user_labels, "client-label-24")
    self.assertEqual(metadata.system_labels, "")
    self.assertEqual(metadata.hardware_info.bios_version, "Version 1.23v")

  def testGetMetadataWithTwoUserLabels(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    self.AddClientLabel(self.client_id, self.token.username, "a")
    self.AddClientLabel(self.client_id, self.token.username, "b")

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.os, "Windows")
    self.assertEqual(metadata.labels, "a,b")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "")

  def testGetMetadataWithSystemLabels(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    self.AddClientLabel(self.client_id, self.token.username, "a")
    self.AddClientLabel(self.client_id, self.token.username, "b")
    self.AddClientLabel(self.client_id, "GRR", "c")

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.labels, "a,b,c")
    self.assertEqual(metadata.user_labels, "a,b")
    self.assertEqual(metadata.system_labels, "c")

  def testGetMetadataMissingKB(self):
    # We do not want to use `self.client_id` in this test because we need an
    # uninitialized client.
    client_id = "C.4815162342108108"
    data_store.REL_DB.WriteClientMetadata(
        client_id, first_seen=rdfvalue.RDFDatetime(42))

    # Expect empty usernames field due to no knowledge base.
    metadata = export.GetMetadata(
        client_id, data_store.REL_DB.ReadClientFullInfo(client_id))
    self.assertFalse(metadata.usernames)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
