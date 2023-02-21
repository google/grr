#!/usr/bin/env python
import ipaddress
import socket
from unittest import mock

from absl import app

from grr_response_server import ip_resolver
from grr.test_lib import test_lib


class IPResolverTest(test_lib.GRRBaseTest):

  def testIPInfo(self):

    args = []

    def MockGetNameInfo(ip, unused_flags):
      args.append(ip)
      return "test.com", ip[1]

    resolver = ip_resolver.IPResolver()
    with mock.patch.object(socket, "getnameinfo", MockGetNameInfo):
      for ip, result in [
          ("192.168.0.1", ip_resolver.IPInfo.INTERNAL),
          ("10.0.0.7", ip_resolver.IPInfo.INTERNAL),
          ("::1", ip_resolver.IPInfo.INTERNAL),
          ("69.50.225.155", ip_resolver.IPInfo.EXTERNAL),
          ("69.50.225.155", ip_resolver.IPInfo.EXTERNAL),
      ]:
        info, _ = resolver.RetrieveIPInfo(ipaddress.ip_address(ip))
        self.assertEqual(info, result)

    # There is one external address but it was resolved twice. There is a cache
    # so getnameinfo should have been called only once.
    self.assertLen(args, 1)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
