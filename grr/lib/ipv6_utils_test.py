#!/usr/bin/env python
"""Tests for grr.lib.ipv6_utils."""

import socket

from grr.lib import flags
from grr.lib import ipv6_addresses
from grr.lib import ipv6_utils
from grr.lib import test_lib


class Ipv6UtilsTest(test_lib.GRRBaseTest):
  """Test IPv6 utilities functions.

  Test addresses inspired by:
  http://download.dartware.com/thirdparty/test-ipv6-regex.pl

  We test for equivalence with socket.inet_pton and socket.inet_ntop but not
  reversibility since the addresses are output to best practice standard and the
  input is syntactically correct but not optimised.  We also don't restore
  dotted quad IPv4 endings.
  """

  def testInetAtoN(self):
    for address in ipv6_addresses.IPV6_ADDRESSES:
      self.assertEqual(
          ipv6_utils.InetAtoN(address),
          socket.inet_pton(socket.AF_INET6, address))

    for address in ipv6_addresses.BAD_IPV6_ADDRESSES:
      self.assertRaises(socket.error, ipv6_utils.InetAtoN, address)

  def testInetNtoA(self):
    for address in ipv6_addresses.IPV6_ADDRESSES:
      packed = socket.inet_pton(socket.AF_INET6, address)

      self.assertEqual(
          ipv6_utils.InetNtoA(packed),
          socket.inet_ntop(socket.AF_INET6, packed))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
