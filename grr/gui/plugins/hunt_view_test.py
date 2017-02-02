#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the hunt_view interface."""



import os
import traceback


import mock

from grr.gui import api_call_router_with_approval_checks
from grr.gui import gui_test_lib
from grr.gui import runtests_test
from grr.gui.api_plugins import hunt as api_hunt

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


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
    client_mock = test_lib.SampleHuntMock()

    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt = aff4.FACTORY.Open(hunt.urn, token=self.token)
    all_count, _, _ = hunt.GetClientsCounts()
    if client_limit == 0:
      # No limit, so we should have all the clients
      self.assertEqual(all_count, client_count)
    else:
      self.assertEqual(all_count, min(client_count, client_limit))

  def testPageTitleReflectsSelectedHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/#/hunts")
    self.WaitUntilEqual("GRR | Hunts", self.GetPageTitle)

    self.Click("css=td:contains('GenericHunt')")
    self.WaitUntilEqual("GRR | " + hunt.urn.Basename(), self.GetPageTitle)

  def testHuntView(self):
    """Test that we can see all the hunt data."""
    with self.ACLChecksDisabled():
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
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

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
    client_mock = test_lib.SampleHuntMock(failrate=failrate)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

  def testHuntClientsView(self):
    """Test the detailed client view works."""
    hunt = self._CreateHuntWithDownloadedFile()

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Overview Tab then the Details Link.
    self.Click("css=li[heading=Overview]")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    # Check the Hunt Clients tab.
    self.Click("css=li[heading=Clients]")

    client_id = self.client_ids[0]
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('%s')" % client_id.Basename())

    hunt_flows = list(
        aff4.FACTORY.ListChildren(
            hunt.urn.Add(client_id.Basename()), token=self.token))
    self.assertEqual(len(hunt_flows), 1)
    self.WaitUntil(self.IsTextPresent, utils.SmartStr(hunt_flows[0]))

  def testHuntOverviewShowsStats(self):
    """Test the detailed client view works."""
    with self.ACLChecksDisabled():
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
    self.WaitUntil(self.IsTextPresent, "5,000.00s")
    self.WaitUntil(self.IsTextPresent, "1,000,000b")

  def testHuntResultsView(self):
    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "aff4:/sample/1")
    self.WaitUntil(self.IsTextPresent,
                   "aff4:/C.0000000000000001/fs/os/c/bin/bash")
    self.WaitUntil(self.IsTextPresent, "aff4:/sample/3")

    with self.ACLChecksDisabled():
      self.RequestAndGrantClientApproval("C.0000000000000001")

    self.Click("link=aff4:/C.0000000000000001/fs/os/c/bin/bash")
    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a:contains('Browse Virtual Filesystem')")

  def testHuntStatsView(self):
    with self.ACLChecksDisabled():
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
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(
          path=os.path.join(self.base_path, "test.plist"))

      self.GrantHuntApproval(hunt.urn)

    self.Open("/")

    self.Click("css=#notification_button")
    self.Click("css=a:contains('has granted you access')")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr.row-selected td:contains('GenericHunt')")
    self.WaitUntil(self.IsTextPresent, str(hunt.urn))

  def testLogsTabShowsLogsFromAllClients(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, str(client_id))
      self.WaitUntil(self.IsTextPresent, "File %s transferred successfully." %
                     str(client_id.Add("fs/os/tmp/evil.txt")))

  def testLogsTabFiltersLogsByString(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    self.Type("css=grr-hunt-log input.search-query",
              self.client_ids[-1].Basename())
    self.Click("css=grr-hunt-log button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, str(self.client_ids[-1]))
    self.WaitUntil(self.IsTextPresent, "File %s transferred successfully." %
                   str(self.client_ids[-1].Add("fs/os/tmp/evil.txt")))

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, str(client_id))
      self.WaitUntilNot(self.IsTextPresent,
                        "File %s transferred successfully." %
                        str(client_id.Add("fs/os/tmp/evil.txt")))

  def testLogsTabShowsDatesInUTC(self):
    with self.ACLChecksDisabled():
      with self.CreateSampleHunt() as hunt:
        with test_lib.FakeTime(42):
          hunt.Log("I do log.")

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    self.WaitUntil(self.IsTextPresent, "1970-01-01 00:00:42 UTC")

  def testErrorsTabShowsErrorsFromAllClients(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Errors]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, str(client_id))

  def testErrorsTabShowsDatesInUTC(self):
    with self.ACLChecksDisabled():
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
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Errors]")

    self.Type("css=grr-hunt-errors input.search-query",
              self.client_ids[-1].Basename())
    self.Click("css=grr-hunt-errors button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, str(self.client_ids[-1]))

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, str(client_id))

  def testCrashesTabShowsNoErrorWhenCrashesAreMissing(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView()

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Crashes]")

    self.WaitUntilNot(self.IsTextPresent, "Loading...")
    self.WaitUntilNot(self.IsVisible, "css=button#show_backtrace")

  def testShowsResultsTabForIndividualFlowsOnClients(self):
    with self.ACLChecksDisabled():
      # Create and run the hunt.
      self.CreateSampleHunt(stopped=False)
      client_mock = test_lib.SampleHuntMock(failrate=-1)
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

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
    with self.ACLChecksDisabled():
      # Create some clients and a hunt to view.
      self.CreateSampleHunt()

    # Run the hunt on half the clients.
    finished_client_ids = self.client_ids[5:]
    outstanding_client_ids = self.client_ids[:5]

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, finished_client_ids, False, self.token)

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
    with self.ACLChecksDisabled():
      # Create some clients and a hunt to view.
      self.CreateSampleHunt()

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading='Context Details']")

    # Check for different context properties.
    self.WaitUntilContains(
        self.hunt_urn, self.GetText,
        "css=table > tbody td.proto_key:contains(\"Session id\") "
        "~ td.proto_value")
    self.WaitUntilContains(
        self.token.username, self.GetText,
        "css=table > tbody td.proto_key:contains(\"Creator\") "
        "~ td.proto_value")

  def testDownloadAsPanelNotShownForEmptyHuntResults(self):
    with self.ACLChecksDisabled():
      hunt_urn = self.CreateGenericHuntWithCollection([])

    self.Open("/#/hunts/%s/results" % hunt_urn.Basename())

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsElementPresent, "css=grr-download-collection-as")

  @mock.patch.object(api_call_router_with_approval_checks.
                     ApiCallRouterWithApprovalChecksWithRobotAccess,
                     "GetExportedHuntResults")
  def testHuntResultsCanBeDownloadedAsCsv(self, mock_method):
    with self.ACLChecksDisabled():
      hunt_urn = self.CreateGenericHuntWithCollection()

    self.Open("/#/hunts/%s/results" % hunt_urn.Basename())
    self.Click("css=grr-download-collection-as button[name='csv-zip']")

    def MockMethodIsCalled():
      try:
        mock_method.assert_called_once_with(
            api_hunt.ApiGetExportedHuntResultsArgs(
                hunt_id=hunt_urn.Basename(), plugin_name="csv-zip"),
            token=mock.ANY)

        return True
      except AssertionError:
        return False

    self.WaitUntil(MockMethodIsCalled)


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
