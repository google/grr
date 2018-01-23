#!/usr/bin/env python
from google.protobuf import text_format
import unittest
from grr.lib.rdfvalues import objects
from grr_response_proto import objects_pb2


def MakeClient():
  client = objects.Client(client_id="C.0000000000000000")

  base_pb = objects_pb2.Client()
  text_format.Merge("""
    os_release: "Ubuntu"
    os_version: "14.4"
    interfaces: {
      addresses: {
        address_type: INET
        packed_bytes: "\177\000\000\001"
      }
      addresses: {
        address_type: INET6
        packed_bytes: "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\001"
      }
    }
    interfaces: {
    mac_address: "\001\002\003\004\001\002\003\004\001\002\003\004"
      addresses: {
        address_type: INET
        packed_bytes: "\010\010\010\010"
      }
      addresses: {
        address_type: INET6
        packed_bytes: "\376\200\001\002\003\000\000\000\000\000\000\000\000\000\000\000"
      }
    }
    knowledge_base: {
      users: {
        username: "joe"
        full_name: "Good Guy Joe"
      }
      users: {
        username: "fred"
        full_name: "Ok Guy Fred"
      }
      fqdn: "test123.examples.com"
      os: "Linux"
    }
    cloud_instance: {
      cloud_type: GOOGLE
      google: {
        unique_id: "us-central1-a/myproject/1771384456894610289"
      }
    }
    """, base_pb)

  client.ParseFromString(base_pb.SerializeToString())
  return client


class ObjectTest(unittest.TestCase):

  def testInvalidClientID(self):

    # No id.
    with self.assertRaises(ValueError):
      objects.Client()

    # One digit short.
    with self.assertRaises(ValueError):
      objects.Client(client_id="C.000000000000000")

    with self.assertRaises(ValueError):
      objects.Client(client_id="not a real id")

    objects.Client(client_id="C.0000000000000000")

  def testClientBasics(self):
    client = MakeClient()
    self.assertIsNone(client.timestamp)

    self.assertEqual(client.knowledge_base.fqdn, "test123.examples.com")
    self.assertEqual(client.Uname(), "Linux-Ubuntu-14.4")

  def testClientAddresses(self):
    client = MakeClient()
    self.assertEqual(
        sorted(client.GetIPAddresses()), ["8.8.8.8", "fe80:102:300::"])
    self.assertEqual(client.GetMacAddresses(), ["010203040102030401020304"])

  def testClientSummary(self):
    client = MakeClient()
    summary = client.GetSummary()
    self.assertEqual(summary.system_info.fqdn, "test123.examples.com")
    self.assertEqual(summary.cloud_instance_id,
                     "us-central1-a/myproject/1771384456894610289")
    self.assertEqual(
        sorted([u.username for u in summary.users]), ["fred", "joe"])


if __name__ == "__main__":
  unittest.main()
