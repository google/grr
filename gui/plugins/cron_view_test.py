#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test the cron_view interface."""


from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs


class TestCronView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def setUp(self):
    super(TestCronView, self).setUp()
    cronjobs.RunAllCronJobs(token=self.token)

  def testCronView(self):
    """Test that scheduling flows works."""
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageCron]")

    # Table should contain Last Run
    self.WaitUntil(self.IsTextPresent, "Last Run")

    # Select a Cron.
    self.Click("css=td:contains('OSBreakDown')")

    # Check we can now see the log.
    self.WaitUntil(self.IsElementPresent, "css=table[class=proto_table]")
    self.WaitUntil(self.IsTextPresent, "Successfully ran cron job OSBreakDown")
