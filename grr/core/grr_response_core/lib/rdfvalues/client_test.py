#!/usr/bin/env python
# Lint as: python3
"""Test client RDFValues."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import socket
from unittest import mock

from absl import app
from absl.testing import absltest
import psutil

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_proto import knowledge_base_pb2
from grr.test_lib import test_lib


class UserTests(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test the User ProtoStruct implementation."""

  rdfvalue_class = rdf_client.User

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

    rdf_from_serialized = rdf_client.User.FromSerializedBytes(serialized)

    self.assertEqual(rdf_from_serialized.username, proto.username)
    self.assertEqual(rdf_from_serialized.desktop, proto.desktop)

    rdf_direct = rdf_client.User(username="user1", desktop="User Desktop 1")

    self.assertEqual(rdf_from_serialized, rdf_direct)

  def testTimeEncoding(self):
    fast_proto = rdf_client.User(username="user")

    datetime = rdfvalue.RDFDatetime.FromHumanReadable("2013-04-05 16:00:03")

    # Check that we can coerce an int to an RDFDatetime.
    # TODO(hanuszczak): Yeah, but why would we...?
    fast_proto.last_logon = datetime.AsMicrosecondsSinceEpoch()

    self.assertEqual(fast_proto.last_logon, datetime)

    # Check that this is backwards compatible with the old protobuf library.
    proto = knowledge_base_pb2.User()
    proto.ParseFromString(fast_proto.SerializeToBytes())

    # Old implementation should just see the last_logon field as an integer.
    self.assertIsInstance(proto.last_logon, int)
    self.assertEqual(proto.last_logon, datetime.AsMicrosecondsSinceEpoch())

    # fast protobufs interoperate with old serialized formats.
    serialized_data = proto.SerializeToString()
    fast_proto = rdf_client.User.FromSerializedBytes(serialized_data)
    self.assertIsInstance(fast_proto.last_logon, rdfvalue.RDFDatetime)
    self.assertEqual(fast_proto.last_logon, datetime.AsMicrosecondsSinceEpoch())

  def testPrettyPrintMode(self):

    for mode, result in [
        (0o775, "-rwxrwxr-x"),
        (0o75, "----rwxr-x"),
        (0, "----------"),
        # DIR
        (0o40775, "drwxrwxr-x"),
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
      value = rdf_client_fs.StatMode(mode)
      self.assertEqual(str(value), result)


class ClientURNTests(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
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
    test_set = [
        "C.00aaeccbb45f33a3", "C.00aaeccbb45f33a3".upper(),
        "c.00aaeccbb45f33a3", "C.00aaeccbb45f33a3 "
    ]
    results = []
    for urnstr in test_set:
      results.append(rdf_client.ClientURN(urnstr))
      results.append(rdf_client.ClientURN("aff4:/%s" % urnstr))

    self.assertLen(results, len(test_set) * 2)

    # Check all are identical
    self.assertTrue(all([x == results[0] for x in results]))

    # Check we can handle URN as well as string
    rdf_client.ClientURN(rdf_client.ClientURN(test_set[0]))

    error_set = [
        "B.00aaeccbb45f33a3", "c.00accbb45f33a3", "aff5:/C.00aaeccbb45f33a3"
    ]

    for badurn in error_set:
      self.assertRaises(type_info.TypeValueError, rdf_client.ClientURN, badurn)


class NetworkAddressTests(rdf_test_base.RDFValueTestMixin,
                          test_lib.GRRBaseTest):
  """Test the NetworkAddress."""

  rdfvalue_class = rdf_client_network.NetworkAddress

  def GenerateSample(self, number=0):
    return rdf_client_network.NetworkAddress(
        human_readable_address="192.168.0.%s" % number)

  def testIPv4(self):
    sample = rdf_client_network.NetworkAddress(
        human_readable_address="192.168.0.1")
    self.assertEqual(sample.address_type,
                     rdf_client_network.NetworkAddress.Family.INET)
    # Equal to socket.inet_pton(socket.AF_INET, "192.168.0.1"), which is
    # unavailable on Windows.
    self.assertEqual(sample.packed_bytes, b"\xc0\xa8\x00\x01")

    self.assertEqual(sample.human_readable_address, "192.168.0.1")

    self.CheckRDFValue(self.rdfvalue_class(sample), sample)

  def testIPv6(self):
    ipv6_addresses = ["fe80::202:b3ff:fe1e:8329", "::1"]
    # Equal to socket.inet_pton(socket.AF_INET6, address), which is unavailable
    # on Windows.
    expected_addresses = [
        b"\xfe\x80\x00\x00\x00\x00\x00\x00\x02\x02\xb3\xff\xfe\x1e\x83\x29",
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
    ]
    for address, expected in zip(ipv6_addresses, expected_addresses):
      sample = rdf_client_network.NetworkAddress(human_readable_address=address)
      self.assertEqual(sample.address_type,
                       rdf_client_network.NetworkAddress.Family.INET6)
      self.assertEqual(sample.packed_bytes, expected)

      self.assertEqual(sample.human_readable_address, address)

      self.CheckRDFValue(self.rdfvalue_class(sample), sample)


class UnameTests(rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest):
  """Test the Uname."""

  rdfvalue_class = rdf_client.Uname

  def GenerateSample(self, number=0):
    # Make the hostname slighly different for comparison tests.
    result = self.rdfvalue_class.FromCurrentSystem()
    parts = result.fqdn.split(".")
    parts[0] += str(number)
    result.fqdn = ".".join(parts)
    return result

  def testSignature(self):
    sample = self.GenerateSample()
    self.assertEqual(sample.signature(), sample.pep425tag)

    # We do not support old protos without a signature.
    sample.pep425tag = None
    self.assertRaises(ValueError, sample.signature)

  def testGetFQDN(self):
    with mock.patch.object(socket, "getfqdn", return_value="foo.bar.baz"):
      uname = self.rdfvalue_class.FromCurrentSystem()
      self.assertEqual(uname.fqdn, "foo.bar.baz")

  def testGetFQDN_Localhost(self):
    with mock.patch.object(
        socket, "getfqdn", return_value=rdf_client._LOCALHOST):
      with mock.patch.object(socket, "gethostname", return_value="foo"):
        uname = self.rdfvalue_class.FromCurrentSystem()
        self.assertEqual(uname.fqdn, "foo")


class CpuSampleTest(absltest.TestCase):

  def testFromMany(self):
    samples = [
        rdf_client_stats.CpuSample(
            timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2001-01-01"),
            cpu_percent=0.2,
            user_cpu_time=0.1,
            system_cpu_time=0.5),
        rdf_client_stats.CpuSample(
            timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2001-02-01"),
            cpu_percent=0.1,
            user_cpu_time=2.5,
            system_cpu_time=1.2),
        rdf_client_stats.CpuSample(
            timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2001-03-01"),
            cpu_percent=0.6,
            user_cpu_time=3.4,
            system_cpu_time=2.4),
    ]

    expected = rdf_client_stats.CpuSample(
        timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2001-03-01"),
        cpu_percent=0.3,
        user_cpu_time=3.4,
        system_cpu_time=2.4)

    self.assertEqual(rdf_client_stats.CpuSample.FromMany(samples), expected)

  def testFromManyRaisesOnEmpty(self):
    with self.assertRaises(ValueError):
      rdf_client_stats.CpuSample.FromMany([])


class IOSampleTest(absltest.TestCase):

  def testFromMany(self):
    samples = [
        rdf_client_stats.IOSample(
            timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2001-01-01"),
            read_bytes=0,
            write_bytes=0),
        rdf_client_stats.IOSample(
            timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2002-01-01"),
            read_bytes=512,
            write_bytes=1024),
        rdf_client_stats.IOSample(
            timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2003-01-01"),
            read_bytes=2048,
            write_bytes=4096),
    ]

    expected = rdf_client_stats.IOSample(
        timestamp=rdfvalue.RDFDatetime.FromHumanReadable("2003-01-01"),
        read_bytes=2048,
        write_bytes=4096)

    self.assertEqual(rdf_client_stats.IOSample.FromMany(samples), expected)

  def testFromManyRaisesOnEmpty(self):
    with self.assertRaises(ValueError):
      rdf_client_stats.IOSample.FromMany([])


class ClientStatsTest(absltest.TestCase):

  def testDownsampled(self):
    timestamp = rdfvalue.RDFDatetime.FromHumanReadable

    stats = rdf_client_stats.ClientStats(
        cpu_samples=[
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:00"),
                user_cpu_time=2.5,
                system_cpu_time=3.2,
                cpu_percent=0.5),
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:05"),
                user_cpu_time=2.6,
                system_cpu_time=4.7,
                cpu_percent=0.6),
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:10"),
                user_cpu_time=10.0,
                system_cpu_time=14.2,
                cpu_percent=0.9),
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:12"),
                user_cpu_time=12.3,
                system_cpu_time=14.9,
                cpu_percent=0.1),
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:21"),
                user_cpu_time=16.1,
                system_cpu_time=22.3,
                cpu_percent=0.4)
        ],
        io_samples=[
            rdf_client_stats.IOSample(
                timestamp=timestamp("2001-01-01 00:00"),
                read_count=0,
                write_count=0),
            rdf_client_stats.IOSample(
                timestamp=timestamp("2001-01-01 00:02"),
                read_count=3,
                write_count=5),
            rdf_client_stats.IOSample(
                timestamp=timestamp("2001-01-01 00:12"),
                read_count=6,
                write_count=8),
        ])

    expected = rdf_client_stats.ClientStats(
        cpu_samples=[
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:05"),
                user_cpu_time=2.6,
                system_cpu_time=4.7,
                cpu_percent=0.55),
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:12"),
                user_cpu_time=12.3,
                system_cpu_time=14.9,
                cpu_percent=0.5),
            rdf_client_stats.CpuSample(
                timestamp=timestamp("2001-01-01 00:21"),
                user_cpu_time=16.1,
                system_cpu_time=22.3,
                cpu_percent=0.4),
        ],
        io_samples=[
            rdf_client_stats.IOSample(
                timestamp=timestamp("2001-01-01 00:02"),
                read_count=3,
                write_count=5),
            rdf_client_stats.IOSample(
                timestamp=timestamp("2001-01-01 00:12"),
                read_count=6,
                write_count=8),
        ])

    actual = rdf_client_stats.ClientStats.Downsampled(
        stats, interval=rdfvalue.Duration.From(10, rdfvalue.MINUTES))

    self.assertEqual(actual, expected)


class ProcessTest(absltest.TestCase):

  def testFromPsutilProcess(self):

    p = psutil.Process()
    res = rdf_client.Process.FromPsutilProcess(p)

    int_fields = [
        "pid", "ppid", "ctime", "num_threads", "user_cpu_time",
        "system_cpu_time", "RSS_size", "VMS_size", "memory_percent"
    ]

    if platform.system() != "Windows":
      int_fields.extend([
          "real_uid", "effective_uid", "saved_uid", "real_gid", "effective_gid",
          "saved_gid"
      ])

    for field in int_fields:
      self.assertGreater(
          getattr(res, field), 0,
          "rdf_client.Process.{} is not greater than 0, got {!r}.".format(
              field, getattr(res, field)))

    string_fields = ["name", "exe", "cmdline", "cwd", "username"]

    if platform.system() != "Windows":
      string_fields.append("terminal")

    for field in string_fields:
      self.assertNotEqual(
          getattr(res, field), "",
          "rdf_client.Process.{} is the empty string.".format(field))

    # Prevent flaky tests by allowing "sleeping" as state of current process.
    self.assertIn(res.status, ["running", "sleeping"])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
