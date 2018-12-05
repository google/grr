#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""OSX tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import ctypes
import os
import socket
import struct


from future.builtins import bytes
import mock

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr.test_lib import client_test_lib
from grr.test_lib import osx_launchd_testdata
from grr.test_lib import test_lib


class OSXClientTests(client_test_lib.OSSpecificClientTests):
  """OSX client action tests."""

  def setUp(self):
    super(OSXClientTests, self).setUp()
    # TODO(user): move this import to the top of the file.
    # At the moment, importing this at the top of the file causes
    # "Duplicate names for registered classes" metaclass registry
    # error.
    # pylint: disable=g-import-not-at-top
    from grr_response_client.client_actions.osx import osx
    # pylint: enable=g-import-not-at-top
    self.osx = osx


class OSXFilesystemTests(OSXClientTests):
  """Test reading osx file system."""

  def testFileSystemEnumeration64Bit(self):
    """Ensure we can enumerate file systems successfully."""
    path = os.path.join(self.base_path, "osx_fsdata")
    results = self.osx.client_utils_osx.ParseFileSystemsStruct(
        self.osx.client_utils_osx.StatFS64Struct, 7,
        open(path, "rb").read())
    self.assertLen(results, 7)
    self.assertEqual(results[0].f_fstypename, "hfs")
    self.assertEqual(results[0].f_mntonname, "/")
    self.assertEqual(results[0].f_mntfromname, "/dev/disk0s2")
    self.assertEqual(results[2].f_fstypename, "autofs")
    self.assertEqual(results[2].f_mntonname, "/auto")
    self.assertEqual(results[2].f_mntfromname, "map auto.auto")


class OSXEnumerateRunningServicesTest(OSXClientTests):

  def ValidResponseProto(self, proto):
    self.assertTrue(proto.label)
    return True

  def ValidResponseProtoSingle(self, proto):
    return True

  @mock.patch(
      "grr_response_client.client_utils_osx."
      "OSXVersion")
  def testOSXEnumerateRunningServicesAll(self, osx_version_mock):
    version_value_mock = mock.Mock()
    version_value_mock.VersionAsMajorMinor.return_value = [10, 7]
    osx_version_mock.return_value = version_value_mock

    with mock.patch.object(
        self.osx, "GetRunningLaunchDaemons") as get_running_launch_daemons_mock:
      with mock.patch.object(self.osx.OSXEnumerateRunningServices,
                             "SendReply") as send_reply_mock:

        get_running_launch_daemons_mock.return_value = osx_launchd_testdata.JOBS

        action = self.osx.OSXEnumerateRunningServices(None)
        num_results = len(
            osx_launchd_testdata.JOBS) - osx_launchd_testdata.FILTERED_COUNT

        action.Run(None)

        self.assertEqual(send_reply_mock.call_count, num_results)
        for c_args in send_reply_mock.call_args_list:
          # First call argument is expected to be an OSXServiceInformation.
          # Verify that the label is set.
          self.assertTrue(c_args[0][0].label)

  @mock.patch(
      "grr_response_client.client_utils_osx."
      "OSXVersion")
  def testOSXEnumerateRunningServicesSingle(self, osx_version_mock):
    version_value_mock = mock.Mock()
    version_value_mock.VersionAsMajorMinor.return_value = [10, 7, 1]
    osx_version_mock.return_value = version_value_mock

    with mock.patch.object(
        self.osx, "GetRunningLaunchDaemons") as get_running_launch_daemons_mock:
      with mock.patch.object(self.osx.OSXEnumerateRunningServices,
                             "SendReply") as send_reply_mock:

        get_running_launch_daemons_mock.return_value = osx_launchd_testdata.JOB

        action = self.osx.OSXEnumerateRunningServices(None)
        action.Run(None)

        self.assertEqual(send_reply_mock.call_count, 1)
        proto = send_reply_mock.call_args[0][0]

        td = osx_launchd_testdata.JOB[0]
        self.assertEqual(proto.label, td["Label"])
        self.assertEqual(proto.lastexitstatus, td["LastExitStatus"].value)
        self.assertEqual(proto.sessiontype, td["LimitLoadToSessionType"])
        self.assertLen(proto.machservice, len(td["MachServices"]))
        self.assertEqual(proto.ondemand, td["OnDemand"].value)
        self.assertLen(proto.args, len(td["ProgramArguments"]))
        self.assertEqual(proto.timeout, td["TimeOut"].value)

  @mock.patch(
      "grr_response_client.client_utils_osx."
      "OSXVersion")
  def testOSXEnumerateRunningServicesVersionError(self, osx_version_mock):
    version_value_mock = mock.Mock()
    version_value_mock.VersionAsMajorMinor.return_value = [10, 5, 1]
    version_value_mock.VersionString.return_value = "10.5.1"
    osx_version_mock.return_value = version_value_mock

    action = self.osx.OSXEnumerateRunningServices(None)
    with self.assertRaises(self.osx.UnsupportedOSVersionError):
      action.Run(None)


