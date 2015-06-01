#!/usr/bin/env python
"""Tests for grr.parsers.wmi_parser."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.parsers import wmi_parser
from grr.test_data import client_fixture


class WMIParserTest(test_lib.FlowTestsBaseclass):

  def testInterfaceParsing(self):
    parser = wmi_parser.WMIInterfacesParser()
    rdf_dict = rdf_protodict.Dict()
    wmi_properties = (client_fixture.WMIWin32NetworkAdapterConfigurationMock.
                      __dict__.iteritems())
    for key, value in wmi_properties:
      if not key.startswith("__"):
        try:
          rdf_dict[key] = value
        except TypeError:
          rdf_dict[key] = "Failed to encode: %s" % value

    result_list = list(parser.Parse(
        None, rdf_dict, None))
    self.assertEqual(len(result_list), 2)
    for result in result_list:
      if isinstance(result, rdf_client.Interface):
        self.assertEqual(len(result.addresses), 4)
        self.assertItemsEqual(
            [x.human_readable_address for x in result.addresses],
            ["192.168.1.20", "ffff::ffff:aaaa:1111:aaaa",
             "dddd:0:8888:6666:bbbb:aaaa:eeee:bbbb",
             "dddd:0:8888:6666:bbbb:aaaa:ffff:bbbb"])

        self.assertItemsEqual(
            [x.human_readable_address for x in result.dhcp_server_list],
            ["192.168.1.1"])

        self.assertEqual(result.dhcp_lease_expires.AsMicroSecondsFromEpoch(),
                         1409008979123456)
        self.assertEqual(result.dhcp_lease_obtained.AsMicroSecondsFromEpoch(),
                         1408994579123456)

      elif isinstance(result, rdf_client.DNSClientConfiguration):
        self.assertItemsEqual(result.dns_server, ["192.168.1.1",
                                                  "192.168.255.81",
                                                  "192.168.128.88"])

        self.assertItemsEqual(result.dns_suffix, ["blah.example.com",
                                                  "ad.example.com",
                                                  "internal.example.com",
                                                  "example.com"])


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
