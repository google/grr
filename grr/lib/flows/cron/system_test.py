#!/usr/bin/env python
"""System cron flows tests."""


from grr.endtoend_tests import base
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import client_fixture
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import stats as aff4_stats
from grr.lib.flows.cron import system
from grr.lib.flows.general import endtoend as endtoend_flows
from grr.lib.flows.general import endtoend_test
from grr.lib.rdfvalues import client as client_rdf
from grr.lib.rdfvalues import flows


class SystemCronFlowTest(test_lib.FlowTestsBaseclass):
  """Test system cron flows."""

  def setUp(self):
    super(SystemCronFlowTest, self).setUp()

    # We are only interested in the client object (path = "/" in client VFS)
    fixture = test_lib.FilterFixture(regex="^/$")

    # Make 10 windows clients
    for i in range(0, 10):
      test_lib.ClientFixture("C.0%015X" % i, token=self.token, fixture=fixture)

      with aff4.FACTORY.Open("C.0%015X" % i,
                             mode="rw",
                             token=self.token) as client:
        client.AddLabels("Label1", "Label2", owner="GRR")
        client.AddLabels("UserLabel", owner="jim")

    # Make 10 linux clients 12 hours apart.
    for i in range(0, 10):
      test_lib.ClientFixture("C.1%015X" % i,
                             token=self.token,
                             fixture=client_fixture.LINUX_FIXTURE)

  def _CheckVersionStats(self, label, attribute, counts):

    fd = aff4.FACTORY.Open("aff4:/stats/ClientFleetStats/%s" % label,
                           token=self.token)
    histogram = fd.Get(attribute)

    # There should be counts[0] instances in 1 day actives.
    self.assertEqual(histogram[0].title, "1 day actives for %s label" % label)
    self.assertEqual(len(histogram[0]), counts[0])

    # There should be counts[1] instances in 7 day actives.
    self.assertEqual(histogram[1].title, "7 day actives for %s label" % label)
    self.assertEqual(len(histogram[1]), counts[1])

    # There should be counts[2] instances in 14 day actives.
    self.assertEqual(histogram[2].title, "14 day actives for %s label" % label)
    self.assertEqual(histogram[2][0].label, "GRR Monitor 1")
    self.assertEqual(histogram[2][0].y_value, counts[2])

    # There should be counts[3] instances in 30 day actives.
    self.assertEqual(histogram[3].title, "30 day actives for %s label" % label)
    self.assertEqual(histogram[3][0].label, "GRR Monitor 1")
    self.assertEqual(histogram[3][0].y_value, counts[3])

  def testGRRVersionBreakDown(self):
    """Check that all client stats cron jobs are run.

    All machines should be in All once.
    Windows machines should be in Label1 and Label2.
    There should be no stats for UserLabel.
    """
    for _ in test_lib.TestFlowHelper("GRRVersionBreakDown", token=self.token):
      pass

    histogram = aff4_stats.ClientFleetStats.SchemaCls.GRRVERSION_HISTOGRAM
    self._CheckVersionStats("All", histogram, [0, 0, 20, 20])
    self._CheckVersionStats("Label1", histogram, [0, 0, 10, 10])
    self._CheckVersionStats("Label2", histogram, [0, 0, 10, 10])

    # This shouldn't exist since it isn't a system label
    aff4.FACTORY.Open("aff4:/stats/ClientFleetStats/UserLabel",
                      aff4.AFF4Volume,
                      token=self.token)

  def _CheckOSStats(self, label, attribute, counts):

    fd = aff4.FACTORY.Open("aff4:/stats/ClientFleetStats/%s" % label,
                           token=self.token)
    histogram = fd.Get(attribute)

    # There should be counts[0] instances in 1 day actives.
    self.assertEqual(histogram[0].title, "1 day actives for %s label" % label)
    self.assertEqual(len(histogram[0]), counts[0])

    # There should be counts[1] instances in 7 day actives.
    self.assertEqual(histogram[1].title, "7 day actives for %s label" % label)
    self.assertEqual(len(histogram[1]), counts[1])

    # There should be counts[2] instances in 14 day actives for linux and
    # windows.
    self.assertEqual(histogram[2].title, "14 day actives for %s label" % label)
    all_labels = []
    for item in histogram[2]:
      all_labels.append(item.label)
      self.assertEqual(item.y_value, counts[2][item.label])
    self.assertItemsEqual(all_labels, counts[2].keys())

    # There should be counts[3] instances in 30 day actives for linux and
    # windows.
    self.assertEqual(histogram[3].title, "30 day actives for %s label" % label)
    all_labels = []
    for item in histogram[3]:
      all_labels.append(item.label)
      self.assertEqual(item.y_value, counts[3][item.label])
    self.assertItemsEqual(all_labels, counts[3].keys())

  def testOSBreakdown(self):
    """Check that all client stats cron jobs are run."""
    for _ in test_lib.TestFlowHelper("OSBreakDown", token=self.token):
      pass

    histogram = aff4_stats.ClientFleetStats.SchemaCls.OS_HISTOGRAM
    self._CheckOSStats("All", histogram, [0, 0, {"Linux": 10,
                                                 "Windows": 10},
                                          {"Linux": 10,
                                           "Windows": 10}])
    self._CheckOSStats("Label1", histogram,
                       [0, 0, {"Windows": 10}, {"Windows": 10}])
    self._CheckOSStats("Label2", histogram,
                       [0, 0, {"Windows": 10}, {"Windows": 10}])

  def _CheckAccessStats(self, label, count):
    fd = aff4.FACTORY.Open("aff4:/stats/ClientFleetStats/%s" % label,
                           token=self.token)

    histogram = fd.Get(fd.Schema.LAST_CONTACTED_HISTOGRAM)

    data = [(x.x_value, x.y_value) for x in histogram]

    self.assertEqual(data, [
        (86400000000L, 0L), (172800000000L, 0L), (259200000000L, 0L),
        (604800000000L, 0L), (1209600000000L, count), (2592000000000L, count),
        (5184000000000L, count)
    ])

  def testLastAccessStats(self):
    """Check that all client stats cron jobs are run."""
    for _ in test_lib.TestFlowHelper("LastAccessStats", token=self.token):
      pass

    # All our clients appeared at the same time (and did not appear since).
    self._CheckAccessStats("All", count=20L)

    # All our clients appeared at the same time but this label is only half.
    self._CheckAccessStats("Label1", count=10L)

    # All our clients appeared at the same time but this label is only half.
    self._CheckAccessStats("Label2", count=10L)

  def testPurgeClientStats(self):
    max_age = system.PurgeClientStats.MAX_AGE

    for t in [1 * max_age, 1.5 * max_age, 2 * max_age]:
      with test_lib.FakeTime(t):
        urn = self.client_id.Add("stats")

        stats_fd = aff4.FACTORY.Create(urn,
                                       aff4_stats.ClientStats,
                                       token=self.token,
                                       mode="rw")
        st = client_rdf.ClientStats(RSS_size=int(t))
        stats_fd.AddAttribute(stats_fd.Schema.STATS(st))

        stats_fd.Close()

    stat_obj = aff4.FACTORY.Open(urn,
                                 age=aff4.ALL_TIMES,
                                 token=self.token,
                                 ignore_cache=True)
    stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))
    self.assertEqual(len(stat_entries), 3)
    self.assertTrue(max_age in [e.RSS_size for e in stat_entries])

    with test_lib.FakeTime(2.5 * max_age):
      for _ in test_lib.TestFlowHelper("PurgeClientStats",
                                       None,
                                       client_id=self.client_id,
                                       token=self.token):
        pass

    stat_obj = aff4.FACTORY.Open(urn,
                                 age=aff4.ALL_TIMES,
                                 token=self.token,
                                 ignore_cache=True)
    stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))
    self.assertEqual(len(stat_entries), 1)
    self.assertTrue(max_age not in [e.RSS_size for e in stat_entries])

  def _SetSummaries(self, client_id):
    client = aff4.FACTORY.Create(client_id,
                                 aff4_grr.VFSGRRClient,
                                 mode="rw",
                                 token=self.token)
    client.Set(client.Schema.HOSTNAME(client_id))
    client.Set(client.Schema.SYSTEM("Darwin"))
    client.Set(client.Schema.OS_RELEASE("OSX"))
    client.Set(client.Schema.OS_VERSION("10.9.2"))
    client.Set(client.Schema.KERNEL("13.1.0"))
    client.Set(client.Schema.FQDN("%s.example.com" % client_id))
    client.Set(client.Schema.ARCH("AMD64"))
    client.Flush()

  def testEndToEndTests(self):

    self.client_ids = ["aff4:/C.6000000000000000", "aff4:/C.6000000000000001",
                       "aff4:/C.6000000000000002"]
    for clientid in self.client_ids:
      self._SetSummaries(clientid)

    self.client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

    with test_lib.ConfigOverrider({
        "Test.end_to_end_client_ids": self.client_ids
    }):
      with utils.MultiStubber(
          (base.AutomatedTest, "classes",
           {"MockEndToEndTest": endtoend_test.MockEndToEndTest}),
          (system.EndToEndTests, "lifetime", 0)):

        # The test harness doesn't understand the callstate at a later time that
        # this flow is doing, so we need to disable check_flow_errors.
        for _ in test_lib.TestFlowHelper("EndToEndTests",
                                         self.client_mock,
                                         client_id=self.client_id,
                                         check_flow_errors=False,
                                         token=self.token):
          pass

      test_lib.TestHuntHelperWithMultipleMocks({},
                                               check_flow_errors=False,
                                               token=self.token)
      hunt_ids = list(aff4.FACTORY.Open("aff4:/hunts",
                                        token=self.token).ListChildren())
      # We have only created one hunt, and we should have started with a clean
      # aff4 space.
      self.assertEqual(len(hunt_ids), 1)

      hunt_obj = aff4.FACTORY.Open(hunt_ids[0],
                                   token=self.token,
                                   age=aff4.ALL_TIMES)
      self.assertItemsEqual(
          sorted(hunt_obj.GetClients()), sorted(self.client_ids))

  def _CreateResult(self, success, clientid):
    success = endtoend_flows.EndToEndTestResult(success=success)
    return flows.GrrMessage(source=clientid, payload=success)

  def testEndToEndTestsResultChecking(self):

    self.client_ids = ["aff4:/C.6000000000000000", "aff4:/C.6000000000000001",
                       "aff4:/C.6000000000000002"]
    for clientid in self.client_ids:
      self._SetSummaries(clientid)

    self.client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

    endtoend = system.EndToEndTests(None, token=self.token)
    endtoend.state.Register("hunt_id", "aff4:/temphuntid")
    endtoend.state.Register("client_ids", set(self.client_ids))
    endtoend.state.Register("client_ids_failures", set())
    endtoend.state.Register("client_ids_result_reported", set())

    # No results at all
    self.assertRaises(flow.FlowError, endtoend._CheckForSuccess, [])

    # Not enough client results
    endtoend.state.Register("client_ids_failures", set())
    endtoend.state.Register("client_ids_result_reported", set())
    self.assertRaises(flow.FlowError, endtoend._CheckForSuccess,
                      [self._CreateResult(True, "aff4:/C.6000000000000001")])

    # All clients succeeded
    endtoend.state.Register("client_ids_failures", set())
    endtoend.state.Register("client_ids_result_reported", set())
    endtoend._CheckForSuccess([self._CreateResult(True,
                                                  "aff4:/C.6000000000000000"),
                               self._CreateResult(True,
                                                  "aff4:/C.6000000000000001"),
                               self._CreateResult(True,
                                                  "aff4:/C.6000000000000002")])

    # All clients complete, but some failures
    endtoend.state.Register("client_ids_failures", set())
    endtoend.state.Register("client_ids_result_reported", set())
    self.assertRaises(flow.FlowError, endtoend._CheckForSuccess,
                      [self._CreateResult(True, "aff4:/C.6000000000000000"),
                       self._CreateResult(False, "aff4:/C.6000000000000001"),
                       self._CreateResult(False, "aff4:/C.6000000000000002")])


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
