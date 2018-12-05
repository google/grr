#!/usr/bin/env python
"""Tests for the rapid hunts feature."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class HuntsWithRapidHuntingDisabledTest(gui_test_lib.GRRSeleniumHuntTest):
  """Test that rapid hunts logic does nothing when the config flag is off."""

  def testNewHuntWizardDoesNotSetClientRateOrMentionRapidHunts(self):
    self.Open("/#/hunts")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=File Finder")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Check that client rate is not set to 0.
    self.WaitUntil(
        self.IsElementPresent, "css=grr-new-hunt-wizard-form "
        "label:contains('Client rate') ~ * input")
    self.assertNotEqual(
        "0",
        self.GetValue("css=grr-new-hunt-wizard-form "
                      "label:contains('Client rate') ~ * input"))

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Review')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('FileFinder')")

    self.WaitUntilNot(
        self.IsElementPresent,
        "css=grr-wizard-form:contains('eligible for rapid hunting')")

  def testHuntViewDoesNotShowAnythingForRapidLikeHunts(self):
    # CreateHunt sets client rate to 0. Thus we have a rapid-hunting-like hunt:
    # FileFinder without download and client rate 0.
    hunt_obj = self.CreateHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=rdf_file_finder.FileFinderArgs(paths=["/tmp/evil.txt"]))

    self.Open("/#/hunts/%s" % hunt_obj.urn.Basename())

    self.WaitUntil(self.IsElementPresent,
                   "css=dt:contains('Client Rate') + dd:contains(0)")
    self.WaitUntilNot(
        self.IsElementPresent,
        "css=dt:contains('Client Rate') + dd:contains('rapid hunting')")


@db_test_lib.DualDBTest
class HuntsWithRapidHuntingEnabledTest(gui_test_lib.GRRSeleniumHuntTest):
  """Test rapid hunts logic works correctly when the config flag is on."""

  def setUp(self):
    super(HuntsWithRapidHuntingEnabledTest, self).setUp()
    self._config_overrider = test_lib.ConfigOverrider(
        {"AdminUI.rapid_hunts_enabled": True})
    self._config_overrider.Start()

  def tearDown(self):
    super(HuntsWithRapidHuntingEnabledTest, self).tearDown()
    self._config_overrider.Stop()

  def testClientRateSetTo0WhenFlowIsEligible(self):
    self.Open("/#/hunts")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=File Finder")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Check that client rate is set to 0.
    self.WaitUntilEqual(
        "0", self.GetValue, "css=grr-new-hunt-wizard-form "
        "label:contains('Client rate') ~ * input")

  def _ClickFromFlowConfigurationToReview(self):
    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")

    # Click on "Next" button.
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Review')")

  def _ClickFromReviewToFlowConfiguration(self):
    # Click on "Back" button.
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Where to run?')")

    # Click on "Back" button.
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('How to process results')")

    # Click on "Back" button
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Click on "Back" button
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

  def testRapidHuntEligibilityNoteShownForEligibleHunt(self):
    self.Open("/#/hunts")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=File Finder")

    self._ClickFromFlowConfigurationToReview()

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-wizard-form:contains('is eligible for rapid hunting')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Client rate set to 0')")
    self.assertEqual(self.GetText("css=td:contains('Client rate') + td"), "0")

  def testRapidHuntEligibilityNoteShownForNonEligibleHunt(self):
    self.Open("/#/hunts")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    self._ClickFromFlowConfigurationToReview()

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-wizard-form:contains('is not eligible for rapid hunting')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form td:contains('ListProcesses')")
    # Client rate shouldn't have been touched (neither by user nor by rapid
    # hunting logic). Therefore it should simply have its default value and
    # not be present in the review page.
    self.WaitUntilNot(self.IsElementPresent,
                      "css=td:contains('Client rate') + td")

  def testRapidHuntEligibilityNoteDynamicallyChanges(self):
    self.Open("/#/hunts")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=File Finder")

    self._ClickFromFlowConfigurationToReview()

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-wizard-form:contains('is eligible for rapid hunting')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Client rate set to 0')")
    self.assertEqual(self.GetText("css=td:contains('Client rate') + td"), "0")

    # Now go all the way back and change the flow, thus making the hunt not
    # eligible for rapid hunting.

    self._ClickFromReviewToFlowConfiguration()
    # Click on the FileFinder item in Filesystem flows list
    self.Click("css=#_Processes > i.jstree-icon")
    self.Click("link=ListProcesses")

    self._ClickFromFlowConfigurationToReview()

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-wizard-form:contains('is not eligible for rapid hunting')")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form td:contains('ListProcesses')")
    self.assertNotEquals(
        self.GetText("css=td:contains('Client rate') + td"), "0")

  def testRapidHuntClientRateCanBeManuallyOverridden(self):
    self.Open("/#/hunts")

    # Open up "New Hunt" wizard
    self.Click("css=button[name=NewHunt]")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    # Click on the FileFinder item in Filesystem flows list
    self.Click("css=#_Filesystem > i.jstree-icon")
    self.Click("link=File Finder")

    # Click on "Next" button
    self.Click("css=grr-new-hunt-wizard-form button.Next")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('Hunt parameters')")

    # Override client rate to 42.
    self.Type(
        "css=grr-new-hunt-wizard-form "
        "label:contains('Client rate') ~ * input", "42")

    # Click on "Back" button
    self.Click("css=grr-new-hunt-wizard-form button.Back")
    self.WaitUntil(self.IsElementPresent,
                   "css=grr-wizard-form:contains('What to run?')")

    self._ClickFromFlowConfigurationToReview()

    self.WaitUntil(
        self.IsElementPresent,
        "css=grr-wizard-form:contains('is eligible for rapid hunting')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=grr-wizard-form:contains('Client rate set to 0')")
    self.assertEqual(self.GetText("css=td:contains('Client rate') + td"), "42")

  def testHuntViewShowsEligibilityNoteForRapidLikeHuntWithClientRate0(self):
    # CreateHunt sets client rate to 0. Thus we have a rapid-hunting-like hunt:
    # FileFinder without download action and client rate 0.
    hunt_obj = self.CreateHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=rdf_file_finder.FileFinderArgs(paths=["/tmp/evil.txt"]))

    self.Open("/#/hunts/%s" % hunt_obj.urn.Basename())

    self.WaitUntil(
        self.IsElementPresent, "css=dt:contains('Client Rate') + "
        "dd:contains('is eligible for rapid hunting')")
    self.WaitUntil(
        self.IsElementPresent, "css=dt:contains('Client Rate') + "
        "dd:contains('Client rate set to 0')")
    self.assertTrue(
        self.GetText("css=dt:contains('Client Rate') + dd").startswith("0 "))

  def testHuntViewShowsEligibilityNoteForNonRapidHuntWithClientRate0(self):
    # CreateHunt sets client rate to 0. Thus we have a non-eligible hunt:
    # FileFinder with a recursive glob expression and client rate 0.
    hunt_obj = self.CreateHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=rdf_file_finder.FileFinderArgs(paths=["/tmp/**"]))

    self.Open("/#/hunts/%s" % hunt_obj.urn.Basename())

    self.WaitUntil(
        self.IsElementPresent, "css=dt:contains('Client Rate') + "
        "dd:contains('is not eligible for rapid hunting')")
    self.assertTrue(
        self.GetText("css=dt:contains('Client Rate') + dd").startswith("0 "))

  def testHuntViewDoesShowsNothingForRapidLikeHuntWithClientRateNon0(self):
    hunt_obj = self.CreateHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=rdf_file_finder.FileFinderArgs(paths=["/tmp/foo"]),
        client_rate=42)

    self.Open("/#/hunts/%s" % hunt_obj.urn.Basename())

    self.WaitUntil(self.IsElementPresent, "css=dt:contains('Client Rate')")
    self.WaitUntilNot(
        self.IsElementPresent, "css=dt:contains('Client Rate') + "
        "dd:contains('rapid hunting')")

  def testHuntViewDoesShowsNothingForNonRapidLikeHuntWithClientRateNon0(self):
    hunt_obj = self.CreateHunt(
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=rdf_file_finder.FileFinderArgs(paths=["/tmp/**"]),
        client_rate=42)

    self.Open("/#/hunts/%s" % hunt_obj.urn.Basename())

    self.WaitUntil(self.IsElementPresent, "css=dt:contains('Client Rate')")
    self.WaitUntilNot(
        self.IsElementPresent, "css=dt:contains('Client Rate') + "
        "dd:contains('rapid hunting')")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
