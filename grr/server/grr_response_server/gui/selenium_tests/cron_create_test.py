#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the cron creation UI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server import foreman_rules
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestCronCreation(gui_test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def testHuntSchedulingWorksCorrectly(self):
    self.Open("/")
    self.Click("css=a[grrtarget=crons]")

    self.Click("css=button[name=ScheduleHuntCronJob]")
    self.WaitUntil(self.IsTextPresent, "Cron Job properties")

    # Select daily periodicity
    self.Type(
        "css=grr-new-cron-job-wizard-form "
        "label:contains('Periodicity') ~ * input", "1d")

    # Click on "Next" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")

    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on Filesystem item in flows list
    self.WaitUntil(self.IsElementPresent, "css=#_Filesystem > i.jstree-icon")
    self.Click("css=#_Filesystem > i.jstree-icon")

    # Click on Find Files item in Filesystem flows list
    self.Click("link=File Finder")

    # Change "path" and "pathtype" values
    self.Type(
        "css=grr-new-cron-job-wizard-form "
        "grr-form-proto-repeated-field:has(label:contains('Paths')) "
        "input", "/tmp")
    self.Select(
        "css=grr-new-cron-job-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Pathtype')) "
        "select", "TSK")

    # Click on "Next" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Configure the hunt to use dummy output plugin.
    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Select("css=grr-new-cron-job-wizard-form select",
                gui_test_lib.DummyOutputPlugin.__name__)
    self.Type(
        "css=grr-new-cron-job-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Filename Regex')) "
        "input", "some regex")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Create 3 foreman rules. Note that "Add" button adds rules to the beginning
    # of a list.
    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Select("css=grr-new-cron-job-wizard-form div.well select", "Regex")
    rule = foreman_rules.ForemanRegexClientRule
    label = rule.ForemanStringField.SYSTEM.description
    self.Select(
        "css=grr-new-cron-job-wizard-form div.well "
        "label:contains('Field') ~ * select", label)
    self.Type(
        "css=grr-new-cron-job-wizard-form div.well "
        "label:contains('Attribute regex') ~ * input", "Linux")

    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Select("css=grr-new-cron-job-wizard-form div.well select", "Integer")
    rule = foreman_rules.ForemanIntegerClientRule
    label = rule.ForemanIntegerField.CLIENT_CLOCK.description
    self.Select(
        "css=grr-new-cron-job-wizard-form div.well "
        "label:contains('Field') ~ * select", label)
    self.Select(
        "css=grr-new-cron-job-wizard-form div.well "
        "label:contains('Operator') ~ * select", "GREATER_THAN")
    self.Type(
        "css=grr-new-cron-job-wizard-form div.well "
        "label:contains('Value') ~ * input", "1336650631137737")

    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Click("css=grr-new-cron-job-wizard-form div.well "
               "label:contains('Os darwin') ~ * input[type=checkbox]")

    # Click on "Next" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("DummyOutputPlugin"))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Client rule set"))

    # Check that periodicity information is present in the review.
    self.assertTrue(self.IsTextPresent("Periodicity"))
    self.assertTrue(self.IsTextPresent("1d"))

    # Click on "Schedule" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")

    # Anyone can schedule a hunt but we need an approval to actually start it.
    self.WaitUntil(self.IsTextPresent, "Created Cron Job:")

    # Close the window and check that cron job object was created.
    self.Click("css=grr-new-cron-job-wizard-form button.Next")

    # Select newly created cron job.
    self.Click("css=td:contains('FileFinder_')")

    # Check that correct details are displayed in cron job details tab.
    self.WaitUntil(self.IsTextPresent, "FileFinder")
    self.WaitUntil(self.IsTextPresent, "Cron Arguments")

    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
