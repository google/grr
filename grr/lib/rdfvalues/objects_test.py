#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

from google.protobuf import text_format
import unittest
from grr.lib import rdfvalue
from grr.lib.rdfvalues import objects
from grr_response_proto import objects_pb2


def MakeClient():
  client = objects.ClientSnapshot(client_id="C.0000000000000000")

  base_pb = objects_pb2.ClientSnapshot()
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
      objects.ClientSnapshot()

    # One digit short.
    with self.assertRaises(ValueError):
      objects.ClientSnapshot(client_id="C.000000000000000")

    with self.assertRaises(ValueError):
      objects.ClientSnapshot(client_id="not a real id")

    objects.ClientSnapshot(client_id="C.0000000000000000")

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

  def testClientSummaryTimestamp(self):
    client = MakeClient()
    client.timestamp = rdfvalue.RDFDatetime.Now()
    summary = client.GetSummary()
    self.assertEqual(client.timestamp, summary.timestamp)


class PathInfoTest(unittest.TestCase):

  def testPathInfoMakePathID(self):
    # Even if the path components have unlikely/uncommon characters, we
    # shouldn't have any id collisions.
    test_paths = [
        ["usr", "local", "bin", "protoc"],
        ["usr", "home", "user"],
        ["usr", "home", "user\n"],
        ["usr", "home", "user\00"],
        ["usr", "home", "user", u"⛄࿄"],
        ["usr", "home", "user", "odd", "path"],
        ["usr", "home", "user", "odd/path"],
        ["usr", "home", "user", "odd\\path"],
    ]
    hashes_seen = set()
    for path in test_paths:
      self.assertNotIn(objects.PathInfo.MakePathID(path), hashes_seen)
      hashes_seen.add(objects.PathInfo.MakePathID(path))
      # Check that the result is stable.
      self.assertIn(objects.PathInfo.MakePathID(path), hashes_seen)
    self.assertEqual(len(hashes_seen), len(test_paths))

  def testAncestorPathIDs(self):
    hashes_seen = set()
    for path_id, _ in objects.PathInfo.MakeAncestorPathIDs(
        ["usr", "home", "user", "has", "a", "long", "long", "path"]):
      hashes_seen.add(path_id)
    self.assertEqual(len(hashes_seen), 8)

    self.assertIn(objects.PathInfo.MakePathID(["usr"]), hashes_seen)
    self.assertIn(
        objects.PathInfo.MakePathID(["usr", "home", "user", "has"]),
        hashes_seen)
    self.assertIn(
        objects.PathInfo.MakePathID(
            ["usr", "home", "user", "has", "a", "long", "long"]), hashes_seen)
    # We consider a path to be an ancestor of itself.
    self.assertIn(
        objects.PathInfo.MakePathID(
            ["usr", "home", "user", "has", "a", "long", "long", "path"]),
        hashes_seen)

  def testUpdateFromValidates(self):
    # cannot merge from a string
    with self.assertRaises(ValueError):
      objects.PathInfo(
          components=["usr", "local", "bin"],).UpdateFrom("/usr/local/bin")
    # both must refer to the same path type
    with self.assertRaises(ValueError):
      objects.PathInfo(
          components=["usr", "local", "bin"],
          path_type=objects.PathInfo.PathType.OS,
      ).UpdateFrom(
          objects.PathInfo(
              components=["usr", "local", "bin"],
              path_type=objects.PathInfo.PathType.TSK,
          ))
    # both must refer to the same path
    with self.assertRaises(ValueError):
      objects.PathInfo(components=["usr", "local", "bin"]).UpdateFrom(
          objects.PathInfo(components=["usr", "local", "bin", "protoc"]))

  def testUpdateFromDirectory(self):
    dest = objects.PathInfo(components=["usr", "local", "bin"])
    self.assertFalse(dest.directory)
    dest.UpdateFrom(
        objects.PathInfo(components=["usr", "local", "bin"], directory=True))
    self.assertTrue(dest.directory)

  def testMergePathInfoLastUpdate(self):
    components = ["usr", "local", "bin"]
    dest = objects.PathInfo(components=components)
    self.assertIsNone(dest.last_path_history_timestamp)

    dest.UpdateFrom(
        objects.PathInfo(
            components=components,
            last_path_history_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2017-01-01")))
    self.assertEqual(dest.last_path_history_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2017-01-01"))

    # Merging in a record without last_path_history_timestamp shouldn't change
    # it.
    dest.UpdateFrom(objects.PathInfo(components=components))
    self.assertEqual(dest.last_path_history_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2017-01-01"))

    # Merging in a record with an earlier last_path_history_timestamp shouldn't
    # change it.
    dest.UpdateFrom(
        objects.PathInfo(
            components=components,
            last_path_history_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2016-01-01")))
    self.assertEqual(dest.last_path_history_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2017-01-01"))

    # Merging in a record with a later last_path_history_timestamp should change
    # it.
    dest.UpdateFrom(
        objects.PathInfo(
            components=components,
            last_path_history_timestamp=rdfvalue.RDFDatetime.FromHumanReadable(
                "2018-01-01")))
    self.assertEqual(dest.last_path_history_timestamp,
                     rdfvalue.RDFDatetime.FromHumanReadable("2018-01-01"))


if __name__ == "__main__":
  unittest.main()
