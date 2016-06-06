#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the hunt_view interface."""



import os
import traceback


import mock

from grr.gui import api_call_handler_utils
from grr.gui import runtests_test

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import output_plugin
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.flows.general import collectors
from grr.lib.flows.general import export as flow_export
from grr.lib.flows.general import file_finder
from grr.lib.flows.general import transfer
from grr.lib.hunts import process_results
from grr.lib.hunts import results as hunts_results
from grr.lib.output_plugins import csv_plugin
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import foreman as rdf_foreman


class TestHuntView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  reason = "Felt like it!"

  def CreateSampleHunt(self,
                       path=None,
                       stopped=False,
                       output_plugins=None,
                       client_limit=0,
                       client_count=10,
                       token=None):
    token = token or self.token
    self.client_ids = self.SetupClients(client_count)

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
            path=path or "/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.OS,)),
        client_rule_set=client_rule_set,
        output_plugins=output_plugins or [],
        client_rate=0,
        client_limit=client_limit,
        token=token) as hunt:
      if not stopped:
        hunt.Run()

    with aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=token) as foreman:

      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    self.hunt_urn = hunt.urn
    return aff4.FACTORY.Open(hunt.urn,
                             mode="rw",
                             token=token,
                             age=aff4.ALL_TIMES)

  def CreateGenericHuntWithCollection(self, values=None):
    self.client_ids = self.SetupClients(10)

    if values is None:
      values = [rdfvalue.RDFURN("aff4:/sample/1"),
                rdfvalue.RDFURN("aff4:/C.0000000000000001/fs/os/c/bin/bash"),
                rdfvalue.RDFURN("aff4:/sample/3")]

    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client",
                attribute_regex="GRR"))
    ])

    with hunts.GRRHunt.StartHunt(hunt_name="GenericHunt",
                                 client_rule_set=client_rule_set,
                                 output_plugins=[],
                                 token=self.token) as hunt:

      runner = hunt.GetRunner()
      runner.Start()

      with aff4.FACTORY.Open(runner.context.results_collection_urn,
                             aff4_type=hunts_results.HuntResultCollection,
                             mode="w",
                             token=self.token) as collection:

        for value in values:
          collection.Add(rdf_flows.GrrMessage(payload=value))

      return hunt.urn

  def SetupTestHuntView(self, client_limit=0, client_count=10):
    # Create some clients and a hunt to view.
    with self.CreateSampleHunt(client_limit=client_limit,
                               client_count=client_count) as hunt:
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

  def CheckState(self, state):
    self.WaitUntil(self.IsElementPresent, "css=div[state=\"%s\"]" % state)

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

  def testToolbarStateForStoppedHunt(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt(stopped=True)

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

    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=RunHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent, "css=button[name=StopHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt]:not([disabled])")

  def testToolbarStateForRunningHunt(self):
    with self.ACLChecksDisabled():
      self.CreateSampleHunt(stopped=False)

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

    self.WaitUntil(self.IsElementPresent, "css=button[name=RunHunt][disabled]")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=StopHunt]:not([disabled])")
    self.WaitUntil(self.IsElementPresent,
                   "css=button[name=ModifyHunt][disabled]")

  def testRunHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
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
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

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
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    # Check the hunt is in a running state.
    self.CheckState("STARTED")

  def testStopHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=False)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Stop button and check that dialog appears.
    self.Click("css=button[name=StopHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to stop this hunt?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")

    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.session_id)

    # Click on Stop and wait for dialog again.
    self.Click("css=button[name=StopHunt]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to stop this hunt?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Hunt stopped successfully")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Check the hunt is not in a running state.
    self.CheckState("STOPPED")

  def testModifyHunt(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(stopped=True)

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Modify button and check that dialog appears.
    self.Click("css=button[name=ModifyHunt]")
    self.WaitUntil(self.IsTextPresent, "Modify a hunt")

    self.Type("css=input[id=v_-client_limit]", "4483")
    self.Type("css=input[id=v_-expiry_time]",
              str(rdfvalue.Duration("5m").Expiry()))

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
    self.Type("css=input[id=v_-expiry_time]",
              str(rdfvalue.Duration("5m").Expiry()))

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt modified successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.WaitUntil(self.IsTextPresent, "4483")

  def testDeleteHunt(self):
    with self.ACLChecksDisabled():
      # This needs to be created by a different user so we can test the
      # approval dialog.
      hunt = self.CreateSampleHunt(stopped=True,
                                   token=access_control.ACLToken(
                                       username="random user",
                                       reason="test"))

    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=hunts]")
    self.WaitUntil(self.IsTextPresent, "GenericHunt")

    # Select a Hunt.
    self.Click("css=td:contains('GenericHunt')")

    # Click on delete button.
    self.Click("css=button[name=DeleteHunt]")
    self.WaitUntil(self.IsTextPresent, "Delete a hunt")

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

    # Select a hunt again, as it's deselected after approval dialog
    # disappears. TODO(user): if this behavior is not convenient, fix it.
    self.Click("css=td:contains('GenericHunt')")

    # Click on Delete button and check that dialog appears.
    self.Click("css=button[name=DeleteHunt]")
    self.WaitUntil(self.IsTextPresent, "Delete a hunt")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Hunt Deleted!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

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
    self.Click("css=a[grrtarget=hunts]")

    self.WaitUntil(self.IsTextPresent, "GenericHunt")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Overview Tab then the Details Link.
    self.Click("css=li[heading=Overview]")
    self.WaitUntil(self.IsTextPresent, "Hunt URN")

    # Check the Hunt Details.
    self.Click("css=button[name=ViewHuntDetails]")
    self.WaitUntil(self.IsTextPresent, "Viewing Hunt aff4:/hunts/")

    self.WaitUntil(self.IsTextPresent, "COMPLETED")

    # Select the first client which should have errors.
    self.Click("css=td:contains('%s')" % self.client_ids[1].Basename())
    self.WaitUntil(self.IsTextPresent, "Last Checkin")

    self.Click("css=a[renderer=HuntLogRenderer]")
    self.WaitUntil(self.IsTextPresent, "GetFile Flow Completed")

    self.Click("css=a[renderer=HuntErrorRenderer]")
    self.WaitUntil(self.IsTextPresent, "Client Error 1")

    self.Click("css=a[renderer=HuntHostInformationRenderer]")
    self.WaitUntil(self.IsTextPresent, "CLIENT_INFO")
    self.WaitUntil(self.IsTextPresent, "VFSGRRClient")

  def testHuntOverviewShowsStats(self):
    """Test the detailed client view works."""
    with self.ACLChecksDisabled():
      with self.CreateSampleHunt() as hunt:
        hunt_stats = hunt.state.context.usage_stats
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

  def testDoesNotShowPerFileDownloadButtonForNonExportableRDFValues(self):
    values = [rdf_client.Process(pid=1), rdf_client.Process(pid=42423)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "42423")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-results-collection grr-downloadable-urn button")

  def testShowsPerFileDownloadButtonForFileFinderHunt(self):
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
    stat_entry = rdf_client.StatEntry(aff4path=client_id.Add("fs/os/foo/bar"))
    values = [file_finder.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-results-collection grr-downloadable-urn button")

  def testShowsPerFileDownloadButtonForArtifactDownloaderHunt(self):
    with self.ACLChecksDisabled():
      client_id = self.SetupClients(1)[0]
    stat_entry = rdf_client.StatEntry(aff4path=client_id.Add("fs/os/foo/bar"))
    values = [collectors.ArtifactFilesDownloaderResult(
        downloaded_file=stat_entry)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsElementPresent,
                   "css=grr-results-collection grr-downloadable-urn button")

  def _CreateHuntWithDownloadedFile(self):
    with self.ACLChecksDisabled():
      hunt = self.CreateSampleHunt(
          path=os.path.join(self.base_path, "test.plist"),
          client_count=1)

      action_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                            "HashFile", "HashBuffer")
      test_lib.TestHuntHelper(action_mock, self.client_ids, False, self.token)

      return hunt

  def testHuntAuthorizationIsRequiredToDownloadSingleHuntFile(self):
    self._CreateHuntWithDownloadedFile()

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")
    self.Click("css=grr-results-collection grr-downloadable-urn button")

    self.WaitUntil(self.IsTextPresent, "Create a new approval request")

  def testDownloadsSingleHuntFileIfAuthorizationIsPresent(self):
    hunt = self._CreateHuntWithDownloadedFile()
    with self.ACLChecksDisabled():
      results = aff4.FACTORY.Open(hunt.urn.Add("Results"), token=self.token)
      fd = aff4.FACTORY.Open(
          flow_export.CollectionItemToAff4Path(results[0]),
          token=self.token)

      self.GrantHuntApproval(hunt.urn)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    with mock.patch.object(fd.__class__, "Read") as mock_obj:
      self.Click("css=grr-results-collection grr-downloadable-urn button")
      self.WaitUntil(lambda: mock_obj.called)

  def testDisplaysErrorMessageIfSingleHuntFileCanNotBeRead(self):
    hunt = self._CreateHuntWithDownloadedFile()
    with self.ACLChecksDisabled():
      results = aff4.FACTORY.Open(hunt.urn.Add("Results"), token=self.token)
      aff4_path = flow_export.CollectionItemToAff4Path(results[0])
      with aff4.FACTORY.Create(aff4_path,
                               aff4_type=aff4.AFF4Volume,
                               token=self.token) as _:
        pass

      self.GrantHuntApproval(hunt.urn)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")
    self.Click("css=grr-results-collection grr-downloadable-urn button")
    self.WaitUntil(self.IsTextPresent, "Couldn't download the file.")

  def testDoesNotShowGenerateArchiveButtonForNonExportableRDFValues(self):
    values = [rdf_client.Process(pid=1), rdf_client.Process(pid=42423)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "42423")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testDoesNotShowGenerateArchiveButtonWhenResultsCollectionIsEmpty(self):
    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection([])

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent, "Value")
    self.WaitUntilNot(self.IsTextPresent,
                      "Files referenced in this collection can be downloaded")

  def testShowsGenerateArchiveButtonForFileFinderHunt(self):
    stat_entry = rdf_client.StatEntry(aff4path="aff4:/foo/bar")
    values = [file_finder.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent,
                   "Files referenced in this collection can be downloaded")

  def testShowsGenerateArchiveButtonForArtifactDownloaderHunt(self):
    stat_entry = rdf_client.StatEntry(aff4path="aff4:/foo/bar")
    values = [collectors.ArtifactFilesDownloaderResult(
        downloaded_file=stat_entry)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")

    self.WaitUntil(self.IsTextPresent,
                   "Files referenced in this collection can be downloaded")

  def testHuntAuthorizationIsRequiredToGenerateResultsArchive(self):
    stat_entry = rdf_client.StatEntry(aff4path="aff4:/foo/bar")
    values = [file_finder.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      self.CreateGenericHuntWithCollection(values=values)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")
    self.Click("css=button.DownloadButton")

    self.WaitUntil(self.IsTextPresent, "Create a new approval request")

  def testGenerateZipButtonGetsDisabledAfterClick(self):
    stat_entry = rdf_client.StatEntry(aff4path="aff4:/foo/bar")
    values = [file_finder.FileFinderResult(stat_entry=stat_entry)]

    with self.ACLChecksDisabled():
      hunt_urn = self.CreateGenericHuntWithCollection(values=values)
      self.GrantHuntApproval(hunt_urn)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")
    self.Click("css=button.DownloadButton")

    self.WaitUntil(self.IsElementPresent, "css=button.DownloadButton[disabled]")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

  def testShowsNotificationWhenArchiveGenerationIsDone(self):
    hunt = self._CreateHuntWithDownloadedFile()
    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.urn)

    self.Open("/")
    self.Click("css=a[grrtarget=hunts]")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Results]")
    self.Click("css=button.DownloadButton")
    self.WaitUntil(self.IsTextPresent, "Generation has started")

    self.WaitUntil(self.IsUserNotificationPresent,
                   "Downloaded archive of hunt %s" % hunt.urn.Basename())
    # Check that the archive generating flow does not end with an error.
    self.WaitUntilNot(self.IsUserNotificationPresent, "terminated due to error")

  def testShowsErrorMessageIfArchiveStreamingFailsBeforeFirstChunkIsSent(self):
    hunt = self._CreateHuntWithDownloadedFile()
    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.urn)

    def RaisingStub(*unused_args, **unused_kwargs):
      raise RuntimeError("something went wrong")

    with utils.Stubber(api_call_handler_utils.CollectionArchiveGenerator,
                       "Generate", RaisingStub):
      self.Open("/")
      self.Click("css=a[grrtarget=hunts]")
      self.Click("css=td:contains('GenericHunt')")
      self.Click("css=li[heading=Results]")
      self.Click("css=button.DownloadButton")
      self.WaitUntil(self.IsTextPresent,
                     "Can't generate archive: Unknown error")
      self.WaitUntil(self.IsUserNotificationPresent,
                     "Archive generation failed for hunt")

  def testShowsNotificationIfArchiveStreamingFailsInProgress(self):
    hunt = self._CreateHuntWithDownloadedFile()
    with self.ACLChecksDisabled():
      self.GrantHuntApproval(hunt.urn)

    def RaisingStub(*unused_args, **unused_kwargs):
      yield "foo"
      yield "bar"
      raise RuntimeError("something went wrong")

    with utils.Stubber(api_call_handler_utils.CollectionArchiveGenerator,
                       "Generate", RaisingStub):
      self.Open("/")
      self.Click("css=a[grrtarget=hunts]")
      self.Click("css=td:contains('GenericHunt')")
      self.Click("css=li[heading=Results]")
      self.Click("css=button.DownloadButton")
      self.WaitUntil(self.IsUserNotificationPresent,
                     "Archive generation failed for hunt")
      # There will be no failure message, as we can't get a status from an
      # iframe that triggers the download.
      self.WaitUntilNot(self.IsTextPresent,
                        "Can't generate archive: Unknown error")

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

  def testListOfCSVFilesIsNotShownWhenHuntProducedNoResults(self):
    with self.ACLChecksDisabled():
      self.client_ids = self.SetupClients(10)

      # Create hunt without results.
      self.CreateSampleHunt(output_plugins=[
          output_plugin.OutputPluginDescriptor(
              plugin_name=csv_plugin.CSVOutputPlugin.__name__)
      ])

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsTextPresent, "CSV Output")
    self.WaitUntil(self.IsTextPresent, "Nothing was written yet")

  def testShowsFilesAndAllowsDownloadWhenCSVExportIsUsed(self):
    with self.ACLChecksDisabled():
      self.client_ids = self.SetupClients(10)

      # Create hunt.
      self.CreateSampleHunt(output_plugins=[
          output_plugin.OutputPluginDescriptor(
              plugin_name=csv_plugin.CSVOutputPlugin.__name__)
      ])

      # Actually run created hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Make sure results are processed.
      flow_urn = flow.GRRFlow.StartFlow(
          flow_name=process_results.ProcessHuntResultCollectionsCronFlow.
          __name__,
          token=self.token)
      for _ in test_lib.TestFlowHelper(flow_urn, token=self.token):
        pass

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")

    # Click the Results tab.
    self.Click("css=li[heading=Results]")
    self.WaitUntil(self.IsTextPresent, "Following files were written")

    # Check that displayed file can be downloaded.
    self.Click("css=a:contains('ExportedFile.csv')")
    self.WaitUntil(self.FileWasDownloaded)

  def testLogsTabShowsLogsFromAllClients(self):
    with self.ACLChecksDisabled():
      self.SetupHuntDetailView(failrate=-1)

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading=Log]")

    for client_id in self.client_ids:
      self.WaitUntil(self.IsTextPresent, str(client_id))
      self.WaitUntil(
          self.IsTextPresent,
          "Finished reading " + str(client_id.Add("fs/os/tmp/evil.txt")))

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
    self.WaitUntil(self.IsTextPresent, "Finished reading " +
                   str(self.client_ids[-1].Add("fs/os/tmp/evil.txt")))

    for client_id in self.client_ids[:-1]:
      self.WaitUntilNot(self.IsTextPresent, str(client_id))
      self.WaitUntilNot(
          self.IsTextPresent,
          "Finished reading " + str(client_id.Add("fs/os/tmp/evil.txt")))

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

  def testOutstandingClientsTabShowsAllNonCompletedClients(self):
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
    self.Click("css=li[heading=Outstanding]")

    for client_id in outstanding_client_ids:
      self.WaitUntilContains(client_id.Basename(), self.GetText,
                             "css=.tab-content")

  def testContextTabShowsHuntContext(self):
    with self.ACLChecksDisabled():
      # Create some clients and a hunt to view.
      self.CreateSampleHunt()

    self.Open("/#main=ManageHunts")
    self.Click("css=td:contains('GenericHunt')")
    self.Click("css=li[heading='Context Detail']")

    # Check for different context properties.
    self.WaitUntilContains(
        "GetFile", self.GetText,
        "css=table > tbody td.proto_key:contains(\"Description\") "
        "~ td.proto_value")
    self.WaitUntilContains(
        "Running tests", self.GetText,
        "css=table > tbody td.proto_key:contains(\"Reason\") "
        "~ td.proto_value")
    self.WaitUntilContains(
        "Start", self.GetText,
        "css=table > tbody td.proto_key:contains(\"current_state\") "
        "~ td.proto_value")
    self.WaitUntilContains(
        "test", self.GetText,
        "css=table > tbody td.proto_key:contains(\"creator\") "
        "~ td.proto_value")
    self.WaitUntilContains(
        "%s/Results" % self.hunt_urn, self.GetText,
        "css=table > tbody td.proto_key:contains(\"results_collection_urn\") "
        "~ td.proto_value")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
