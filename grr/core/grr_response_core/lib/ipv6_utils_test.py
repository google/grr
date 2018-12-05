#!/usr/bin/env python
"""Tests for grr.lib.ipv6_utils."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import socket
import yaml

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import ipv6_utils
from grr.test_lib import test_lib


class Ipv6UtilsTest(test_lib.GRRBaseTest):
  """Test IPv6 utilities functions.

  Test addresses inspired by:
  http://download.dartware.com/thirdparty/test-ipv6-regex.pl

  We test for equivalence with linux's implementation of socket.inet_pton and
  socket.inet_ntop but not reversibility since the addresses are output to best
  practice standard and the input is syntactically correct but not optimised.
  We also don't restore dotted quad IPv4 endings.

  The test dataset was created as follows for each address:
    packed = socket.inet_pton(socket.AF_INET6, address)
    test_tuple = (packed, socket.inet_ntop(socket.AF_INET6, packed))
  """

  def testInetPtoNandNtoP(self):
    path = os.path.join(config.CONFIG["Test.data_dir"], "ipv6_addresses.yaml")
    with open(path, "rb") as test_data:
      test_dict = yaml.safe_load(test_data)

    for address in test_dict["ipv6_test_set"]:
      expected_packed, expected_unpacked = test_dict["ipv6_test_set"][address]
      self.assertEqual(
          ipv6_utils.CustomInetPtoN(socket.AF_INET6, address), expected_packed)
      self.assertEqual(
          ipv6_utils.CustomInetNtoP(socket.AF_INET6, expected_packed),
          expected_unpacked)

      for address in test_dict["bad_ipv6_addresses"]:
        with self.assertRaises(socket.error, message=address):
          ipv6_utils.CustomInetPtoN(socket.AF_INET6, address)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