class IterIfaddrsTest(OSXClientTests):

  def testEmpty(self):
    self.assertEmpty(list(self.osx.IterIfaddrs(None)))

  def testMultiple(self):
    ifaddr_foo = self.osx.Ifaddrs()
    ifaddr_foo.ifa_name = ctypes.create_string_buffer("foo".encode("utf-8"))
    ifaddr_foo.ifa_next = None

    ifaddr_bar = self.osx.Ifaddrs()
    ifaddr_bar.ifa_name = ctypes.create_string_buffer("bar".encode("utf-8"))
    ifaddr_bar.ifa_next = ctypes.pointer(ifaddr_foo)

    ifaddr_baz = self.osx.Ifaddrs()
    ifaddr_baz.ifa_name = ctypes.create_string_buffer("baz".encode("utf-8"))
    ifaddr_baz.ifa_next = ctypes.pointer(ifaddr_bar)

    name = lambda ifaddr: ctypes.string_at(ifaddr.ifa_name).decode("utf-8")

    results = list(self.osx.IterIfaddrs(ctypes.pointer(ifaddr_baz)))
    self.assertLen(results, 3)
    self.assertEqual(name(results[0]), "baz")
    self.assertEqual(name(results[1]), "bar")
    self.assertEqual(name(results[2]), "foo")


