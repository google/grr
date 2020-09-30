#!/usr/bin/env python
from absl.testing import absltest

from grr_api_client.connectors import http
from grr_response_proto.api import metadata_pb2


class VersionTupleTest(absltest.TestCase):

  def testFromJson(self):
    version = http.VersionTuple.FromJson("""
    {
      "major": 2,
      "minor": 7,
      "revision": 1,
      "release": 8
    }
    """)
    self.assertEqual(version.major, 2)
    self.assertEqual(version.minor, 7)
    self.assertEqual(version.revision, 1)
    self.assertEqual(version.release, 8)

  def testFromProto(self):
    proto = metadata_pb2.ApiGetGrrVersionResult()
    proto.major = 2
    proto.minor = 7
    proto.revision = 1
    proto.release = 8

    version = http.VersionTuple.FromProto(proto)
    self.assertEqual(version.major, 2)
    self.assertEqual(version.minor, 7)
    self.assertEqual(version.revision, 1)
    self.assertEqual(version.release, 8)

  def testFromString(self):
    version = http.VersionTuple.FromString("2.7.1.post8")
    self.assertEqual(version.major, 2)
    self.assertEqual(version.minor, 7)
    self.assertEqual(version.revision, 1)
    self.assertEqual(version.release, 8)

  def testFromStringRaisesOnIncorrectFormat(self):
    with self.assertRaises(ValueError):
      http.VersionTuple.FromString("foo.bar.quux")


if __name__ == "__main__":
  absltest.main()
