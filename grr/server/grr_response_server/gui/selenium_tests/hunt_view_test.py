#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Test the hunt_view interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import traceback

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import hunt
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import test_lib


class TestHuntView(gui_test_lib.GRRSeleniumHuntTest):
  """Test the Cron view GUI."""

  reason = "Felt like it!"

  def SetupTestHuntView(self, client_limit=0, client_count=10):
    # Create some clients and a hunt to view.
    hunt_id = self.CreateSampleHunt(
        client_limit=client_limit, client_count=client_count)

    self.RunHunt(failrate=2)

    self.AddLogToHunt(hunt_id, self.client_ids[0], "TestLogLine")
    # Log an error just with some random traceback.
    self.AddErrorToHunt(hunt_id, self.client_ids[1], "Client Error 1",
                        traceback.format_exc())

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    if client_limit == 0:
      self.assertEqual(hunt_counters.num_clients, client_count)
    else:
      self.assertEqual(hunt_counters.num_clients, min(client_count,
                                                      client_limit))

    return hunt_id

  def testPageTitleReflectsSelectedHunt(self):
    hunt_id = self.CreateSampleHunt(stopped=True)

    self.Open("/#/hunts")
    self.WaitUntilEqual("GRR | Hunts", self.GetPageTitle)

    self.Click("css=td:contains('%s')" % hunt_id)
    self.WaitUntilEqual("GRR | " + hunt_id, self.GetPageTitle)

  def testHuntView(self):
    """Test that we can see all the hunt data."""
    hunt_id = self.SetupTestHuntView()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, hunt_id)

    # Select a Hunt.
    self.Click("css=td:contains('%s')" % hunt_id)

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
    hunt_id = self.CreateSampleHunt()

    self.RunHunt(client_ids=self.client_ids, failrate=failrate)

    self.AddErrorToHunt(hunt_id, self.client_ids[1], "Client Error 1",
                        traceback.format_exc())

    return hunt_id

  def testHuntClientsView(self):
    """Test the detailed client view works."""
    hunt_id = self._CreateHuntWithDownloadedFile()

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, hunt_id)
    self.Click("css=td:contains('%s')" % hunt_id)

    # Click the Overview Tab then the Details Link.
    self.Click("css=li[heading=Overview]")
    self.WaitUntil(self.IsTextPresent, "Hunt ID")

    # Check the Hunt Clients tab.
    self.Click("css=li[heading=Clients]")

    client_id = self.client_ids[0]
    self.WaitUntil(self.IsElementPresent, "css=tr:contains('%s')" % client_id)

    self.RequestAndGrantClientApproval(client_id)

    # TODO(user): move the code below outside of if as soon as hunt's
    # subflows are properly reported in the REL_DB implementation.
    self.Click("css=tr:contains('%s') td:nth-of-type(2) a" % client_id)
    self.WaitUntil(self.IsTextPresent, "Flow Information")
    self.WaitUntil(self.IsTextPresent, self.base_path)

  def testHuntOverviewShowsStats(self):
    """Test the detailed client view works."""
    hunt_id = self.CreateSampleHunt()
    client_id = self.SetupClient(0)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow.RandomFlowId(),
        parent_hunt_id=hunt_id,
        create_time=rdfvalue.RDFDatetime.Now())
    rdf_flow.cpu_time_used.user_cpu_time = 5000
    rdf_flow.network_bytes_sent = 1000000
    data_store.REL_DB.WriteFlowObject(rdf_flow)

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, hunt_id)
    self.Click("css=td:contains('%s')" % hunt_id)

    # Click the Overview Tab and check that the stats are present.
    self.Click("css=li[heading=Overview]")
    self.WaitUntil(self.IsTextPresent, "1h 23m 20s")
    self.WaitUntil(self.IsTextPresent, "976.6KiB")

  def testHuntOverviewGetsUpdatedWhenHuntChanges(self):
    hunt_id = self.CreateSampleHunt()
    client_id = self.SetupClient(0)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow.RandomFlowId(),
        parent_hunt_id=hunt_id,
        create_time=rdfvalue.RDFDatetime.Now())
    rdf_flow.cpu_time_used.user_cpu_time = 5000
    rdf_flow.network_bytes_sent = 1000000
    data_store.REL_DB.WriteFlowObject(rdf_flow)

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntOverviewDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)

    self.WaitUntil(self.IsTextPresent, "1h 23m 20s")
    self.WaitUntil(self.IsTextPresent, "976.6KiB")

    client_id = self.SetupClient(1)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow.RandomFlowId(),
        parent_hunt_id=hunt_id,
        create_time=rdfvalue.RDFDatetime.Now())
    rdf_flow.cpu_time_used.user_cpu_time = 1000
    rdf_flow.network_bytes_sent = 10000000
    data_store.REL_DB.WriteFlowObject(rdf_flow)

    self.WaitUntil(self.IsTextPresent, "1h 40m")
    self.WaitUntil(self.IsTextPresent, "10.5MiB")

  def testHuntOverviewShowsStartAndExpirationTime(self):
    duration = rdfvalue.Duration.From(3, rdfvalue.DAYS)
    init_start_time = rdfvalue.RDFDatetime.FromHumanReadable("1973-01-01 08:34")
    last_start_time = rdfvalue.RDFDatetime.FromHumanReadable("1981-03-04 12:52")
    expiration_time = init_start_time + duration

    hunt_id = self.CreateHunt(duration=duration)

    # Navigate to the hunt view.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, hunt_id)

    # Select the hunt.
    self.Click("css=td:contains('{}')".format(hunt_id))

    self.RequestAndGrantHuntApproval(hunt_id)

    self.assertFalse(self.IsTextPresent(str(init_start_time)))
    self.assertFalse(self.IsTextPresent(str(expiration_time)))
    self.assertFalse(self.IsTextPresent(str(last_start_time)))

    with test_lib.FakeTime(init_start_time):
      hunt.StartHunt(hunt_id)

    self.Refresh()
    self.WaitUntil(self.IsTextPresent, str(init_start_time))
    self.WaitUntil(self.IsTextPresent, str(expiration_time))
    self.assertFalse(self.IsTextPresent(str(last_start_time)))

    with test_lib.FakeTime(last_start_time):
      hunt.PauseHunt(hunt_id)
      hunt.StartHunt(hunt_id)

    self.Refresh()
    self.WaitUntil(self.IsTextPresent, str(init_start_time))
    self.WaitUntil(self.IsTextPresent, str(expiration_time))
    self.WaitUntil(self.IsTextPresent, str(last_start_time))

  def testHuntListShowsStartAndExpirationTime(self):
    hunt_1_start_time = rdfvalue.RDFDatetime.FromHumanReadable("1992-11-11")
    hunt_2_start_time = rdfvalue.RDFDatetime.FromHumanReadable("2001-05-03")

    hunt_1_duration = rdfvalue.Duration.From(3, rdfvalue.DAYS)
    hunt_2_duration = rdfvalue.Duration.From(5, rdfvalue.HOURS)

    hunt_1_expiration_time = hunt_1_start_time + hunt_1_duration
    hunt_2_expiration_time = hunt_2_start_time + hunt_2_duration

    hunt_1_id = self.CreateHunt(duration=hunt_1_duration)
    hunt_2_id = self.CreateHunt(duration=hunt_2_duration)

    # Navigate to the hunt list.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, hunt_1_id)
    self.WaitUntil(self.IsTextPresent, hunt_2_id)

    self.assertFalse(self.IsTextPresent(str(hunt_1_start_time)))
    self.assertFalse(self.IsTextPresent(str(hunt_1_expiration_time)))
    self.assertFalse(self.IsTextPresent(str(hunt_2_start_time)))
    self.assertFalse(self.IsTextPresent(str(hunt_2_expiration_time)))

    with test_lib.FakeTime(hunt_1_start_time):
      hunt.StartHunt(hunt_1_id)

    self.Refresh()
    self.WaitUntil(self.IsTextPresent, str(hunt_1_start_time))
    self.WaitUntil(self.IsTextPresent, str(hunt_1_expiration_time))
    self.assertFalse(self.IsTextPresent(str(hunt_2_start_time)))
    self.assertFalse(self.IsTextPresent(str(hunt_2_expiration_time)))

    with test_lib.FakeTime(hunt_2_start_time):
      hunt.StartHunt(hunt_2_id)

    self.Refresh()
    self.WaitUntil(self.IsTextPresent, str(hunt_1_start_time))
    self.WaitUntil(self.IsTextPresent, str(hunt_1_expiration_time))
    self.WaitUntil(self.IsTextPresent, str(hunt_2_start_time))
    self.WaitUntil(self.IsTextPresent, str(hunt_2_expiration_time))

  def testHuntStatsView(self):
    hunt_id = self.SetupTestHuntView()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, hunt_id)
    self.Click("css=td:contains('%s')" % hunt_id)

    # Click the Stats tab.
    self.Click("css=li[heading=Stats]")

    self.WaitUntil(self.IsTextPresent, "Total number of clients")
    self.WaitUntil(self.IsTextPresent, "10")

    self.WaitUntil(self.IsTextPresent, "User CPU mean")
    self.WaitUntil(self.IsTextPresent, "5.5")

    self.WaitUntil(self.IsTextPresent, "User CPU stddev")
    self.WaitUntil(self.IsTextPresent, "2.9")

    self.WaitUntil(self.IsTextPresent, "System CPU mean")
    self.WaitUntil(self.IsTextPresent, "11")

    self.WaitUntil(self.IsTextPresent, "System CPU stddev")
    self.WaitUntil(self.IsTextPresent, "5.7")

    self.WaitUntil(self.IsTextPresent, "Network bytes sent mean")
    self.WaitUntil(self.IsTextPresent, "16.5")

    self.WaitUntil(self.IsTextPresent, "Network bytes sent stddev")
    self.WaitUntil(self.IsTextPresent, "8.6")

  def testHuntNotificationIsShownAndClickable(self):
    hunt_id = self.CreateSampleHunt(
        path=os.path.join(self.base_path, "test.plist"))

    self.RequestAndGrantHuntApproval(hunt_id)

    self.Open("/")

    self.Click("css=#notification_button")
    self.Click("css=a:contains('has granted you access')")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr.row-selected td:contains('%s')" % hunt_id)
    self.WaitUntil(self.IsTextPresent, hunt_id)

  def testLogsTabShowsLogsFromAllClients(self):
    hunt_id = self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Log]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, client_id)
      # TODO(amoser): Get rid of the aff4 prefix here.
      self.WaitUntil(
          self.IsTextPresent, "File aff4:/%s/%s transferred successfully." %
          (client_id, "fs/os/tmp/evil.txt"))

  def testLogsTabGetsAutoRefreshed(self):
    hunt_id = self.CreateSampleHunt()
    self.AddLogToHunt(hunt_id, self.client_ids[0], "foo-log")

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntLogDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Log]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-log td:contains('foo-log')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-hunt-log td:contains('bar-log')")

    self.AddLogToHunt(hunt_id, self.client_ids[1], "bar-log")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-log td:contains('bar-log')")

  def testLogsTabFiltersLogsByString(self):
    hunt_id = self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Log]")

    self.Type("css=grr-hunt-log input.search-query", self.client_ids[-1])
    self.Click("css=grr-hunt-log button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, self.client_ids[-1])
    # TODO(amoser): Get rid of the aff4 prefix here.
    self.WaitUntil(
        self.IsTextPresent, "File aff4:/%s/%s transferred successfully." %
        (self.client_ids[-1], "fs/os/tmp/evil.txt"))

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, client_id)
      self.WaitUntilNot(
          self.IsTextPresent, "File %s/%s transferred successfully." %
          (client_id, "fs/os/tmp/evil.txt"))

  def testLogsTabShowsDatesInUTC(self):
    hunt_id = self.CreateSampleHunt()
    with test_lib.FakeTime(42):
      self.AddLogToHunt(hunt_id, self.client_ids[0], "I do log.")

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Log]")

    self.WaitUntil(self.IsTextPresent, "1970-01-01 00:00:42 UTC")

  def testErrorsTabShowsErrorsFromAllClients(self):
    hunt_id = self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Errors]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, client_id)

  def testErrorsTabGetsAutoRefreshed(self):
    hunt_id = self.CreateSampleHunt()
    self.AddErrorToHunt(hunt_id, self.client_ids[0], "foo-error",
                        traceback.format_exc())

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntErrorsDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Errors]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-errors td:contains('foo-error')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-hunt-errors td:contains('bar-error')")

    self.AddErrorToHunt(hunt_id, self.client_ids[0], "bar-error",
                        traceback.format_exc())

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-errors td:contains('bar-error')")

  def testErrorsTabShowsDatesInUTC(self):
    hunt_id = self.CreateSampleHunt()
    with test_lib.FakeTime(42):
      self.AddErrorToHunt(hunt_id, self.client_ids[0], "Client Error 1",
                          traceback.format_exc())

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Errors]")

    self.WaitUntil(self.IsTextPresent, "1970-01-01 00:00:42 UTC")

  def testErrorsTabFiltersErrorsByString(self):
    hunt_id = self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Errors]")

    self.Type("css=grr-hunt-errors input.search-query", self.client_ids[-1])
    self.Click("css=grr-hunt-errors button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, self.client_ids[-1])

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, client_id)

  def testCrashesTabShowsNoErrorWhenCrashesAreMissing(self):
    hunt_id = self.SetupHuntDetailView()

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Crashes]")

    self.WaitUntilNot(self.IsTextPresent, "Loading...")
    self.WaitUntilNot(self.IsVisible, "css=button#show_backtrace")

  def testCrashesTabGetsAutoRefreshed(self):
    client_ids = self.SetupClients(2)
    hunt_id = self.StartHunt()

    self.RunHuntWithClientCrashes([client_ids[0]])

    self.Open("/")
    # Ensure auto-refresh updates happen every second.
    self.GetJavaScriptValue(
        "grrUi.hunt.huntCrashesDirective.setAutoRefreshInterval(1000);")

    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Crashes]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-crashes td:contains('%s')" % client_ids[0])
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-hunt-crashes td:contains('%s')" % client_ids[1])

    self.RunHuntWithClientCrashes([client_ids[1]])

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-hunt-crashes td:contains('%s')" % client_ids[1])

  def testShowsResultsTabForIndividualFlowsOnClients(self):
    # Create and run the hunt.
    self.CreateSampleHunt(stopped=False)
    self.RunHunt(client_ids=self.client_ids, failrate=-1)

    self.RequestAndGrantClientApproval(self.client_ids[0])

    self.Open("/#c=" + self.client_ids[0])
    self.Click("css=a:contains('Manage launched flows')")

    self.Click("css=grr-client-flows-list tr:contains('GetFile')")
    self.Click("css=li[heading=Results]")
    # This is to check that no exceptions happened when we tried to display
    # results.
    self.WaitUntilNot(self.IsTextPresent, "Loading...")

  def testClientsTabShowsCompletedAndOutstandingClients(self):
    # Create some clients and a hunt to view.
    hunt_id = self.CreateSampleHunt()

    # Run the hunt on half the clients.
    finished_client_ids = self.client_ids[5:]
    outstanding_client_ids = self.client_ids[:5]

    self.AssignTasksToClients(client_ids=outstanding_client_ids)
    self.RunHunt(failrate=2, client_ids=finished_client_ids)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading=Clients]")

    self.Click("css=label[name=ShowCompletedClients]")
    for client_id in finished_client_ids:
      self.WaitUntilContains(client_id, self.GetText, "css=.tab-content")

    self.Click("css=label[name=ShowOutstandingClients]")
    for client_id in outstanding_client_ids:
      self.WaitUntilContains(client_id, self.GetText, "css=.tab-content")

  def testContextTabShowsHuntContext(self):
    # Create some clients and a hunt to view.
    hunt_id = self.CreateSampleHunt()

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('%s')" % hunt_id)
    self.Click("css=li[heading='Context Details']")

    # Check for different context properties.
    self.WaitUntilContains(
        hunt_id, self.GetText,
        "css=table > tbody td.proto_key:contains(\"Session id\") "
        "~ td.proto_value")
    self.WaitUntilContains(
        self.token.username, self.GetText,
        "css=table > tbody td.proto_key:contains(\"Creator\") "
        "~ td.proto_value")

  def testHuntCreatorIsNotifiedWhenHuntIsStoppedDueToCrashes(self):
    hunt_id = self.StartHunt(crash_limit=3, creator=self.token.username)

    # Run the hunt on 3 clients, one by one. Crash detection check happens
    # when client is scheduled, so it's important to schedule the clients
    # one by one in the test.
    for client_id in self.SetupClients(3):
      self.RunHuntWithClientCrashes([client_id])

    self.Open("/")

    # Wait until the notification is there and show the notifications list.
    self.WaitUntilEqual("1", self.GetText, "css=button[id=notification_button]")
    self.Click("css=button[id=notification_button]")

    # Click on the "hunt [id] reached the crashes limit" notificaiton.
    self.Click("css=td:contains(Hunt %s reached the crashes limit)" % hunt_id)

    # Clicking on notification should shown the hunt's overview page.
    self.WaitUntil(self.IsTextPresent, "/tmp/evil.txt")

    # TODO(user): display hunt.hunt_state_comment in the UI.


if __name__ == "__main__":
  app.run(test_lib.main)
