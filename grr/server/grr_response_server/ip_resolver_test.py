#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import socket

import ipaddr

from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_server import ip_resolver
from grr.test_lib import test_lib


class IPResolverTest(test_lib.GRRBaseTest):

  def testIPInfo(self):

    args = []

    def MockGetNameInfo(ip, unused_flags):
      args.append(ip)
      return "test.com", ip[1]

    resolver = ip_resolver.IPResolver()
    with utils.Stubber(socket, "getnameinfo", MockGetNameInfo):
      for ip, result in [
          ("192.168.0.1", ip_resolver.IPInfo.INTERNAL),
          ("10.0.0.7", ip_resolver.IPInfo.INTERNAL),
          ("::1", ip_resolver.IPInfo.INTERNAL),
          ("69.50.225.155", ip_resolver.IPInfo.EXTERNAL),
          ("69.50.225.155", ip_resolver.IPInfo.EXTERNAL),
      ]:
        rdf_ip = ipaddr.IPAddress(ip)
        info, _ = resolver.RetrieveIPInfo(rdf_ip)
        self.assertEqual(info, result)

    # There is one external address but it was resolved twice. There is a cache
    # so getnameinfo should have been called only once.
    self.assertLen(args, 1)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
