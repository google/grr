#!/usr/bin/env python
# Copyright 2011 Google Inc.
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

"""AFF4 Cron object tests."""


import time

from grr.lib import aff4
from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs
from grr.test_data import client_fixture


class CronJobTest(test_lib.AFF4ObjectTest):
  """Test the cron implementation."""

  def setUp(self):
    super(CronJobTest, self).setUp()

    # Mock today's time to be 8 days after the fixture date.
    self.old_time = time.time
    self.now = test_lib.FIXTURE_TIME + 8 * 60 * 60 * 24
    time.time = lambda: self.now

    # We are only interested in the client object (path = "/" in client VFS)
    fixture = test_lib.FilterFixture(regex="^/$")

    # Make 10 windows clients
    for i in range(0, 10):
      test_lib.ClientFixture("C.0%015X" % i, token=self.token, fixture=fixture)

    # Make 10 linux clients 12 hours apart.
    for i in range(0, 10):
      test_lib.ClientFixture("C.1%015X" % i, token=self.token,
                             fixture=client_fixture.LINUX_FIXTURE)

  def tearDown(self):
    time.time = self.old_time

  def testClientStatsCronJobs(self):
    """Check that all client stats cron jobs are run."""
    cronjobs.RunAllCronJobs(token=self.token)

    fd = aff4.FACTORY.Open("cron:/GRRVersionBreakDown", token=self.token)
    histogram = fd.Get(fd.Schema.GRRVERSION_HISTOGRAM)

    # There should be 0 instances in 1 day actives.
    self.assertEqual(histogram.data[0].title, "1 day actives")
    self.assertEqual(len(histogram.data[0].data), 0)

    # There should be 0 instances in 7 day actives.
    self.assertEqual(histogram.data[1].title, "7 day actives")
    self.assertEqual(len(histogram.data[1].data), 0)

    # There should be 10 of each (Linux, Windows) instances in 14 day actives.
    self.assertEqual(histogram.data[2].title, "14 day actives")
    self.assertEqual(histogram.data[2].data[0].label, "GRR Monitor 1")
    self.assertEqual(histogram.data[2].data[0].y_value, 20)

    # There should be 10 of each (Linux, Windows) instances in 30 day actives.
    self.assertEqual(histogram.data[3].title, "30 day actives")
    self.assertEqual(histogram.data[3].data[0].label, "GRR Monitor 1")
    self.assertEqual(histogram.data[3].data[0].y_value, 20)

    # Make sure that we only run once. We try to run all the crons after 20
    # minutes.
    self.now += 20 * 60

    cronjobs.RunAllCronJobs(token=self.token)

    fd = aff4.FACTORY.Open("cron:/GRRVersionBreakDown", token=self.token,
                           age=aff4.ALL_TIMES)

    histograms = list(fd.GetValuesForAttribute(
        fd.Schema.GRRVERSION_HISTOGRAM))

    self.assertEqual(len(histograms), 1)

  def testOSBreakdown(self):
    """Check that all client stats cron jobs are run."""
    cronjobs.RunAllCronJobs(token=self.token)

    fd = aff4.FACTORY.Open("cron:/OSBreakDown", token=self.token)

    histogram = fd.Get(fd.Schema.OS_HISTOGRAM)

    # There should be a 0 instances in 1 day actives.
    self.assertEqual(histogram.data[0].title, "1 day actives")
    self.assertEqual(len(histogram.data[0].data), 0)

    # There should be a 0 instances in 7 day actives.
    self.assertEqual(histogram.data[1].title, "7 day actives")
    self.assertEqual(len(histogram.data[1].data), 0)

    # There should be 10 of each (Linux, Windows) instances in 14 day actives.
    self.assertEqual(histogram.data[2].title, "14 day actives")
    self.assertEqual(histogram.data[2].data[0].label, "Linux")
    self.assertEqual(histogram.data[2].data[0].y_value, 10)
    self.assertEqual(histogram.data[2].data[1].label, "Windows")
    self.assertEqual(histogram.data[2].data[1].y_value, 10)

    # There should be 10 of each (Linux, Windows) instances in 30 day actives.
    self.assertEqual(histogram.data[3].title, "30 day actives")
    self.assertEqual(histogram.data[3].data[0].label, "Linux")
    self.assertEqual(histogram.data[3].data[0].y_value, 10)
    self.assertEqual(histogram.data[3].data[1].label, "Windows")
    self.assertEqual(histogram.data[3].data[1].y_value, 10)

  def testLastAccessStats(self):
    """Check that all client stats cron jobs are run."""
    cronjobs.RunAllCronJobs(token=self.token)

    fd = aff4.FACTORY.Open("cron:/LastAccessStats", token=self.token)

    histogram = fd.Get(fd.Schema.HISTOGRAM)

    data = [(x.x_value, x.y_value) for x in histogram.data.data]
    self.assertEqual(data, [
        (86400000000L, 0L),
        (172800000000L, 0L),
        (259200000000L, 0L),
        (604800000000L, 0L),

        # All our clients appeared at the same time (and did not appear since).
        (1209600000000L, 20L),
        (2592000000000L, 20L),
        (5184000000000L, 20L)])
