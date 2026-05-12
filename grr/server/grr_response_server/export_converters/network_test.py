#!/usr/bin/env python
import socket

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import text
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import network
from grr.test_lib import test_lib


class NetworkConnectionToExportedNetworkConnectionConverterProtoTest(
    absltest.TestCase
):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testBasicConversion(self):
    conn = sysinfo_pb2.NetworkConnection(
        family=sysinfo_pb2.NetworkConnection.Family.INET6,
        type=sysinfo_pb2.NetworkConnection.Type.SOCK_STREAM,
        state=sysinfo_pb2.NetworkConnection.State.LISTEN,
        local_address=sysinfo_pb2.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=sysinfo_pb2.NetworkEndpoint(ip="0.0.0.1", port=33),
        pid=2136,
        ctime=123,
    )

    converter = (
        network.NetworkConnectionToExportedNetworkConnectionConverterProto()
    )
    results = list(converter.Convert(self.metadata_proto, conn))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedNetworkConnection)
    self.assertEqual(
        results[0].family, sysinfo_pb2.NetworkConnection.Family.INET6
    )
    self.assertEqual(
        results[0].state, sysinfo_pb2.NetworkConnection.State.LISTEN
    )
    self.assertEqual(
        results[0].type, sysinfo_pb2.NetworkConnection.Type.SOCK_STREAM
    )
    self.assertEqual(results[0].local_address.ip, "0.0.0.0")
    self.assertEqual(results[0].local_address.port, 22)
    self.assertEqual(results[0].remote_address.ip, "0.0.0.1")
    self.assertEqual(results[0].remote_address.port, 33)
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 123)


class InterfaceToExportedNetworkInterfaceConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testInterfaceToExportedNetworkInterfaceConverter(self):
    mac_address_bytes = b"123456"
    mac_address = text.Hexify(mac_address_bytes)

    interface = jobs_pb2.Interface(
        mac_address=mac_address_bytes,
        ifname="eth0",
        addresses=[
            jobs_pb2.NetworkAddress(
                address_type=jobs_pb2.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "127.0.0.1"),
            ),
            jobs_pb2.NetworkAddress(
                address_type=jobs_pb2.NetworkAddress.Family.INET,
                packed_bytes=socket.inet_pton(socket.AF_INET, "10.0.0.1"),
            ),
            jobs_pb2.NetworkAddress(
                address_type=jobs_pb2.NetworkAddress.Family.INET6,
                packed_bytes=socket.inet_pton(
                    socket.AF_INET6, "2001:720:1500:1::a100"
                ),
            ),
        ],
    )

    converter = network.InterfaceToExportedNetworkInterfaceConverterProto()
    results = list(converter.Convert(self.metadata_proto, interface))
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedNetworkInterface)
    self.assertEqual(results[0].mac_address, mac_address)
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")


class DNSClientConfigurationToExportedDNSClientConfigurationProtoTest(
    absltest.TestCase
):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testDNSClientConfigurationToExportedDNSClientConfiguration(self):
    dns_servers = ["192.168.1.1", "8.8.8.8"]
    dns_suffixes = ["internal.company.com", "company.com"]
    config = sysinfo_pb2.DNSClientConfiguration(
        dns_server=dns_servers, dns_suffix=dns_suffixes
    )

    converter = (
        network.DNSClientConfigurationToExportedDNSClientConfigurationProto()
    )
    results = list(converter.Convert(self.metadata_proto, config))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], export_pb2.ExportedDNSClientConfiguration)
    self.assertEqual(results[0].dns_servers, " ".join(dns_servers))
    self.assertEqual(results[0].dns_suffixes, " ".join(dns_suffixes))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
