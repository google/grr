#!/usr/bin/env python
"""Tests for export converters."""

import socket

from absl import app
from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.util import text
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import client_summary
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class ClientSummaryToExportedNetworkInterfaceConverterTest(
    export_test_lib.ExportTestBase
):

  def testClientSummaryToExportedNetworkInterfaceConverter(self):
    mac_address_bytes = b"123456"
    mac_address = text.Hexify(mac_address_bytes)

    summary = rdf_client.ClientSummary(
        interfaces=[
            rdf_client_network.Interface(
                mac_address=mac_address_bytes,
                ifname="eth0",
                addresses=[
                    rdf_client_network.NetworkAddress(
                        address_type=rdf_client_network.NetworkAddress.Family.INET,
                        packed_bytes=socket.inet_pton(
                            socket.AF_INET, "127.0.0.1"
                        ),
                    ),
                    rdf_client_network.NetworkAddress(
                        address_type=rdf_client_network.NetworkAddress.Family.INET,
                        packed_bytes=socket.inet_pton(
                            socket.AF_INET, "10.0.0.1"
                        ),
                    ),
                    rdf_client_network.NetworkAddress(
                        address_type=rdf_client_network.NetworkAddress.Family.INET6,
                        packed_bytes=socket.inet_pton(
                            socket.AF_INET6, "2001:720:1500:1::a100"
                        ),
                    ),
                ],
            )
        ]
    )

    converter = (
        client_summary.ClientSummaryToExportedNetworkInterfaceConverter()
    )
    results = list(converter.Convert(self.metadata, summary))
    self.assertLen(results, 1)
    self.assertEqual(results[0].mac_address, mac_address)
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")


class ClientSummaryToExportedClientConverterTest(
    export_test_lib.ExportTestBase
):

  def testClientSummaryToExportedClientConverter(self):
    summary = rdf_client.ClientSummary()
    metadata = base.ExportedMetadata(hostname="ahostname")

    converter = client_summary.ClientSummaryToExportedClientConverter()
    results = list(converter.Convert(metadata, summary))

    self.assertLen(results, 1)
    self.assertEqual(results[0].metadata.hostname, "ahostname")


class ClientSummaryToExportedClientConverterProtoTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testClientSummaryToExportedClientConverter(self):
    unused_summary = jobs_pb2.ClientSummary()

    converter = client_summary.ClientSummaryToExportedClientConverterProto()
    results = list(converter.Convert(self.metadata_proto, unused_summary))

    self.assertLen(results, 1)
    self.assertEqual(results[0].metadata, self.metadata_proto)


class ClientSummaryToExportedNetworkInterfaceConverterProtoTest(
    absltest.TestCase
):

  def setUp(self):
    super().setUp()
    self.client_id = "C.1234567890123456"
    self.metadata_proto = export_pb2.ExportedMetadata(
        client_urn=rdf_client.ClientURN(self.client_id).SerializeToWireFormat(),
        client_id=self.client_id,
    )

  def testClientSummaryToExportedNetworkInterfaceConverter(self):
    mac_address_bytes = b"123456"
    mac_address = text.Hexify(mac_address_bytes)

    summary = jobs_pb2.ClientSummary(
        interfaces=[
            jobs_pb2.Interface(
                mac_address=mac_address_bytes,
                ifname="eth0",
                addresses=[
                    jobs_pb2.NetworkAddress(
                        address_type=jobs_pb2.NetworkAddress.Family.INET,
                        packed_bytes=socket.inet_pton(
                            socket.AF_INET, "127.0.0.1"
                        ),
                    ),
                    jobs_pb2.NetworkAddress(
                        address_type=jobs_pb2.NetworkAddress.Family.INET,
                        packed_bytes=socket.inet_pton(
                            socket.AF_INET, "10.0.0.1"
                        ),
                    ),
                    jobs_pb2.NetworkAddress(
                        address_type=jobs_pb2.NetworkAddress.Family.INET6,
                        packed_bytes=socket.inet_pton(
                            socket.AF_INET6, "2001:720:1500:1::a100"
                        ),
                    ),
                ],
            ),
            jobs_pb2.Interface(
                mac_address=mac_address_bytes,
                ifname="eth1",
                addresses=[
                    jobs_pb2.NetworkAddress(
                        address_type=jobs_pb2.NetworkAddress.Family.INET,
                        packed_bytes=socket.inet_pton(
                            socket.AF_INET, "192.168.1.1"
                        ),
                    ),
                ],
            ),
        ]
    )

    converter = (
        client_summary.ClientSummaryToExportedNetworkInterfaceConverterProto()
    )
    results = list(converter.Convert(self.metadata_proto, summary))
    self.assertLen(results, 2)

    self.assertIsInstance(results[0], export_pb2.ExportedNetworkInterface)
    self.assertEqual(results[0].mac_address, mac_address)
    self.assertEqual(results[0].ifname, "eth0")
    self.assertEqual(results[0].ip4_addresses, "127.0.0.1 10.0.0.1")
    self.assertEqual(results[0].ip6_addresses, "2001:720:1500:1::a100")

    self.assertIsInstance(results[1], export_pb2.ExportedNetworkInterface)
    self.assertEqual(results[1].mac_address, mac_address)
    self.assertEqual(results[1].ifname, "eth1")
    self.assertEqual(results[1].ip4_addresses, "192.168.1.1")
    self.assertEqual(results[1].ip6_addresses, "")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
