#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import process
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class ProcessToExportedProcessConverter(export_test_lib.ExportTestBase):

  def testBasicConversion(self):
    proc = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
    )

    converter = process.ProcessToExportedProcessConverter()
    results = list(converter.Convert(self.metadata, proc))

    self.assertLen(results, 1)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].ppid, 1)
    self.assertEqual(results[0].cmdline, "cmd.exe")
    self.assertEqual(results[0].exe, "c:\\windows\\cmd.exe")
    self.assertEqual(results[0].ctime, 1333718907167083)


class ProcessToExportedProcessConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testBasicConversion(self):
    proc = sysinfo_pb2.Process(
        pid=2,
        ppid=1,
        name="cmd.exe",
        cmdline=["cmd.exe", "/c", "echo"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        real_uid=111,
        effective_uid=222,
        saved_uid=333,
        real_gid=444,
        effective_gid=555,
        saved_gid=666,
        username="user",
        terminal="pts/0",
        status="RUNNING",
        nice=20,
        cwd="C:\\Users\\User",
        num_threads=1,
        user_cpu_time=7.0,
        system_cpu_time=8.0,
        RSS_size=999,
        VMS_size=987,
        memory_percent=9.0,
    )

    converter = process.ProcessToExportedProcessConverterProto()
    results = list(converter.Convert(self.metadata_proto, proc))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedProcess)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].ppid, 1)
    self.assertEqual(results[0].name, "cmd.exe")
    self.assertEqual(results[0].cmdline, "cmd.exe /c echo")
    self.assertEqual(results[0].exe, "c:\\windows\\cmd.exe")
    self.assertEqual(results[0].ctime, 1333718907167083)
    self.assertEqual(results[0].real_uid, 111)
    self.assertEqual(results[0].effective_uid, 222)
    self.assertEqual(results[0].saved_uid, 333)
    self.assertEqual(results[0].real_gid, 444)
    self.assertEqual(results[0].effective_gid, 555)
    self.assertEqual(results[0].saved_gid, 666)
    self.assertEqual(results[0].username, "user")
    self.assertEqual(results[0].terminal, "pts/0")
    self.assertEqual(results[0].status, "RUNNING")
    self.assertEqual(results[0].nice, 20)
    self.assertEqual(results[0].cwd, "C:\\Users\\User")
    self.assertEqual(results[0].num_threads, 1)
    self.assertEqual(results[0].user_cpu_time, 7.0)
    self.assertEqual(results[0].system_cpu_time, 8.0)
    self.assertEqual(results[0].rss_size, 999)
    self.assertEqual(results[0].vms_size, 987)
    self.assertEqual(results[0].memory_percent, 9.0)


class ProcessToExportedOpenFileConverterTest(export_test_lib.ExportTestBase):

  def testBasicConversion(self):
    proc = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        open_files=["/some/a", "/some/b"],
    )

    converter = process.ProcessToExportedOpenFileConverter()
    results = list(converter.Convert(self.metadata, proc))

    self.assertLen(results, 2)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].path, "/some/a")
    self.assertEqual(results[1].pid, 2)
    self.assertEqual(results[1].path, "/some/b")


class ProcessToExportedOpenFileConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testBasicConversion(self):
    proc = sysinfo_pb2.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        open_files=["/some/a", "/some/b"],
    )

    converter = process.ProcessToExportedOpenFileConverterProto()
    results = list(converter.Convert(self.metadata_proto, proc))

    self.assertLen(results, 2)
    self.assertIsInstance(results[0], export_pb2.ExportedOpenFile)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].path, "/some/a")
    self.assertIsInstance(results[1], export_pb2.ExportedOpenFile)
    self.assertEqual(results[1].pid, 2)
    self.assertEqual(results[1].path, "/some/b")


