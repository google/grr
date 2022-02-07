#!/usr/bin/env python
import socket

from absl import app

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.util import text
from grr_response_server.export_converters import network
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class NetworkConnectionToExportedNetworkConnectionConverterTest(
    export_test_lib.ExportTestBase):

  def testBasicConversion(self):
    conn = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.LISTEN,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=0),
        pid=2136,
        ctime=123)

    converter = network.NetworkConnectionToExportedNetworkConnectionConverter()
    results = list(converter.Convert(self.metadata, conn))

    self.assertLen(results, 1)
    self.assertEqual(results[0].state,
                     rdf_client_network.NetworkConnection.State.LISTEN)
    self.assertEqual(results[0].type,
                     rdf_client_network.NetworkConnection.Type.SOCK_STREAM)
    self.assertEqual(results[0].local_address,
                     rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=22))
    self.assertEqual(results[0].remote_address,
                     rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=0))
    self.assertEqual(results[0].pid, 2136)
    self.assertEqual(results[0].ctime, 123)


class InterfaceToExportedNetworkInterfaceConverterTest(
    export_test_lib.ExportTestBase):

  def testInterfaceToExportedNetworkInterfaceConverter(self):
    mac_address_bytes = b"123456"
    mac_address = text.Hexify(mac_address_bytes)

    interface = rdf_client_network.Interface(
        mac_address=mac_address_bytes,
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

    converter = network.InterfaceToExportedNetworkInterfaceConverter()
    results = list(converter.Convert(self.metadata, interface))
    self.assertLen(results, 1)
    self.assertEqual(results[0].mac_address, mac_address)
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")


class DNSClientConfigurationToExportedDNSClientConfigurationTest(
    export_test_lib.ExportTestBase):

  def testDNSClientConfigurationToExportedDNSClientConfiguration(self):
    dns_servers = ["192.168.1.1", "8.8.8.8"]
    dns_suffixes = ["internal.company.com", "company.com"]
    config = rdf_client_network.DNSClientConfiguration(
        dns_server=dns_servers, dns_suffix=dns_suffixes)

    converter = network.DNSClientConfigurationToExportedDNSClientConfiguration()
    results = list(converter.Convert(self.metadata, config))

    self.assertLen(results, 1)
    self.assertEqual(results[0].dns_servers, " ".join(dns_servers))
    self.assertEqual(results[0].dns_suffixes, " ".join(dns_suffixes))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
