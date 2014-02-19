#!/usr/bin/env python
"""System cron flows tests."""


import time

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.flows.cron import system
from grr.test_data import client_fixture


class SystemCronFlowTest(test_lib.FlowTestsBaseclass):
  """Test system cron flows."""

  def setUp(self):
    super(SystemCronFlowTest, self).setUp()

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

  def testGRRVersionBreakDown(self):
    """Check that all client stats cron jobs are run."""
    for _ in test_lib.TestFlowHelper("GRRVersionBreakDown", token=self.token):
      pass

    fd = aff4.FACTORY.Open("aff4:/stats/ClientFleetStats", token=self.token)
    histogram = fd.Get(fd.Schema.GRRVERSION_HISTOGRAM)

    # There should be 0 instances in 1 day actives.
    self.assertEqual(histogram[0].title, "1 day actives")
    self.assertEqual(len(histogram[0]), 0)

    # There should be 0 instances in 7 day actives.
    self.assertEqual(histogram[1].title, "7 day actives")
    self.assertEqual(len(histogram[1]), 0)

    # There should be 10 of each (Linux, Windows) instances in 14 day actives.
    self.assertEqual(histogram[2].title, "14 day actives")
    self.assertEqual(histogram[2][0].label, "GRR Monitor 1")
    self.assertEqual(histogram[2][0].y_value, 20)

    # There should be 10 of each (Linux, Windows) instances in 30 day actives.
    self.assertEqual(histogram[3].title, "30 day actives")
    self.assertEqual(histogram[3][0].label, "GRR Monitor 1")
    self.assertEqual(histogram[3][0].y_value, 20)

  def testOSBreakdown(self):
    """Check that all client stats cron jobs are run."""
    for _ in test_lib.TestFlowHelper("OSBreakDown", token=self.token):
      pass

    fd = aff4.FACTORY.Open("aff4:/stats/ClientFleetStats", token=self.token)

    histogram = fd.Get(fd.Schema.OS_HISTOGRAM)

    # There should be a 0 instances in 1 day actives.
    self.assertEqual(histogram[0].title, "1 day actives")
    self.assertEqual(len(histogram[0]), 0)

    # There should be a 0 instances in 7 day actives.
    self.assertEqual(histogram[1].title, "7 day actives")
    self.assertEqual(len(histogram[1]), 0)

    # There should be 10 of each (Linux, Windows) instances in 14 day actives.
    self.assertEqual(histogram[2].title, "14 day actives")
    self.assertEqual(histogram[2][0].label, "Linux")
    self.assertEqual(histogram[2][0].y_value, 10)
    self.assertEqual(histogram[2][1].label, "Windows")
    self.assertEqual(histogram[2][1].y_value, 10)

    # There should be 10 of each (Linux, Windows) instances in 30 day actives.
    self.assertEqual(histogram[3].title, "30 day actives")
    self.assertEqual(histogram[3][0].label, "Linux")
    self.assertEqual(histogram[3][0].y_value, 10)
    self.assertEqual(histogram[3][1].label, "Windows")
    self.assertEqual(histogram[3][1].y_value, 10)

  def testLastAccessStats(self):
    """Check that all client stats cron jobs are run."""
    for _ in test_lib.TestFlowHelper("LastAccessStats", token=self.token):
      pass

    fd = aff4.FACTORY.Open("aff4:/stats/ClientFleetStats", token=self.token)

    histogram = fd.Get(fd.Schema.LAST_CONTACTED_HISTOGRAM)

    data = [(x.x_value, x.y_value) for x in histogram]

    self.assertEqual(data, [
        (86400000000L, 0L),
        (172800000000L, 0L),
        (259200000000L, 0L),
        (604800000000L, 0L),

        # All our clients appeared at the same time (and did not appear since).
        (1209600000000L, 20L),
        (2592000000000L, 20L),
        (5184000000000L, 20L)])

  def testPurgeClientStats(self):
    max_age = system.PurgeClientStats.MAX_AGE

    for t in [1 * max_age, 1.5 * max_age, 2 * max_age]:
      with test_lib.FakeTime(t):
        urn = self.client_id.Add("stats")

        stats_fd = aff4.FACTORY.Create(urn, "ClientStats", token=self.token,
                                       mode="rw")
        st = rdfvalue.ClientStats(RSS_size=int(t))
        stats_fd.AddAttribute(stats_fd.Schema.STATS(st))

        stats_fd.Close()

    stat_obj = aff4.FACTORY.Open(
        urn, age=aff4.ALL_TIMES, token=self.token, ignore_cache=True)
    stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))
    self.assertEqual(len(stat_entries), 3)
    self.assertTrue(max_age in [e.RSS_size for e in stat_entries])

    with test_lib.FakeTime(2.5 * max_age):
      for _ in test_lib.TestFlowHelper(
          "PurgeClientStats", None, client_id=self.client_id, token=self.token):
        pass

    stat_obj = aff4.FACTORY.Open(
        urn, age=aff4.ALL_TIMES, token=self.token, ignore_cache=True)
    stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))
    self.assertEqual(len(stat_entries), 1)
    self.assertTrue(max_age not in [e.RSS_size for e in stat_entries])
