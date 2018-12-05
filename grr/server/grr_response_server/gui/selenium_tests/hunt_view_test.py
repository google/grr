#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the hunt_view interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import traceback


from grr_response_core.lib import flags
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestHuntView(gui_test_lib.GRRSeleniumHuntTest):
  """Test the Cron view GUI."""

  reason = "Felt like it!"

  def SetupTestHuntView(self, client_limit=0, client_count=10):
    # Create some clients and a hunt to view.
    with self.CreateSampleHunt(
        client_limit=client_limit, client_count=client_count) as hunt:
      hunt.Log("TestLogLine")

      # Log an error just with some random traceback.
      hunt.LogClientError(self.client_ids[1], "Client Error 1",
                          traceback.format_exc())

    # Run the hunt.
    client_mock = hunt_test_lib.SampleHuntMock()

    hunt_test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                                 self.token)

    hunt = aff4.FACTORY.Open(hunt.urn, token=self.token)
    all_count, _, _ = hunt.GetClientsCounts()
    if client_limit == 0:
      # No limit, so we should have all the clients
      self.assertEqual(all_count, client_count)
    else:
      self.assertEqual(all_count, min(client_count, client_limit))

    return hunt

  def testPageTitleReflectsSelectedHunt(self):
    hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/#/hunts")
    self.WaitUntilEqual("GRR | Hunts", self.GetPageTitle)

    self.Click("css=td:contains('GenericHunt')")
    self.WaitUntilEqual("GRR | " + hunt.urn.Basename(), self.GetPageTitle)

  def testHuntView(self):
    """Test that we can see all the hunt data."""
    self.SetupTestHuntView()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")

    # Click the Log Tab.
    self.Click("css=li[heading=Log]")
    self.WaitUntil(self.IsTextPresent, "TestLogLine")

    # Click the Error Tab.
    self.Click("css=li[heading=Errors]")
    self.WaitUntil(self.IsTextPresent, "Client Error 1")

  def SetupHuntDetailView(self, failrate=2):
    """Create some clients and a hunt to view."""
    with self.CreateSampleHunt() as hunt:
      hunt.LogClientError(self.client_ids[1], "Client Error 1",
                          traceback.format_exc())

    # Run the hunt.
    client_mock = hunt_test_lib.SampleHuntMock(failrate=failrate)
    hunt_test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                                 self.token)

    return hunt

  def testHuntClientsView(self):
    """Test the detailed client view works."""
    self._CreateHuntWithDownloadedFile()

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Overview Tab then the Details Link.
    self.Click("css=li[heading=Overview]")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")

    # Check the Hunt Clients tab.
    self.Click("css=li[heading=Clients]")

    client_id = self.client_ids[0]
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())

    self.RequestAndGrantClientApproval(client_id)

    # TODO(user): move the code below outside of if as soon as hunt's
    # subflows are properly reported in the REL_DB implementation.
    if not data_store.RelationalDBFlowsEnabled():
      self.Click(
          "css=tr:contains('%s') td:nth-of-type(2) a" % client_id.Basename())
      self.WaitUntil(self.IsTextPresent, "Flow Information")
      self.WaitUntil(self.IsTextPresent, self.base_path)

  def testHuntOverviewShowsBrokenHunt(self):
    hunt = self.CreateSampleHunt()
    broken_hunt = self.CreateSampleHunt()

    # Break the hunt.
    data_store.DB.DeleteAttributes(
        broken_hunt.urn,
        [broken_hunt.Schema.HUNT_ARGS, broken_hunt.Schema.HUNT_RUNNER_ARGS])
    data_store.DB.Flush()

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/#/hunts")

    hunt_id = hunt.urn.Basename()
    broken_hunt_id = broken_hunt.urn.Basename()

    # Both hunts are shown even though one throws an error.
    self.WaitUntil(self.IsTextPresent, hunt_id)
    self.WaitUntil(self.IsTextPresent, broken_hunt_id)

    self.Click("css=td:contains('%s')" % broken_hunt_id)
    self.WaitUntil(self.IsTextPresent, "Error while Opening")
    self.WaitUntil(self.IsTextPresent, "Error while opening hunt:")

  def testHuntOverviewShowsStats(self):
    """Test the detailed client view works."""
    with self.CreateSampleHunt() as hunt:
      hunt_stats = hunt.context.usage_stats
      hunt_stats.user_cpu_stats.sum = 5000
      hunt_stats.network_bytes_sent_stats.sum = 1000000

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Overview Tab and check that the stats are present.
    self.Click("css=li[heading=Overview]")
    self.WaitUntil(self.IsTextPresent, "1h 23m 20s")
    self.WaitUntil(self.IsTextPresent, "976.6KiB")

  def testHuntOverviewGetsUpdatedWhenHuntChanges(self):
    with self.CreateSampleHunt() as hunt:
      hunt_stats = hunt.context.usage_stats
      hunt_stats.user_cpu_stats.sum = 5000
      hunt_stats.network_bytes_sent_stats.sum = 1000000

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntOverviewDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")

    self.WaitUntil(self.IsTextPresent, "1h 23m 20s")
    self.WaitUntil(self.IsTextPresent, "976.6KiB")

    with aff4.FACTORY.Open(hunt.urn, mode="rw", token=self.token) as fd:
      fd.context.usage_stats.user_cpu_stats.sum = 6000
      fd.context.usage_stats.network_bytes_sent_stats.sum = 11000000

    self.WaitUntil(self.IsTextPresent, "1h 40m")
    self.WaitUntil(self.IsTextPresent, "10.5MiB")

  def testHuntStatsView(self):
    self.SetupTestHuntView()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Stats tab.
    self.Click("css=li[heading=Stats]")

    self.WaitUntil(self.IsTextPresent, "Total number of clients")
    self.WaitUntil(self.IsTextPresent, "10")

    self.WaitUntil(self.IsTextPresent, "User CPU mean")
    self.WaitUntil(self.IsTextPresent, "5.5")

    self.WaitUntil(self.IsTextPresent, "User CPU stdev")
    self.WaitUntil(self.IsTextPresent, "2.9")

    self.WaitUntil(self.IsTextPresent, "System CPU mean")
    self.WaitUntil(self.IsTextPresent, "11")

    self.WaitUntil(self.IsTextPresent, "System CPU stdev")
    self.WaitUntil(self.IsTextPresent, "5.7")

    self.WaitUntil(self.IsTextPresent, "Network bytes sent mean")
    self.WaitUntil(self.IsTextPresent, "16.5")

    self.WaitUntil(self.IsTextPresent, "Network bytes sent stdev")
    self.WaitUntil(self.IsTextPresent, "8.6")

  def testHuntNotificationIsShownAndClickable(self):
    hunt = self.CreateSampleHunt(
        path=os.path.join(self.base_path, "test.plist"))

    self.RequestAndGrantHuntApproval(hunt.urn.Basename())

    self.Open("/")

    self.Click("css=#notification_button")
    self.Click("css=a:contains('has granted you access')")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr.row-selected td:contains('GenericHunt')")
    self.WaitUntil(self.IsTextPresent, hunt.urn.Basename())

  def testLogsTabShowsLogsFromAllClients(self):
    self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, client_id.Basename())
      self.WaitUntil(
          self.IsTextPresent, "File %s transferred successfully." % str(
              client_id.Add("fs/os/tmp/evil.txt")))

  def testLogsTabGetsAutoRefreshed(self):
    h = self.CreateSampleHunt()
    h.Log("foo-log")

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntLogDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-log td:contains('foo-log')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-hunt-log td:contains('bar-log')")

    h.Log("bar-log")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-log td:contains('bar-log')")

  def testLogsTabFiltersLogsByString(self):
    self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    self.Type("css=grr-hunt-log input.search-query",
              self.client_ids[-1].Basename())
    self.Click("css=grr-hunt-log button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, self.client_ids[-1].Basename())
    self.WaitUntil(
        self.IsTextPresent, "File %s transferred successfully." % str(
            self.client_ids[-1].Add("fs/os/tmp/evil.txt")))

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, client_id.Basename())
      self.WaitUntilNot(
          self.IsTextPresent, "File %s transferred successfully." % str(
              client_id.Add("fs/os/tmp/evil.txt")))

  def testLogsTabShowsDatesInUTC(self):
    with self.CreateSampleHunt() as hunt:
      with test_lib.FakeTime(42):
        hunt.Log("I do log.")

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    self.WaitUntil(self.IsTextPresent, "1970-01-01 00:00:42 UTC")

  def testErrorsTabShowsErrorsFromAllClients(self):
    self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Errors]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, client_id.Basename())

  def testErrorsTabGetsAutoRefreshed(self):
    with self.CreateSampleHunt() as hunt:
      # Log an error just with some random traceback.
      hunt.LogClientError(self.client_ids[0], "foo-error",
                          traceback.format_exc())

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntErrorsDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Errors]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-errors td:contains('foo-error')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-hunt-errors td:contains('bar-error')")

    hunt.LogClientError(self.client_ids[0], "bar-error", traceback.format_exc())

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-errors td:contains('bar-error')")

  def testErrorsTabShowsDatesInUTC(self):
    with self.CreateSampleHunt() as hunt:
      with test_lib.FakeTime(42):
        # Log an error just with some random traceback.
        hunt.LogClientError(self.client_ids[0], "Client Error 1",
                            traceback.format_exc())

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Errors]")

    self.WaitUntil(self.IsTextPresent, "1970-01-01 00:00:42 UTC")

  def testErrorsTabFiltersErrorsByString(self):
    self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Errors]")

    self.Type("css=grr-hunt-errors input.search-query",
              self.client_ids[-1].Basename())
    self.Click("css=grr-hunt-errors button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, self.client_ids[-1].Basename())

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, client_id.Basename())

  def testCrashesTabShowsNoErrorWhenCrashesAreMissing(self):
    self.SetupHuntDetailView()

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Crashes]")

    self.WaitUntilNot(self.IsTextPresent, "Loading...")
    self.WaitUntilNot(self.IsVisible, "css=button#show_backtrace")

  def testCrashesTabGetsAutoRefreshed(self):
    client_ids = self.SetupClients(2)
    with self.CreateHunt(token=self.token) as hunt:
      hunt.Run()

    def CrashClient(client_id):
      self.AssignTasksToClients([client_id])
      client_mock = flow_test_lib.CrashClientMock(client_id, token=self.token)
      hunt_test_lib.TestHuntHelper(
          client_mock, [client_id], check_flow_errors=False, token=self.token)

    CrashClient(client_ids[0])

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntCrashesDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Crashes]")

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-hunt-crashes td:contains('%s')" % client_ids[0].Basename())
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=grr-hunt-crashes td:contains('%s')" % client_ids[1].Basename())

    CrashClient(client_ids[1])

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-hunt-crashes td:contains('%s')" % client_ids[1].Basename())

  def testShowsResultsTabForIndividualFlowsOnClients(self):
    # Create and run the hunt.
    self.CreateSampleHunt(stopped=False)
    client_mock = hunt_test_lib.SampleHuntMock(failrate=-1)
    hunt_test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                                 self.token)

    self.RequestAndGrantClientApproval(self.client_ids[0])

    self.Open("/#c=" + self.client_ids[0].Basename())
    self.Click("css=a:contains('Manage launched flows')")

    self.Click("css=grr-client-flows-list tr:contains('GetFile')")
    self.Click("css=li[heading=Results]")
    # This is to check that no exceptions happened when we tried to display
    # results.
    # TODO(user): Fail *any* test if we get a 500 in the process.
    self.WaitUntilNot(self.IsTextPresent, "Loading...")

  def testClientsTabShowsCompletedAndOutstandingClients(self):
    # Create some clients and a hunt to view.
    self.CreateSampleHunt()

    # Run the hunt on half the clients.
    finished_client_ids = self.client_ids[5:]
    outstanding_client_ids = self.client_ids[:5]

    client_mock = hunt_test_lib.SampleHuntMock()
    hunt_test_lib.TestHuntHelper(client_mock, finished_client_ids, False,
                                 self.token)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Clients]")

    self.Click("css=label[name=ShowCompletedClients]")
    for client_id in finished_client_ids:
      self.WaitUntilContains(client_id.Basename(), self.GetText,
                             "css=.tab-content")

    self.Click("css=label[name=ShowOutstandingClients]")
    for client_id in outstanding_client_ids:
      self.WaitUntilContains(client_id.Basename(), self.GetText,
                             "css=.tab-content")

  def testContextTabShowsHuntContext(self):
    # Create some clients and a hunt to view.
    self.CreateSampleHunt()

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading='Context Details']")

    # Check for different context properties.
    self.WaitUntilContains(
        self.hunt_urn.Basename(), self.GetText,
        "css=table > tbody td.proto_key:contains(\"Session id\") "
        "~ td.proto_value")
    self.WaitUntilContains(
        self.token.username, self.GetText,
        "css=table > tbody td.proto_key:contains(\"Creator\") "
        "~ td.proto_value")

  def testHuntCreatorIsNotifiedWhenHuntIsStoppedDueToCrashes(self):
    with self.CreateHunt(crash_limit=3, token=self.token) as hunt:
      hunt.Run()

      # Run the hunt on 3 clients, one by one. Crash detection check happens
      # when client is scheduled, so it's important to schedule the clients
      # one by one in the test.
      for client_id in self.SetupClients(3):
        self.AssignTasksToClients([client_id])
        client_mock = flow_test_lib.CrashClientMock(client_id, token=self.token)
        hunt_test_lib.TestHuntHelper(
            client_mock, [client_id], check_flow_errors=False, token=self.token)

    self.Open("/")

    # Wait until the notification is there and show the notifications list.
    self.WaitUntilEqual("1", self.GetText, "css=button[id=notification_button]")
    self.Click("css=button[id=notification_button]")

    # Click on the "hunt [id] reached the crashes limit" notificaiton.
    self.Click("css=td:contains(Hunt %s reached the crashes limit)" %
               hunt.urn.Basename())

    # Clicking on notification should shown the hunt's overview page.
    self.WaitUntil(self.IsTextPresent, "/tmp/evil.txt")

    # Go to the logs and check that a reason for hunt's stopping is the
    # hunts logs.
    # Click the Log Tab.
    self.Click("css=li[heading=Log]")
    self.WaitUntil(
        self.IsTextPresent,
        "Hunt %s reached the crashes limit of 3 and was stopped." %
        hunt.urn.Basename())


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
