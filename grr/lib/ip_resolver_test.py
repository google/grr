#!/usr/bin/env python
import socket

from grr.lib import flags
from grr.lib import ip_resolver
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class IPResolverTest(test_lib.GRRBaseTest):

  def testIPInfo(self):

    args = []

    def MockGetNameInfo(ip, unused_flags):
      args.append(ip)
      return "test.com", ip[1]

    resolver = ip_resolver.IPResolver()
    with utils.Stubber(socket, "getnameinfo", MockGetNameInfo):
      for ip, result in [
          ("", ip_resolver.IPInfo.UNKNOWN),
          ("192.168.0.1", ip_resolver.IPInfo.INTERNAL),
          ("10.0.0.7", ip_resolver.IPInfo.INTERNAL),
          ("::1", ip_resolver.IPInfo.INTERNAL),
          ("69.50.225.155", ip_resolver.IPInfo.EXTERNAL),
          ("69.50.225.155", ip_resolver.IPInfo.EXTERNAL),
      ]:
        rdf_ip = rdfvalue.RDFString(ip)
        info, _ = resolver.RetrieveIPInfo(rdf_ip)
        self.assertEqual(info, result)

    # There is one external address but it was resolved twice. There is a cache
    # so getnameinfo should have been called only once.
    self.assertEqual(len(args), 1)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
