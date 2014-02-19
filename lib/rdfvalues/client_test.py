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
    proto = jobs_pb2.User(username="user1")
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
    proto = jobs_pb2.User()
    proto.ParseFromString(fast_proto.SerializeToString())

    # Old implementation should just see the last_logon field as an integer.
    self.assertEqual(proto.last_logon, 1365177603180131)
    self.assertEqual(type(proto.last_logon), long)

    # fast protobufs interoperate with old serialized formats.
    serialized_data = proto.SerializeToString()
    fast_proto = rdfvalue.User(serialized_data)
    self.assertEqual(fast_proto.last_logon, 1365177603180131)
    self.assertEqual(type(fast_proto.last_logon), rdfvalue.RDFDatetime)

  def testPrettyPrintMode(self):

    for mode, result in [
        (0775, "-rwxrwxr-x"),
        (075, "----rwxr-x"),
        (0, "----------"),
        # DIR
        (040775, "drwxrwxr-x"),
        # SUID
        (35232, "-rwSr-----"),
        # GID
        (34208, "-rw-r-S---"),
        # CHR
        (9136, "crw-rw---T"),
        # BLK
        (25008, "brw-rw----"),
        # Socket
        (49663, "srwxrwxrwx"),
        # Sticky
        (33791, "-rwxrwxrwt"),
        # Sticky, not x
        (33784, "-rwxrwx--T"),
        ]:
      value = rdfvalue.StatMode(mode)
      self.assertEqual(unicode(value), result)

  def testConvertToKnowledgeBaseUser(self):
    folders = rdfvalue.FolderInformation(desktop="/usr/local/test/Desktop")
    user = rdfvalue.User(username="test", domain="test.com",
                         homedir="/usr/local/test",
                         special_folders=folders)
    kbuser = user.ToKnowledgeBaseUser()
    self.assertEqual(kbuser.username, "test")
    self.assertEqual(kbuser.userdomain, "test.com")
    self.assertEqual(kbuser.homedir, "/usr/local/test")
    self.assertEqual(kbuser.desktop, "/usr/local/test/Desktop")

  def testConvertFromKnowledgeBaseUser(self):
    kbuser = rdfvalue.KnowledgeBaseUser(username="test", userdomain="test.com",
                                        homedir="/usr/local/test",
                                        desktop="/usr/local/test/Desktop",
                                        localappdata="/usr/local/test/AppData")
    user = rdfvalue.User().FromKnowledgeBaseUser(kbuser)
    self.assertEqual(user.username, "test")
    self.assertEqual(user.domain, "test.com")
    self.assertEqual(user.homedir, "/usr/local/test")
    self.assertEqual(user.special_folders.desktop, "/usr/local/test/Desktop")
    self.assertEqual(user.special_folders.local_app_data,
                     "/usr/local/test/AppData")

