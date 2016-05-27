#!/usr/bin/env python
"""Test client RDFValues."""


import socket

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import test_base
from grr.proto import knowledge_base_pb2


class UserTests(test_base.RDFValueTestCase):
  """Test the User ProtoStruct implementation."""

  rdfvalue_class = rdf_client.User

  USER_ACCOUNT = dict(username=u"user",
                      full_name=u"John Smith",
                      comment=u"This is a user",
                      last_logon=10000,
                      domain=u"Some domain name",
                      homedir=u"/home/user",
                      sid=u"some sid")

  def GenerateSample(self, number=0):
    result = rdf_client.User(username="user%s" % number)
    result.desktop = "User Desktop %s" % number

    return result

  def testKBUserBackwardsCompatibility(self):
    """Check User can be created from deprecated KBUser."""
    kbuser = rdf_client.KnowledgeBaseUser()
    kbuser.username = "user1"
    kbuser.desktop = "User Desktop 1"

    user = rdf_client.User(kbuser)

    self.assertEqual(user.username, "user1")
    self.assertEqual(user.desktop, "User Desktop 1")

  def testCompatibility(self):
    proto = knowledge_base_pb2.User(username="user1")
    proto.desktop = "User Desktop 1"

    serialized = proto.SerializeToString()

    rdf_from_serialized = rdf_client.User(serialized)

    self.assertEqual(rdf_from_serialized.username, proto.username)
    self.assertEqual(rdf_from_serialized.desktop, proto.desktop)

    rdf_direct = rdf_client.User(username="user1", desktop="User Desktop 1")

    self.assertRDFValuesEqual(rdf_from_serialized, rdf_direct)

  def testTimeEncoding(self):
    fast_proto = rdf_client.User(username="user")

    # Check that we can coerce an int to an RDFDatetime.
    fast_proto.last_logon = 1365177603180131

    self.assertEqual(str(fast_proto.last_logon), "2013-04-05 16:00:03")
    self.assertEqual(type(fast_proto.last_logon), rdfvalue.RDFDatetime)

    # Check that this is backwards compatible with the old protobuf library.
    proto = knowledge_base_pb2.User()
    proto.ParseFromString(fast_proto.SerializeToString())

    # Old implementation should just see the last_logon field as an integer.
    self.assertEqual(proto.last_logon, 1365177603180131)
    self.assertEqual(type(proto.last_logon), long)

    # fast protobufs interoperate with old serialized formats.
    serialized_data = proto.SerializeToString()
    fast_proto = rdf_client.User(serialized_data)
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
        # FIFO
        (4516, "prw-r--r--"),
        # Socket
        (49663, "srwxrwxrwx"),
        # Sticky
        (33791, "-rwxrwxrwt"),
        # Sticky, not x
        (33784, "-rwxrwx--T"),
    ]:
      value = rdf_client.StatMode(mode)
      self.assertEqual(unicode(value), result)


class ClientURNTests(test_base.RDFValueTestCase):
  """Test the ClientURN."""

  rdfvalue_class = rdf_client.ClientURN

  def GenerateSample(self, number=0):
    return rdf_client.ClientURN("C.%016X" % number)

  def testInitialization(self):
    """ClientURNs don't allow empty init so we override the default test."""

    self.rdfvalue_class("C.00aaeccbb45f33a3")

    # Initialize from another instance.
    sample = self.GenerateSample()

    self.CheckRDFValue(self.rdfvalue_class(sample), sample)

  def testURNValidation(self):
    # These should all come out the same: C.00aaeccbb45f33a3
    test_set = ["C.00aaeccbb45f33a3", "C.00aaeccbb45f33a3".upper(),
                "c.00aaeccbb45f33a3", "C.00aaeccbb45f33a3 "]
    results = []
    for urnstr in test_set:
      results.append(rdf_client.ClientURN(urnstr))
      results.append(rdf_client.ClientURN("aff4:/%s" % urnstr))

    self.assertEqual(len(results), len(test_set) * 2)

    # Check all are identical
    self.assertTrue(all([x == results[0] for x in results]))

    # Check we can handle URN as well as string
    rdf_client.ClientURN(rdf_client.ClientURN(test_set[0]))

    error_set = ["B.00aaeccbb45f33a3", "", "c.00accbb45f33a3",
                 "aff5:/C.00aaeccbb45f33a3"]

    for badurn in error_set:
      self.assertRaises(type_info.TypeValueError, rdf_client.ClientURN, badurn)

    self.assertRaises(ValueError, rdf_client.ClientURN, None)


class NetworkAddressTests(test_base.RDFValueTestCase):
  """Test the NetworkAddress."""

  rdfvalue_class = rdf_client.NetworkAddress

  def GenerateSample(self, number=0):
    return rdf_client.NetworkAddress(human_readable_address="192.168.0.%s" %
                                     number)

  def testIPv4(self):
    sample = rdf_client.NetworkAddress(human_readable_address="192.168.0.1")
    self.assertEqual(sample.address_type, rdf_client.NetworkAddress.Family.INET)
    self.assertEqual(sample.packed_bytes,
                     socket.inet_pton(socket.AF_INET, "192.168.0.1"))

    self.assertEqual(sample.human_readable_address, "192.168.0.1")

    self.CheckRDFValue(self.rdfvalue_class(sample), sample)

  def testIPv6(self):
    ipv6_addresses = ["fe80::202:b3ff:fe1e:8329", "::1"]
    for address in ipv6_addresses:
      sample = rdf_client.NetworkAddress(human_readable_address=address)
      self.assertEqual(sample.address_type,
                       rdf_client.NetworkAddress.Family.INET6)
      self.assertEqual(sample.packed_bytes,
                       socket.inet_pton(socket.AF_INET6, address))

      self.assertEqual(sample.human_readable_address, address)

      self.CheckRDFValue(self.rdfvalue_class(sample), sample)


class UnameTests(test_base.RDFValueTestCase):
  """Test the Uname."""

  rdfvalue_class = rdf_client.Uname

  def GenerateSample(self, number=0):
    # Make the hostname slighly different for comparison tests.
    result = self.rdfvalue_class.FromCurrentSystem()
    result.node += str(number)
    return result

  def testSignature(self):
    sample = self.GenerateSample()
    self.assertEqual(sample.signature(), sample.pep425tag)

    # We do not support old protos without a signature.
    sample.pep425tag = None
    self.assertRaises(ValueError, sample.signature)