class ProcessToExportedNetworkConnectionConverterTest(
    export_test_lib.ExportTestBase
):

  def testBasicConversion(self):
    conn1 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.LISTEN,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=0),
        pid=2136,
        ctime=0,
    )
    conn2 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.LISTEN,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(
            ip="192.168.1.1", port=31337
        ),
        remote_address=rdf_client_network.NetworkEndpoint(
            ip="1.2.3.4", port=6667
        ),
        pid=1,
        ctime=0,
    )

    proc = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        connections=[conn1, conn2],
    )

    converter = process.ProcessToExportedNetworkConnectionConverter()
    results = list(converter.Convert(self.metadata, proc))

    self.assertLen(results, 2)
    self.assertEqual(
        results[0].state, rdf_client_network.NetworkConnection.State.LISTEN
    )
    self.assertEqual(
        results[0].type, rdf_client_network.NetworkConnection.Type.SOCK_STREAM
    )
    self.assertEqual(results[0].local_address.ip, "0.0.0.0")
    self.assertEqual(results[0].local_address.port, 22)
    self.assertEqual(results[0].remote_address.ip, "0.0.0.0")
    self.assertEqual(results[0].remote_address.port, 0)
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 0)

    self.assertEqual(
        results[1].state, rdf_client_network.NetworkConnection.State.LISTEN
    )
    self.assertEqual(
        results[1].type, rdf_client_network.NetworkConnection.Type.SOCK_STREAM
    )
    self.assertEqual(results[1].local_address.ip, "192.168.1.1")
    self.assertEqual(results[1].local_address.port, 31337)
    self.assertEqual(results[1].remote_address.ip, "1.2.3.4")
    self.assertEqual(results[1].remote_address.port, 6667)
    self.assertEqual(results[1].pid, 1)
    self.assertEqual(results[1].ctime, 0)


class ProcessToExportedNetworkConnectionConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testBasicConversion(self):
    conn1 = sysinfo_pb2.NetworkConnection(
        state=sysinfo_pb2.NetworkConnection.State.LISTEN,
        type=sysinfo_pb2.NetworkConnection.Type.SOCK_STREAM,
        local_address=sysinfo_pb2.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=sysinfo_pb2.NetworkEndpoint(ip="0.0.0.0", port=0),
        pid=2136,
        ctime=0,
    )
    conn2 = sysinfo_pb2.NetworkConnection(
        state=sysinfo_pb2.NetworkConnection.State.ESTABLISHED,
        type=sysinfo_pb2.NetworkConnection.Type.SOCK_DGRAM,
        local_address=sysinfo_pb2.NetworkEndpoint(ip="192.168.1.1", port=31337),
        remote_address=sysinfo_pb2.NetworkEndpoint(ip="1.2.3.4", port=6667),
        pid=1,
        ctime=0,
    )

    proc = sysinfo_pb2.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        connections=[conn1, conn2],
    )

    converter = process.ProcessToExportedNetworkConnectionConverterProto()
    results = list(converter.Convert(self.metadata_proto, proc))

    self.assertLen(results, 2)
    self.assertIsInstance(results[0], export_pb2.ExportedNetworkConnection)
    self.assertEqual(
        results[0].state, sysinfo_pb2.NetworkConnection.State.LISTEN
    )
    self.assertEqual(
        results[0].type, sysinfo_pb2.NetworkConnection.Type.SOCK_STREAM
    )
    self.assertEqual(results[0].local_address.ip, "0.0.0.0")
    self.assertEqual(results[0].local_address.port, 22)
    self.assertEqual(results[0].remote_address.ip, "0.0.0.0")
    self.assertEqual(results[0].remote_address.port, 0)
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 0)

    self.assertIsInstance(results[1], export_pb2.ExportedNetworkConnection)
    self.assertEqual(
        results[1].state, sysinfo_pb2.NetworkConnection.State.ESTABLISHED
    )
    self.assertEqual(
        results[1].type, sysinfo_pb2.NetworkConnection.Type.SOCK_DGRAM
    )
    self.assertEqual(results[1].local_address.ip, "192.168.1.1")
    self.assertEqual(results[1].local_address.port, 31337)
    self.assertEqual(results[1].remote_address.ip, "1.2.3.4")
    self.assertEqual(results[1].remote_address.port, 6667)
    self.assertEqual(results[1].pid, 1)
    self.assertEqual(results[1].ctime, 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
