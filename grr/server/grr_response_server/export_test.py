#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for export converters."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import socket

from absl import app
from absl.testing import absltest
from future.builtins import str

from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import osquery as rdf_osquery
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import export
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import filestore
from grr_response_server.check_lib import checks
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
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
  input_rdf_type = DummyRDFValue

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [rdfvalue.RDFString(str(value))]


class DummyRDFValue3ConverterA(export.ExportConverter):
  input_rdf_type = DummyRDFValue3

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    return [DummyRDFValue(str(value) + "A")]


class DummyRDFValue3ConverterB(export.ExportConverter):
  input_rdf_type = DummyRDFValue3

  def Convert(self, metadata, value, token=None):
    _ = metadata
    _ = token
    if not isinstance(value, DummyRDFValue3):
      raise ValueError("Called with the wrong type")
    return [DummyRDFValue2(str(value) + "B")]


class DummyRDFValue4ToMetadataConverter(export.ExportConverter):
  input_rdf_type = DummyRDFValue4

  def Convert(self, metadata, value, token=None):
    _ = value
    _ = token
    return [metadata]


class DummyRDFValue5Converter(export.ExportConverter):
  input_rdf_type = DummyRDFValue5

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

    if data_store.RelationalDBEnabled():
      path_info = data_store.REL_DB.ReadPathInfo(
          self.client_id.Basename(),
          rdf_objects.PathInfo.PathType.TSK,
          components=tuple(pathspec.CollapsePath().lstrip("/").split("/")))
      stat = path_info.stat_entry
    else:
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

    if data_store.RelationalDBEnabled():
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
    self.assertEqual(results[0].data, b"Sidebar.exe")

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
    if data_store.RelationalDBEnabled():
      self.skipTest("This converter is used with AFF4 only.")

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

  def testFileFinderResultExportConverterConvertsContent(self):
    client_mock = action_mocks.FileFinderClientMockWithTimestamps()

    action = rdf_file_finder.FileFinderAction(
        action_type=rdf_file_finder.FileFinderAction.Action.DOWNLOAD)

    path = os.path.join(self.base_path, "winexec_img.dd")
    flow_id = flow_test_lib.TestFlowHelper(
        file_finder.FileFinder.__name__,
        client_mock,
        client_id=self.client_id,
        paths=[path],
        pathtype=rdf_paths.PathSpec.PathType.OS,
        action=action,
        token=self.token)

    flow_results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(flow_results, 1)

    converter = export.FileFinderResultConverter()
    results = list(
        converter.Convert(self.metadata, flow_results[0], token=self.token))

    self.assertLen(results, 1)

    self.assertEqual(results[0].basename, "winexec_img.dd")

    # Check that by default file contents are not exported
    self.assertFalse(results[0].content)
    self.assertFalse(results[0].content_sha256)

    # Convert again, now specifying export_files_contents=True in options.
    converter = export.FileFinderResultConverter(
        options=export.ExportOptions(export_files_contents=True))
    results = list(
        converter.Convert(self.metadata, flow_results[0], token=self.token))
    self.assertTrue(results[0].content)

    self.assertEqual(
        results[0].content_sha256,
        "0652da33d5602c165396856540c173cd37277916fba07a9bf3080bc5a6236f03")

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
        self.assertEqual(converted.data, str(data))

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
                     b"C:\\Windows\\Sidebar.exe")

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


class SoftwarePackageConverterTest(ExportTestBase):

  def testConvertsCorrectly(self):
    result = rdf_client.SoftwarePackage(
        name="foo",
        version="ver1",
        architecture="i386",
        publisher="somebody",
        install_state=rdf_client.SoftwarePackage.InstallState.PENDING,
        description="desc",
        installed_on=42,
        installed_by="user")

    converter = export.SoftwarePackageConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    self.assertLen(converted, 1)
    self.assertEqual(
        converted[0],
        export.ExportedSoftwarePackage(
            metadata=self.metadata,
            name="foo",
            version="ver1",
            architecture="i386",
            publisher="somebody",
            install_state=export.ExportedSoftwarePackage.InstallState.PENDING,
            description="desc",
            installed_on=42,
            installed_by="user"))


class SoftwarePackagesConverterTest(ExportTestBase):

  def testConvertsCorrectly(self):
    result = rdf_client.SoftwarePackages()
    for i in range(10):
      result.packages.append(
          rdf_client.SoftwarePackage(
              name="foo_%d" % i,
              version="ver_%d" % i,
              architecture="i386_%d" % i,
              publisher="somebody_%d" % i,
              install_state=rdf_client.SoftwarePackage.InstallState.PENDING,
              description="desc_%d" % i,
              installed_on=42 + i,
              installed_by="user_%d" % i))

    converter = export.SoftwarePackagesConverter()
    converted = list(converter.Convert(self.metadata, result, token=self.token))

    self.assertLen(converted, 10)
    for i, r in enumerate(converted):
      self.assertEqual(
          r,
          export.ExportedSoftwarePackage(
              metadata=self.metadata,
              name="foo_%d" % i,
              version="ver_%d" % i,
              architecture="i386_%d" % i,
              publisher="somebody_%d" % i,
              install_state=export.ExportedSoftwarePackage.InstallState.PENDING,
              description="desc_%d" % i,
              installed_on=42 + i,
              installed_by="user_%d" % i))


