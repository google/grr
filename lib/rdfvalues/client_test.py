#!/usr/bin/env python
"""Test client RDFValues."""


from grr.lib import rdfvalue
from grr.lib.rdfvalues import test_base
from grr.proto import jobs_pb2


class UserTests(test_base.RDFValueTestCase):
  """Test the User ProtoStruct implementation."""

  rdfvalue_class = rdfvalue.User

  USER_ACCOUNT = dict(
      username=u"user", full_name=u"John Smith",
      comment=u"This is a user", last_logon=10000,
      domain=u"Some domain name",
      homedir=u"/home/user",
      sid=u"some sid")

  def GenerateSample(self, number=0):
    result = rdfvalue.User(username="user%s" % number)
    result.special_folders.desktop = "User Desktop %s" % number

    return result

  def testCompatibility(self):
    proto = jobs_pb2.UserAccount(username="user1")
    proto.special_folders.desktop = "User Desktop 1"

    serialized = proto.SerializeToString()

    fast_proto = rdfvalue.User(serialized)

    self.assertEqual(fast_proto.username, proto.username)
    self.assertEqual(fast_proto.special_folders.desktop,
                     proto.special_folders.desktop)

    # Serialized form of both should be the same.
    self.assertProtoEqual(fast_proto, proto)

  def testTimeEncoding(self):
    fast_proto = rdfvalue.User(username="user")

    # Check that we can coerce an int to an RDFDatetime.
    fast_proto.last_logon = 1365177603180131

    self.assertEqual(str(fast_proto.last_logon), "2013-04-05 16:00:03")
    self.assertEqual(type(fast_proto.last_logon), rdfvalue.RDFDatetime)

    # Check that this is backwards compatible with the old protobuf library.
    proto = jobs_pb2.UserAccount()
    proto.ParseFromString(fast_proto.SerializeToString())

    # Old implementation should just see the last_logon field as an integer.
    self.assertEqual(proto.last_logon, 1365177603180131)
    self.assertEqual(type(proto.last_logon), long)

    # fast protobufs interoperate with old serialized formats.
    serialized_data = proto.SerializeToString()
    fast_proto = rdfvalue.User(serialized_data)
    self.assertEqual(fast_proto.last_logon, 1365177603180131)
    self.assertEqual(type(fast_proto.last_logon), rdfvalue.RDFDatetime)
