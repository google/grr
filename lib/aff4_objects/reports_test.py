#!/usr/bin/env python
"""Reporting tests."""

from grr.lib import aff4
from grr.lib import test_lib
from grr.lib.aff4_objects import reports


class ReportsTest(test_lib.FlowTestsBaseclass):
  """Test the timeline implementation."""

  def testClientListReport(self):
    """Check that we can create and run a ClientList Report."""

    # Create some clients.
    client_ids = self.SetupClients(10)
    client1 = aff4.FACTORY.Open(client_ids[0], token=self.token, mode="rw")
    client1.Set(client1.Schema.HOSTNAME("lawman"))
    client1.Flush()

    # Create a report for all clients.
    rep = reports.ClientListReport(token=self.token)
    rep.Run()
    self.assertEqual(len(rep.results), 10)
    hostnames = [x.get("Host") for x in rep.results]
    self.assertTrue("lawman" in hostnames)

    rep.SortResults("Host")
    self.assertEqual(len(rep.AsDict()), 10)
    self.assertEqual(len(rep.AsCsv().getvalue().splitlines()), 11)
    self.assertEqual(len(rep.AsText().getvalue().splitlines()), 10)



