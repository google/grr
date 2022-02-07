#!/usr/bin/env python
from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
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
        ctime=1333718907167083)

    converter = process.ProcessToExportedProcessConverter()
    results = list(converter.Convert(self.metadata, proc))

    self.assertLen(results, 1)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].ppid, 1)
    self.assertEqual(results[0].cmdline, "cmd.exe")
    self.assertEqual(results[0].exe, "c:\\windows\\cmd.exe")
    self.assertEqual(results[0].ctime, 1333718907167083)


class ProcessToExportedOpenFileConverterTest(export_test_lib.ExportTestBase):

  def testBasicConversion(self):
    proc = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        open_files=["/some/a", "/some/b"])

    converter = process.ProcessToExportedOpenFileConverter()
    results = list(converter.Convert(self.metadata, proc))

    self.assertLen(results, 2)
    self.assertEqual(results[0].pid, 2)
    self.assertEqual(results[0].path, "/some/a")
    self.assertEqual(results[1].pid, 2)
    self.assertEqual(results[1].path, "/some/b")


class ProcessToExportedNetworkConnectionConverterTest(
    export_test_lib.ExportTestBase):

  def testBasicConversion(self):
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

    proc = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        connections=[conn1, conn2])

    converter = process.ProcessToExportedNetworkConnectionConverter()
    results = list(converter.Convert(self.metadata, proc))

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


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
