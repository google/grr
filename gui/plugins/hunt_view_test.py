#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test the hunt_view interface."""



import traceback

from grr.gui import runtests_test

from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestHuntView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  reason = "Felt like it!"

  def CreateSampleHunt(self, flow_runner_args=None, flow_args=None,
                       stopped=False, output_plugins=None):
    self.client_ids = self.SetupClients(10)

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(
            flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=output_plugins or [],
        client_rate=0, token=self.token) as hunt:
      if not stopped:
        hunt.Run()

    with aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                           token=self.token) as foreman:

      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    self.hunt_urn = hunt.urn
    return aff4.FACTORY.Open(hunt.urn, mode="rw", token=self.token,
                             age=aff4.ALL_TIMES)

  def CreateGenericHuntWithCollection(self, values=None):
    self.client_ids = self.SetupClients(10)

    if values is None:
      values = [rdfvalue.RDFURN("aff4:/sample/1"),
                rdfvalue.RDFURN("aff4:/C.0000000000000001/fs/os/c/bin/bash"),
                rdfvalue.RDFURN("aff4:/sample/3")]

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=[],
        token=self.token) as hunt:

      runner = hunt.GetRunner()
      runner.Start()

      with aff4.FACTORY.Create(
          runner.context.results_collection_urn,
          aff4_type="RDFValueCollection", mode="w",
          token=self.token) as collection:

        for value in values:
          collection.Add(value)

      return hunt.urn

  def SetupTestHuntView(self):
    # Create some clients and a hunt to view.
    with self.CreateSampleHunt() as hunt:
      hunt.Log("TestLogLine")

      # Log an error just with some random traceback.
      hunt.LogClientError(self.client_ids[1], "Client Error 1",
                          traceback.format_exc())

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()

    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt = aff4.FACTORY.Open(hunt.urn, token=self.token)
    all_count, _, _ = hunt.GetClientsCounts()
    self.assertEqual(all_count, 10)

  def CheckState(self, state):
    self.WaitUntil(self.IsElementPresent, "css=div[state=\"%s\"]" % state)

  def testHuntView(self):
    """Test that we can see all the hunt data."""
    with self.ACLChecksDisabled():
      self.SetupTestHuntView()

    # Open up and click on View Hunts.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")
    self.WaitUntil(self.IsTextPresent, "Regex Rules")
    self.WaitUntil(self.IsTextPresent, "Integer Rules")

    # Click the Log Tab.
    self.Click("css=a[renderer=HuntLogRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntLogRenderer_]")
    self.WaitUntil(self.IsTextPresent, "TestLogLine")

    # Click the Error Tab.
    self.Click("css=a[renderer=HuntErrorRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntErrorRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Client Error 1")

  def testToolbarStateForStoppedHunt(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RunHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=PauseHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt]:not([disabled])")

  def testToolbarStateForRunningHunt(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Check we can now see the details.
    self.WaitUntil(self.IsElementPresent, "css=dl.dl-hunt")
    self.WaitUntil(self.IsTextPresent, "Clients Scheduled")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RunHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=PauseHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt][disabled]")

  def testRunHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Run button and check that dialog appears.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent,
                   "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.urn)

    # Click on Run and wait for dialog again.
    self.Click("css=button[name=RunHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to run this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt started successfully!")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    # Check the hunt is in a running state.
    self.CheckState("STARTED")

  def testPauseHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Pause button and check that dialog appears.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent,
                   "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")

    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.session_id)

    # Click on Pause and wait for dialog again.
    self.Click("css=button[name=PauseHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to pause this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt paused successfully")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible,
                      "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Check the hunt is not in a running state.
    self.CheckState("PAUSED")

  def testModifyHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")

    self.Type("css=input[id=v_-client_limit]", "4483")
    self.Type("css=input[id=v_-expiry_time]", str(
        rdfvalue.Duration("5m").Expiry()))

    # Click on Proceed.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # Now create an approval.
    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.session_id)

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")

    self.Type("css=input[id=v_-client_limit]", "4483")
    self.Type("css=input[id=v_-expiry_time]", str(
        rdfvalue.Duration("5m").Expiry()))

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, "4483")

  def SetupHuntDetailView(self, failrate=2):
    """Create some clients and a hunt to view."""
    with self.CreateSampleHunt() as hunt:
      hunt.LogClientError(self.client_ids[1], "Client Error 1",
                          traceback.format_exc())

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock(failrate=failrate)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

  def testHuntDetailView(self):
    """Test the detailed client view works."""
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=-1)

    # Open up and click on View Hunts then the first Hunt.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Overview Tab then the Details Link.
    self.Click("css=a[renderer=HuntOverviewRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntOverviewRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")
    self.Click("css=a[id^=ViewHuntDetails_]")
    self.WaitUntil(self.IsTextPresent, "Viewing Hunt aff4:/hunts/")

    self.WaitUntil(self.IsTextPresent, "COMPLETED")

    # Select the first client which should have errors.
    self.Click("css=td:contains('%s')" % self.client_ids[1].Basename())
    self.WaitUntil(self.IsElementPresent,
                   "css=div[id^=HuntClientOverviewRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Last Checkin")

    self.Click("css=a[renderer=HuntLogRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntLogRenderer_]")
    self.WaitUntil(self.IsTextPresent, "GetFile Flow Completed")

    self.Click("css=a[renderer=HuntErrorRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntErrorRenderer_]")
    self.WaitUntil(self.IsTextPresent, "Client Error 1")

    self.Click("css=a[renderer=HuntHostInformationRenderer]")
    self.WaitUntil(self.IsElementPresent,
                   "css=div[id^=HuntHostInformationRenderer_]")

    self.WaitUntil(self.IsTextPresent, "CLIENT_INFO")
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

  def testHuntResultsView(self):
    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=a[renderer=HuntResultsRenderer]")

    self.WaitUntil(self.IsTextPresent, "aff4:/sample/1")
    self.WaitUntil(self.IsTextPresent,
                   "aff4:/C.0000000000000001/fs/os/c/bin/bash")
    self.WaitUntil(self.IsTextPresent, "aff4:/sample/3")

    with self.ACLChecksDisabled():
      self.GrantClientApproval("C.0000000000000001")

    self.Click("link=aff4:/C.0000000000000001/fs/os/c/bin/bash")
    self.WaitUntil(self.IsElementPresent,
                   "css=li.active a:contains('Browse Virtual Filesystem')")

  def testHuntStatsView(self):
    with self.ACLChecksDisabled():
      self.SetupTestHuntView()

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageHunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    self.WaitUntil(self.IsElementPresent,
                   "css=a[renderer=HuntStatsRenderer]")
    # Click the Stats tab.
    self.Click("css=a[renderer=HuntStatsRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=div[id^=HuntStatsRenderer_]")

    self.assertTrue(self.IsTextPresent("Total number of clients"))
    self.assertTrue(self.IsTextPresent("10"))

    self.assertTrue(self.IsTextPresent("User CPU mean"))
    self.assertTrue(self.IsTextPresent("5.5"))

    self.assertTrue(self.IsTextPresent("User CPU stdev"))
    self.assertTrue(self.IsTextPresent("2.9"))

    self.assertTrue(self.IsTextPresent("System CPU mean"))
    self.assertTrue(self.IsTextPresent("11"))

    self.assertTrue(self.IsTextPresent("System CPU stdev"))
    self.assertTrue(self.IsTextPresent("5.7"))

    self.assertTrue(self.IsTextPresent("Network bytes sent mean"))
    self.assertTrue(self.IsTextPresent("16.5"))

    self.assertTrue(self.IsTextPresent("Network bytes sent stdev"))
    self.assertTrue(self.IsTextPresent("8.6"))

  def testDoesNotShowGenerateArchiveButtonForNonExportableRDFValues(self):
    values = [rdfvalue.Process(pid=1),
              rdfvalue.Process(pid=42423)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntResultsRenderer]")

    self.WaitUntil(self.IsTextPresent, "42423")
    self.WaitUntilNot(self.IsTextPresent,
                      "Results of this hunt can be downloaded as an archive")

  def testDoesNotShowGenerateArchiveButtonWhenResultsCollectionIsEmpty(self):
    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection([])

    self.Open("/")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntResultsRenderer]")

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsTextPresent,
                      "Results of this hunt can be downloaded as an archive")

  def testShowsGenerateArchiveButtonForFileFinderHunt(self):
    stat_entry = rdfvalue.StatEntry(aff4path="aff4:/foo/bar")
    values = [rdfvalue.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntResultsRenderer]")

    self.WaitUntil(self.IsTextPresent,
                   "Results of this hunt can be downloaded as an archive")

  def testHuntAuthorizationIsRequiredToGenerateResultsArchive(self):
    stat_entry = rdfvalue.StatEntry(aff4path="aff4:/foo/bar")
    values = [rdfvalue.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntResultsRenderer]")
    # Using :visible selector as we don't know which button (ZIP or TAR.GZ) will
    # be shown - it depends on the platform.
    self.Click("css=button.DownloadButton:visible")

    self.WaitUntil(self.IsElementPresent, "acl_dialog")

  def testGenerateZipButtonGetsDisabledAfterClick(self):
    stat_entry = rdfvalue.StatEntry(aff4path="aff4:/foo/bar")
    values = [rdfvalue.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      hunt_urn = self.CreateGenericHuntWithCollection(values=values)
      self.GrantHuntApproval(hunt_urn)

    self.Open("/")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntResultsRenderer]")
    # Using :visible selector as we don't know which button (ZIP or TAR.GZ) will
    # be shown - it depends on the platform.
    self.Click("css=button.DownloadButton:visible")

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name*=generate_][disabled]:visible")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

  def testStartsZipGenerationWhenGenerateZipButtonIsClicked(self):
    stat_entry = rdfvalue.StatEntry(aff4path="aff4:/foo/bar")
    values = [rdfvalue.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      hunt_urn = self.CreateGenericHuntWithCollection(values=values)
      self.GrantHuntApproval(hunt_urn)

    self.Open("/")
    self.Click("css=a[grrtarget=ManageHunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntResultsRenderer]")
    # Using :visible selector as we don't know which button (ZIP or TAR.GZ) will
    # be shown - it depends on the platform.
    self.Click("css=button.DownloadButton:visible")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

    with self.ACLChecksDisabled():
      flows_dir = aff4.FACTORY.Open("aff4:/flows")
      flows = list(flows_dir.OpenChildren())
      export_flows = [
          f for f in flows
          if f.__class__.__name__ == "ExportHuntResultFilesAsArchive"]
      self.assertEqual(len(export_flows), 1)
      self.assertEqual(export_flows[0].args.hunt_urn, hunt_urn)

  def testListOfCSVFilesIsNotShownWhenHuntProducedNoResults(self):
    with self.ACLChecksDisabled():
      self.client_ids = self.SetupClients(10)

      # Create hunt without results.
      self.CreateSampleHunt(output_plugins=[
          rdfvalue.OutputPlugin(plugin_name="CSVOutputPlugin")])

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=a[renderer=HuntResultsRenderer]")
    self.WaitUntil(self.IsElementPresent, "css=table[aff4_path]")
    self.WaitUntilNot(self.IsTextPresent,
                      "CSV output plugin writes to following files")

  def testShowsFilesAndAllowsDownloadWhenCSVExportIsUsed(self):
    with self.ACLChecksDisabled():
      self.client_ids = self.SetupClients(10)

      # Create hunt.
      self.CreateSampleHunt(output_plugins=[
          rdfvalue.OutputPlugin(plugin_name="CSVOutputPlugin")])

      # Actually run created hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Make sure results are processed.
      flow_urn = flow.GRRFlow.StartFlow(flow_name="ProcessHuntResultsCronFlow",
                                        token=self.token)
      for _ in test_lib.TestFlowHelper(flow_urn, token=self.token):
        pass

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=a[renderer=HuntResultsRenderer]")
    self.WaitUntil(self.IsTextPresent,
                   "CSV output plugin writes to following files")

    # Check that displayed file can be downloaded.
    self.Click("css=.csv-output-note a:contains('ExportedFile.csv')")
    self.WaitUntil(self.FileWasDownloaded)

  def testLogsTabShowsLogsFromAllClients(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntLogRenderer]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, str(client_id))
      self.WaitUntil(self.IsTextPresent, "Finished reading " +
                     str(client_id.Add("fs/os/tmp/evil.txt")))

  def testLogsTabFiltersLogsByString(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntLogRenderer]")

    self.Type("css=grr-hunt-log input.search-query",
              self.client_ids[-1].Basename())
    self.Click("css=grr-hunt-log button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, str(self.client_ids[-1]))
    self.WaitUntil(self.IsTextPresent, "Finished reading " +
                   str(self.client_ids[-1].Add("fs/os/tmp/evil.txt")))

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, str(client_id))
      self.WaitUntilNot(self.IsTextPresent, "Finished reading " +
                        str(client_id.Add("fs/os/tmp/evil.txt")))

  def testErrorsTabShowsErrorsFromAllClients(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntErrorRenderer]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, str(client_id))

  def testErrorsTabFiltersErrorsByString(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=a[renderer=HuntErrorRenderer]")

    self.Type("css=grr-hunt-errors input.search-query",
              self.client_ids[-1].Basename())
    self.Click("css=grr-hunt-errors button:contains('Filter')")

    self.WaitUntil(self.IsTextPresent, str(self.client_ids[-1]))

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, str(client_id))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
