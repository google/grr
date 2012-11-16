#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    sel = self.selenium
    sel.open("/")

    self.WaitUntil(sel.is_element_present, "css=input[name=q]")
    self.WaitUntil(sel.is_element_present, "css=a[grrtarget=ManageCron]")
    sel.click("css=a[grrtarget=ManageCron]")

    # Table should contain Last Run
    self.WaitUntil(sel.is_text_present, "Last Run")

    # Select a Cron.
    self.WaitUntil(sel.is_element_present, "css=td:contains('OSBreakDown')")
    sel.click("css=td:contains('OSBreakDown')")

    # Check we can now see the log.
    self.WaitUntil(sel.is_element_present, "css=table[class=proto_table]")
    self.WaitUntil(sel.is_text_present, "Successfully ran cron job OSBreakDown")