class YaraProcessScanResponseConverterTest(ExportTestBase):
  """Tests for YaraProcessScanResponseConverter."""

  def GenerateSample(self, match):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083)
    return rdf_memory.YaraProcessScanMatch(
        process=process, match=match, scan_time_us=42)

  def testExportsSingleMatchCorrectly(self):
    sample = self.GenerateSample([rdf_memory.YaraMatch(rule_name="foo")])

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
        rdf_memory.YaraMatch(rule_name="foo"),
        rdf_memory.YaraMatch(rule_name="foo")
    ])

    converter = export.YaraProcessScanResponseConverter()
    converted = list(converter.Convert(self.metadata, sample, token=self.token))

    self.assertLen(converted, 1)

    self.assertEqual(converted[0].rule_name, "foo")
    self.assertEqual(converted[0].scan_time_us, 42)

  def testExportsTwoEntriesForTwoRulesMatchingSameProcess(self):
    sample = self.GenerateSample([
        rdf_memory.YaraMatch(rule_name="foo"),
        rdf_memory.YaraMatch(rule_name="bar")
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


class OsqueryExportConverterTest(absltest.TestCase):

  def setUp(self):
    super(OsqueryExportConverterTest, self).setUp()
    self.converter = export.OsqueryExportConverter()
    self.metadata = export.ExportedMetadata(client_urn="C.48515162342ABCDE")

  def _Convert(self, table):
    return list(self.converter.Convert(self.metadata, table))

  def testNoRows(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT bar, baz FROM foo;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="baz"))

    self.assertEqual(self._Convert(table), [])

  def testSomeRows(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT foo, bar, quux FROM norf;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="bar"))
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="quux"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["thud", "🐺", "42"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["plugh", "🦊", "108"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["blargh", "🦍", "1337"]))

    results = self._Convert(table)
    self.assertLen(results, 3)
    self.assertEqual(results[0].metadata, self.metadata)
    self.assertEqual(results[0].foo, "thud")
    self.assertEqual(results[0].bar, "🐺")
    self.assertEqual(results[0].quux, "42")
    self.assertEqual(results[1].metadata, self.metadata)
    self.assertEqual(results[1].foo, "plugh")
    self.assertEqual(results[1].bar, "🦊")
    self.assertEqual(results[1].quux, "108")
    self.assertEqual(results[2].metadata, self.metadata)
    self.assertEqual(results[2].foo, "blargh")
    self.assertEqual(results[2].bar, "🦍")
    self.assertEqual(results[2].quux, "1337")

  def testMetadataColumn(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "SELECT metadata FROM foo;"
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="metadata"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["bar"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["baz"]))

    results = self._Convert(table)
    self.assertLen(results, 2)
    self.assertEqual(results[0].metadata, self.metadata)
    self.assertEqual(results[0].__metadata__, "bar")
    self.assertEqual(results[1].metadata, self.metadata)
    self.assertEqual(results[1].__metadata__, "baz")

  def testQueryMetadata(self):
    table = rdf_osquery.OsqueryTable()
    table.query = "   SELECT foo FROM quux;          "
    table.header.columns.append(rdf_osquery.OsqueryColumn(name="foo"))
    table.rows.append(rdf_osquery.OsqueryRow(values=["norf"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["thud"]))
    table.rows.append(rdf_osquery.OsqueryRow(values=["blargh"]))

    results = self._Convert(table)
    self.assertLen(results, 3)
    self.assertEqual(results[0].__query__, "SELECT foo FROM quux;")
    self.assertEqual(results[0].foo, "norf")
    self.assertEqual(results[1].__query__, "SELECT foo FROM quux;")
    self.assertEqual(results[1].foo, "thud")
    self.assertEqual(results[2].__query__, "SELECT foo FROM quux;")
    self.assertEqual(results[2].foo, "blargh")


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

  def testGetMetadataWithoutCloudInstanceSet(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertFalse(metadata.HasField("cloud_instance_type"))
    self.assertFalse(metadata.HasField("cloud_instance_id"))

  def testGetMetadataWithGoogleCloudInstanceID(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    snapshot = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    snapshot.cloud_instance = rdf_cloud.CloudInstance(
        cloud_type=rdf_cloud.CloudInstance.InstanceType.GOOGLE,
        google=rdf_cloud.GoogleCloudInstance(unique_id="foo/bar"))
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.cloud_instance_type,
                     metadata.CloudInstanceType.GOOGLE)
    self.assertEqual(metadata.cloud_instance_id, "foo/bar")

  def testGetMetadataWithAmazonCloudInstanceID(self):
    fixture_test_lib.ClientFixture(self.client_id, token=self.token)
    snapshot = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    snapshot.cloud_instance = rdf_cloud.CloudInstance(
        cloud_type=rdf_cloud.CloudInstance.InstanceType.AMAZON,
        amazon=rdf_cloud.AmazonCloudInstance(instance_id="foo/bar"))
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    metadata = export.GetMetadata(
        self.client_id, data_store.REL_DB.ReadClientFullInfo(self.client_id))
    self.assertEqual(metadata.cloud_instance_type,
                     metadata.CloudInstanceType.AMAZON)
    self.assertEqual(metadata.cloud_instance_id, "foo/bar")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
