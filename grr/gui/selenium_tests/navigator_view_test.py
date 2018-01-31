#!/usr/bin/env python
"""Navigator view tests."""

import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestNavigatorView(gui_test_lib.SearchClientTestBase):
  """Tests for NavigatorView (left side bar)."""

  def CreateClient(self, last_ping=None):
    if last_ping is None:
      last_ping = rdfvalue.RDFDatetime.Now()

    client_id = self.SetupClient(0)
    with aff4.FACTORY.Open(
        client_id, mode="rw", token=self.token) as client_obj:
      client_obj.Set(client_obj.Schema.PING(last_ping))

    self.RequestAndGrantClientApproval(client_id)

    client_obj = aff4.FACTORY.Open(client_id, token=self.token)
    return client_id

  def RecordCrash(self, client_id, timestamp):
    with test_lib.FakeTime(timestamp):
      client = flow_test_lib.CrashClientMock(client_id, self.token)
      for _ in flow_test_lib.TestFlowHelper(
          flow_test_lib.FlowWithOneClientRequest.__name__,
          client,
          client_id=client_id,
          token=self.token,
          check_flow_errors=False):
        pass

  def CreateClientWithVolumes(self, available=50):
    client_id = self.SetupClient(0)
    with aff4.FACTORY.Open(
        client_id, mode="rw", token=self.token) as client_obj:
      volume = rdf_client.Volume(
          total_allocation_units=100,
          actual_available_allocation_units=available)
      client_obj.Set(client_obj.Schema.VOLUMES([volume]))

    self.RequestAndGrantClientApproval(client_id)

    client_obj = aff4.FACTORY.Open(client_id, token=self.token)
    return client_id

  def testReasonIsShown(self):
    client_id = self.CreateClient()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Access reason: " + self.token.reason)

  def testOnlineClientStatus(self):
    client_id = self.CreateClient()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='online.png']")

  def testOneDayClientStatus(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1h"))
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='online-1d.png']")

  def testOfflineClientStatus(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d"))
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='offline.png']")

  def testOnlineClientStatusInClientSearch(self):
    client_id = self.CreateClient()

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s') "
                   "img[src$='online.png']" % client_id.Basename())

  def testOneDayClientStatusInClientSearch(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1h"))

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s') "
                   "img[src$='online-1d.png']" % client_id.Basename())

  def testOfflineClientStatusInClientSearch(self):
    client_id = self.CreateClient(
        last_ping=rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d"))

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s') "
                   "img[src$='offline.png']" % client_id.Basename())

  def testLatestCrashesStatusIsNotDisplayedWhenThereAreNoCrashes(self):
    client_id = self.CreateClient()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntilNot(self.IsTextPresent, "Last crash")

  def testCrashIsDisplayedInClientStatus(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient(last_ping=timestamp)
    self.RecordCrash(client_id, timestamp - rdfvalue.Duration("5s"))
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Last crash")
    self.WaitUntilContains("seconds", self.GetText,
                           "css=grr-client-summary .last-crash")

  def testOnlyTheLatestCrashIsDisplayed(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient(last_ping=timestamp)
    self.RecordCrash(client_id, timestamp - rdfvalue.Duration("2h"))
    self.RecordCrash(client_id, timestamp - rdfvalue.Duration("5s"))
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Last crash")
    self.WaitUntilContains("seconds", self.GetText,
                           "css=grr-client-summary .last-crash")

  def testOnlyCrashesHappenedInPastWeekAreDisplayed(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient(last_ping=timestamp)
    self.RecordCrash(client_id, timestamp - rdfvalue.Duration("8d"))
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    # This one is not displayed, because it happened more than 24 hours ago.
    self.WaitUntilNot(self.IsTextPresent, "Last crash")

  def testCrashIconDoesNotAppearInClientSearchWhenClientDidNotCrash(self):
    client_id = self.CreateClient()

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())
    # But it shouldn't have the skull.
    self.WaitUntilNot(self.IsElementPresent, "css=tr:contains('%s') "
                      "img[src$='skull-icon.png']" % client_id.Basename())

  def testCrashIconDoesNotAppearInClientSearchIfClientCrashedLongTimeAgo(self):
    client_id = self.CreateClient()
    self.RecordCrash(client_id,
                     rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("25h"))

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())
    # But it shouldn't have the skull.
    self.WaitUntilNot(self.IsElementPresent, "css=tr:contains('%s') "
                      "img[src$='skull-icon.png']" % client_id.Basename())

  def testCrashIconAppearsInClientSearchIfClientCrashedRecently(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient()
    self.RecordCrash(client_id, timestamp)

    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())
    # And it should have the skull.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s') "
                   "img[src$='skull-icon.png']" % client_id.Basename())

  def testDiskIconDoesNotAppearInClientSearchIfDiskIsNotFull(self):
    client_id = self.CreateClientWithVolumes()
    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())

    # But it shouldn't have the disk icon.
    self.WaitUntilNot(self.IsElementPresent, "css=tr:contains('%s') "
                      "img[src$='hdd-bang-icon.png']" % client_id.Basename())

  def testDiskIconDoesAppearsInClientSearchIfDiskIsFull(self):
    client_id = self.CreateClientWithVolumes(available=1)
    self.Open("/")
    self.Type("client_query", client_id.Basename())
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())

    # With the disk icon.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s') "
                   "img[src$='hdd-bang-icon.png']" % client_id.Basename())

  def testDiskWarningIsNotDisplayed(self):
    client_id = self.CreateClientWithVolumes()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntilNot(self.IsTextPresent, "Disk free space")

  def testDiskWarningIsDisplayed(self):
    client_id = self.CreateClientWithVolumes(available=1)
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntil(self.IsTextPresent, "Disk free space")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
