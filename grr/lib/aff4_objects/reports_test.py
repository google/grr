#!/usr/bin/env python
"""Reporting tests."""

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import reports
from grr.lib.rdfvalues import client as rdf_client


class ReportsTest(test_lib.AFF4ObjectTest):
  """Test the timeline implementation."""

  def testClientListReport(self):
    """Check that we can create and run a ClientList Report."""
    # Create some clients.
    client_ids = self.SetupClients(10)
    with aff4.FACTORY.Open(
        client_ids[0], token=self.token, mode="rw") as client:
      interfaces = client.Schema.INTERFACES()
      interfaces.Append(
          addresses=[rdf_client.NetworkAddress(
              human_readable="1.1.1.1", address_type="INET")],
          mac_address="11:11:11:11:11:11",
          ifname="eth0")
      client.Set(interfaces)
      client.Set(client.Schema.HOSTNAME("lawman"))

    # Also initialize a broken client with no hostname.
    with aff4.FACTORY.Open(
        client_ids[1], token=self.token, mode="rw") as client:
      client.Set(client.Schema.CLIENT_INFO())

    # Create a report for all clients.
    report = reports.ClientListReport(token=self.token)
    report.Run()
    self.assertEqual(len(report.results), 10)
    hostnames = [x.get("Host") for x in report.results]
    self.assertTrue("lawman" in hostnames)

    report.SortResults("Host")
    self.assertEqual(len(report.AsDict()), 10)
    self.assertEqual(len(report.AsCsv().getvalue().splitlines()), 11)
    self.assertEqual(len(report.AsText().getvalue().splitlines()), 10)
    self.assertEqual(report.results[-1]["Interfaces"], "1.1.1.1")

    self.assertEqual(len(report.broken_clients), 1)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
