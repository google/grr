#!/usr/bin/env python
import ipaddress

from absl.testing import absltest

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_proto import jobs_pb2


class NetworkAddressTest(absltest.TestCase):

  def testFromPackedBytesIPv4(self):
    ip = ipaddress.ip_address("192.168.0.1")

    address = rdf_client_network.NetworkAddress.FromPackedBytes(ip.packed)
    self.assertEqual(address.packed_bytes, ip.packed)
    self.assertEqual(address.address_type, jobs_pb2.NetworkAddress.INET)

  def testFromPackedBytesIPv6(self):
    ip = ipaddress.ip_address("2001:db8::8a2e:370:7334")

    address = rdf_client_network.NetworkAddress.FromPackedBytes(ip.packed)
    self.assertEqual(address.packed_bytes, ip.packed)
    self.assertEqual(address.address_type, jobs_pb2.NetworkAddress.INET6)

  def testFromPackedBytesIncorrect(self):
    with self.assertRaises(ValueError):
      rdf_client_network.NetworkAddress.FromPackedBytes(b"\xff\x00\xff")


if __name__ == "__main__":
  absltest.main()