class ParseIfaddrsTest(OSXClientTests):

  def testSingleIpv4(self):
    ipv4 = socket.inet_pton(socket.AF_INET, "127.0.0.1")

    sockaddrin = self.osx.Sockaddrin()
    sockaddrin.sin_family = self.osx.AF_INET
    sockaddrin.sin_addr = struct.unpack("=L", ipv4)[0]

    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_name = ctypes.create_string_buffer("foo".encode("utf-8"))
    ifaddr.ifa_addr = ctypes.cast(
        ctypes.pointer(sockaddrin), ctypes.POINTER(self.osx.Sockaddr))

    results = list(self.osx.ParseIfaddrs(ctypes.pointer(ifaddr)))
    self.assertLen(results, 1)
    self.assertEqual(results[0].ifname, "foo")
    self.assertLen(results[0].addresses, 1)

    address = results[0].addresses[0]
    self.assertEqual(address.address_type, address.Family.INET)
    self.assertEqual(address.packed_bytes, ipv4)

  def testSingleIpv6(self):
    ipv6 = socket.inet_pton(socket.AF_INET6, "2001:db8::ff00:42:8329")

    sockaddrin = self.osx.Sockaddrin6()
    sockaddrin.sin6_family = self.osx.AF_INET6
    sockaddrin.sin6_addr = struct.unpack("=" + "B" * 16, ipv6)

    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_name = ctypes.create_string_buffer("bar".encode("utf-8"))
    ifaddr.ifa_addr = ctypes.cast(
        ctypes.pointer(sockaddrin), ctypes.POINTER(self.osx.Sockaddr))

    results = list(self.osx.ParseIfaddrs(ctypes.pointer(ifaddr)))
    self.assertLen(results, 1)
    self.assertEqual(results[0].ifname, "bar")
    self.assertLen(results[0].addresses, 1)

    address = results[0].addresses[0]
    self.assertEqual(address.address_type, address.Family.INET6)
    self.assertEqual(address.packed_bytes, ipv6)

  def testSingleMac(self):
    name = "baz".encode("utf-8")
    mac = b"\x01\x23\x45\x67\x89\xab"

    sockaddrdl = self.osx.Sockaddrdl()
    sockaddrdl.sdl_family = self.osx.AF_LINK
    sockaddrdl.sdl_data[0:len(name + mac)] = list(bytes(name + mac))
    sockaddrdl.sdl_nlen = len(name)
    sockaddrdl.sdl_alen = len(mac)

    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_name = ctypes.create_string_buffer(name)
    ifaddr.ifa_addr = ctypes.cast(
        ctypes.pointer(sockaddrdl), ctypes.POINTER(self.osx.Sockaddr))

    results = list(self.osx.ParseIfaddrs(ctypes.pointer(ifaddr)))
    self.assertLen(results, 1)
    self.assertEqual(results[0].ifname, name)
    self.assertEqual(results[0].mac_address, mac)

  def testMultiple(self):
    foo_ipv4 = socket.inet_pton(socket.AF_INET, "192.0.2.1")
    foo_mac = b"\x00\xa0\xc9\x14\xc8\x29"

    foo_sockaddrin = self.osx.Sockaddrin()
    foo_sockaddrin.sin_family = self.osx.AF_INET
    foo_sockaddrin.sin_addr = struct.unpack("=L", foo_ipv4)[0]

    foo_sockaddrdl = self.osx.Sockaddrdl()
    foo_sockaddrdl.sdl_family = self.osx.AF_LINK
    foo_sockaddrdl.sdl_data[0:len(foo_mac)] = list(bytes(foo_mac))
    foo_sockaddrdl.sdl_nlen = 0
    foo_sockaddrdl.sdl_alen = len(foo_mac)

    bar_ipv6 = socket.inet_pton(socket.AF_INET6, "2607:f0d0:1002:51::4")
    bar_mac = b"\x48\x2c\x6a\x1e\x59\x3d"

    bar_sockaddrin = self.osx.Sockaddrin6()
    bar_sockaddrin.sin6_family = self.osx.AF_INET6
    bar_sockaddrin.sin6_addr = struct.unpack("=" + "B" * 16, bar_ipv6)

    bar_sockaddrdl = self.osx.Sockaddrdl()
    bar_sockaddrdl.sdl_family = self.osx.AF_LINK
    bar_sockaddrdl.sdl_data[0:len(foo_mac)] = list(bytes(bar_mac))
    bar_sockaddrdl.sdl_nlen = 0
    bar_sockaddrdl.sdl_alen = len(bar_mac)

    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_next = None
    ifaddr.ifa_name = ctypes.create_string_buffer("foo")
    ifaddr.ifa_addr = ctypes.cast(
        ctypes.pointer(foo_sockaddrin), ctypes.POINTER(self.osx.Sockaddr))

    ifnext = ifaddr
    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_next = ctypes.pointer(ifnext)
    ifaddr.ifa_name = ctypes.create_string_buffer("foo")
    ifaddr.ifa_addr = ctypes.cast(
        ctypes.pointer(foo_sockaddrdl), ctypes.POINTER(self.osx.Sockaddr))

    ifnext = ifaddr
    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_next = ctypes.pointer(ifnext)
    ifaddr.ifa_name = ctypes.create_string_buffer("bar")
    ifaddr.ifa_addr = ctypes.cast(
        ctypes.pointer(bar_sockaddrdl), ctypes.POINTER(self.osx.Sockaddr))

    ifnext = ifaddr
    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_next = ctypes.pointer(ifnext)
    ifaddr.ifa_name = ctypes.create_string_buffer("bar")
    ifaddr.ifa_addr = ctypes.cast(
        ctypes.pointer(bar_sockaddrin), ctypes.POINTER(self.osx.Sockaddr))

    expected_foo_iface = rdf_client_network.Interface(
        ifname="foo",
        mac_address=foo_mac,
        addresses=[
            rdf_client_network.NetworkAddress(
                address_type=rdf_client_network.NetworkAddress.Family.INET,
                packed_bytes=foo_ipv4),
        ])

    expected_bar_iface = rdf_client_network.Interface(
        ifname="bar",
        mac_address=bar_mac,
        addresses=[
            rdf_client_network.NetworkAddress(
                address_type=rdf_client_network.NetworkAddress.Family.INET6,
                packed_bytes=bar_ipv6),
        ])

    results = list(self.osx.ParseIfaddrs(ctypes.pointer(ifaddr)))
    self.assertSameElements(results, [expected_foo_iface, expected_bar_iface])

  def testNoAddr(self):
    ifaddr = self.osx.Ifaddrs()
    ifaddr.ifa_name = ctypes.create_string_buffer("foo")

    results = list(self.osx.ParseIfaddrs(ctypes.pointer(ifaddr)))
    self.assertLen(results, 1)
    self.assertEqual(results[0].ifname, "foo")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
