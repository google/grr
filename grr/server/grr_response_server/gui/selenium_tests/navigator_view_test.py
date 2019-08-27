#!/usr/bin/env python
"""Navigator view tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestNavigatorView(gui_test_lib.SearchClientTestBase):
  """Tests for NavigatorView (left side bar)."""

  def CreateClient(self, last_ping=None):
    if last_ping is None:
      last_ping = rdfvalue.RDFDatetime.Now()

    client_id = self.SetupClient(0, ping=last_ping)
    self.RequestAndGrantClientApproval(client_id)

    return client_id

  def RecordCrash(self, client_id, timestamp):
    with test_lib.FakeTime(timestamp):
      client = flow_test_lib.CrashClientMock(client_id, self.token)
      flow_test_lib.TestFlowHelper(
          flow_test_lib.FlowWithOneClientRequest.__name__,
          client,
          client_id=client_id,
          token=self.token,
          check_flow_errors=False)

  def CreateClientWithVolumes(self, available=50):
    volume = rdf_client_fs.Volume(
        total_allocation_units=100, actual_available_allocation_units=available)

    client_id = self.SetupClient(0)

    snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    snapshot.volumes = [volume]
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    self.RequestAndGrantClientApproval(client_id)

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
    client_id = self.CreateClient(last_ping=rdfvalue.RDFDatetime.Now() -
                                  rdfvalue.Duration.From(1, rdfvalue.HOURS))
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='online-1d.png']")

  def testOfflineClientStatus(self):
    client_id = self.CreateClient(last_ping=rdfvalue.RDFDatetime.Now() -
                                  rdfvalue.Duration.From(1, rdfvalue.DAYS))
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsElementPresent, "css=img[src$='offline.png']")

  def testOnlineClientStatusInClientSearch(self):
    client_id = self.CreateClient()

    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    self.WaitUntil(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='online.png']" % client_id)

  def testOneDayClientStatusInClientSearch(self):
    client_id = self.CreateClient(last_ping=rdfvalue.RDFDatetime.Now() -
                                  rdfvalue.Duration.From(1, rdfvalue.HOURS))

    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    self.WaitUntil(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='online-1d.png']" % client_id)

  def testOfflineClientStatusInClientSearch(self):
    client_id = self.CreateClient(last_ping=rdfvalue.RDFDatetime.Now() -
                                  rdfvalue.Duration.From(1, rdfvalue.DAYS))

    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    self.WaitUntil(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='offline.png']" % client_id)

  def testLatestCrashesStatusIsNotDisplayedWhenThereAreNoCrashes(self):
    client_id = self.CreateClient()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntilNot(self.IsTextPresent, "Last crash")

  def testCrashIsDisplayedInClientStatus(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient(last_ping=timestamp)
    self.RecordCrash(client_id,
                     timestamp - rdfvalue.Duration.From(5, rdfvalue.SECONDS))
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Last crash")
    self.WaitUntilContains("seconds", self.GetText,
                           "css=grr-client-summary .last-crash")

  def testOnlyTheLatestCrashIsDisplayed(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient(last_ping=timestamp)
    self.RecordCrash(client_id,
                     timestamp - rdfvalue.Duration.From(2, rdfvalue.HOURS))
    self.RecordCrash(client_id,
                     timestamp - rdfvalue.Duration.From(5, rdfvalue.SECONDS))
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Last crash")
    self.WaitUntilContains("seconds", self.GetText,
                           "css=grr-client-summary .last-crash")

  def testOnlyCrashesHappenedInPastWeekAreDisplayed(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient(last_ping=timestamp)
    self.RecordCrash(client_id,
                     timestamp - rdfvalue.Duration.From(8, rdfvalue.DAYS))
    self.RequestAndGrantClientApproval(client_id)

    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    # This one is not displayed, because it happened more than 24 hours ago.
    self.WaitUntilNot(self.IsTextPresent, "Last crash")

  def testCrashIconDoesNotAppearInClientSearchWhenClientDidNotCrash(self):
    client_id = self.CreateClient()

    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s')" % client_id)
    # But it shouldn't have the skull.
    self.WaitUntilNot(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='skull-icon.png']" % client_id)

  def testCrashIconDoesNotAppearInClientSearchIfClientCrashedLongTimeAgo(self):
    client_id = self.CreateClient()
    self.RecordCrash(
        client_id,
        rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(25, rdfvalue.HOURS))

    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s')" % client_id)
    # But it shouldn't have the skull.
    self.WaitUntilNot(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='skull-icon.png']" % client_id)

  def testCrashIconAppearsInClientSearchIfClientCrashedRecently(self):
    timestamp = rdfvalue.RDFDatetime.Now()
    client_id = self.CreateClient()
    self.RecordCrash(client_id, timestamp)

    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s')" % client_id)
    # And it should have the skull.
    self.WaitUntil(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='skull-icon.png']" % client_id)

  def testDiskIconDoesNotAppearInClientSearchIfDiskIsNotFull(self):
    client_id = self.CreateClientWithVolumes()
    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s')" % client_id)

    # But it shouldn't have the disk icon.
    self.WaitUntilNot(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='hdd-bang-icon.png']" % client_id)

  def testDiskIconDoesAppearsInClientSearchIfDiskIsFull(self):
    client_id = self.CreateClientWithVolumes(available=1)
    self.Open("/")
    self.Type("client_query", client_id)
    self.Click("client_query_submit")

    # There should be a result row with the client id.
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s')" % client_id)

    # With the disk icon.
    self.WaitUntil(
        self.IsElementPresent, "css=tr:contains('%s') "
        "img[src$='hdd-bang-icon.png']" % client_id)

  def testDiskWarningIsNotDisplayed(self):
    client_id = self.CreateClientWithVolumes()
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=img[name='clientDiskWarnings']")

  def testDiskWarningIsDisplayed(self):
    client_id = self.CreateClientWithVolumes(available=1)
    self.Open("/#c=" + str(client_id))
    self.WaitUntil(self.IsTextPresent, "Host-0")
    self.WaitUntil(self.IsElementPresent, "css=img[name='clientDiskWarnings']")


if __name__ == "__main__":
  app.run(test_lib.main)
