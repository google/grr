#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test the cron_view interface."""


from grr.lib import cron
from grr.lib import test_lib


class TestCronView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def setUp(self):
    super(TestCronView, self).setUp()
    cron.ScheduleSystemCronFlows(token=self.token)
    cron.CRON_MANAGER.RunOnce(token=self.token)

  def testCronView(self):
    """Test that scheduling flows works."""
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageCron]")

    # Table should contain Last Run
    self.WaitUntil(self.IsTextPresent, "Last Run")

    # Table should contain system cron jobs
    self.WaitUntil(self.IsTextPresent, "GRRVersionBreakDown")
    self.WaitUntil(self.IsTextPresent, "LastAccessStats")
    self.WaitUntil(self.IsTextPresent, "OSBreakDown")

    # Select a Cron.
    self.Click("css=td:contains('OSBreakDown')")

    # Check that there's one flow in the list.
    self.WaitUntil(self.IsElementPresent,
                   "css=#main_bottomPane td:contains('OSBreakDown')")
