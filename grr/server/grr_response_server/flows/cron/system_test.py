#!/usr/bin/env python
"""System cron flows tests."""


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iterkeys

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.flows.cron import system
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class SystemCronTestMixin(object):

  def setUp(self):
    super(SystemCronTestMixin, self).setUp()

    # This is not optimal, we create clients 0-19 with Linux, then
    # overwrite clients 0-9 with Windows, leaving 10-19 for Linux.
    client_ping_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("8d")
    self.SetupClients(20, system="Linux", ping=client_ping_time)
    self.SetupClients(10, system="Windows", ping=client_ping_time)

    for i in range(0, 10):
      client_id = "C.1%015x" % i
      with aff4.FACTORY.Open(client_id, mode="rw", token=self.token) as client:
        client.AddLabels([u"Label1", u"Label2"], owner=u"GRR")
        client.AddLabel(u"UserLabel", owner=u"jim")

      data_store.REL_DB.AddClientLabels(client_id, u"GRR",
                                        [u"Label1", u"Label2"])
      data_store.REL_DB.AddClientLabels(client_id, u"jim", [u"UserLabel"])

  def _CheckVersionStats(self, label, attribute, counts):

    fd = aff4.FACTORY.Open(
        "aff4:/stats/ClientFleetStats/%s" % label, token=self.token)
    histogram = fd.Get(attribute)

    # There should be counts[0] instances in 1 day actives.
    self.assertEqual(histogram[0].title, "1 day actives for %s label" % label)
    self.assertEqual(len(histogram[0]), counts[0])

    # There should be counts[1] instances in 7 day actives.
    self.assertEqual(histogram[1].title, "7 day actives for %s label" % label)
    self.assertEqual(len(histogram[1]), counts[1])

    # There should be counts[2] instances in 14 day actives.
    self.assertEqual(histogram[2].title, "14 day actives for %s label" % label)
    self.assertEqual(histogram[2][0].label,
                     "GRR Monitor %s" % config.CONFIG["Source.version_numeric"])
    self.assertEqual(histogram[2][0].y_value, counts[2])

    # There should be counts[3] instances in 30 day actives.
    self.assertEqual(histogram[3].title, "30 day actives for %s label" % label)
    self.assertEqual(histogram[3][0].label,
                     "GRR Monitor %s" % config.CONFIG["Source.version_numeric"])
    self.assertEqual(histogram[3][0].y_value, counts[3])

  def _CheckGRRVersionBreakDown(self):
    """Checks the result of the GRRVersionBreakDown cron job."""

    # All machines should be in All once. Windows machines should be in Label1
    # and Label2. There should be no stats for UserLabel.
    histogram = aff4_stats.ClientFleetStats.SchemaCls.GRRVERSION_HISTOGRAM
    self._CheckVersionStats(u"All", histogram, [0, 0, 20, 20])
    self._CheckVersionStats(u"Label1", histogram, [0, 0, 10, 10])
    self._CheckVersionStats(u"Label2", histogram, [0, 0, 10, 10])

    # This shouldn't exist since it isn't a system label
    aff4.FACTORY.Open(
        "aff4:/stats/ClientFleetStats/UserLabel",
        aff4.AFF4Volume,
        token=self.token)

  def _CheckOSStats(self, label, attribute, counts):

    fd = aff4.FACTORY.Open(
        "aff4:/stats/ClientFleetStats/%s" % label, token=self.token)
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
    self.assertItemsEqual(all_labels, list(iterkeys(counts[2])))

    # There should be counts[3] instances in 30 day actives for linux and
    # windows.
    self.assertEqual(histogram[3].title, "30 day actives for %s label" % label)
    all_labels = []
    for item in histogram[3]:
      all_labels.append(item.label)
      self.assertEqual(item.y_value, counts[3][item.label])
    self.assertItemsEqual(all_labels, list(iterkeys(counts[3])))

  def _CheckOSBreakdown(self):
    histogram = aff4_stats.ClientFleetStats.SchemaCls.OS_HISTOGRAM
    self._CheckOSStats(
        u"All", histogram,
        [0, 0, {
            "Linux": 10,
            "Windows": 10
        }, {
            "Linux": 10,
            "Windows": 10
        }])
    self._CheckOSStats(u"Label1", histogram,
                       [0, 0, {
                           "Windows": 10
                       }, {
                           "Windows": 10
                       }])
    self._CheckOSStats(u"Label2", histogram,
                       [0, 0, {
                           "Windows": 10
                       }, {
                           "Windows": 10
                       }])

  def _CheckAccessStats(self, label, count):
    fd = aff4.FACTORY.Open(
        "aff4:/stats/ClientFleetStats/%s" % label, token=self.token)

    histogram = fd.Get(fd.Schema.LAST_CONTACTED_HISTOGRAM)

    data = [(x.x_value, x.y_value) for x in histogram]

    self.assertEqual(data,
                     [(86400000000, 0), (172800000000, 0), (259200000000, 0),
                      (604800000000, 0), (1209600000000, count),
                      (2592000000000, count), (5184000000000, count)])

  def _CheckLastAccessStats(self):

    # All our clients appeared at the same time (and did not appear since).
    self._CheckAccessStats(u"All", count=20)

    # All our clients appeared at the same time but this label is only half.
    self._CheckAccessStats(u"Label1", count=10)

    # All our clients appeared at the same time but this label is only half.
    self._CheckAccessStats(u"Label2", count=10)

  def testPurgeClientStats(self):
    client_id = test_lib.TEST_CLIENT_ID
    max_age = system.PurgeClientStats.MAX_AGE

    for t in [1 * max_age, 1.5 * max_age, 2 * max_age]:
      with test_lib.FakeTime(t):
        urn = client_id.Add("stats")

        stats_fd = aff4.FACTORY.Create(
            urn, aff4_stats.ClientStats, token=self.token, mode="rw")
        st = rdf_client.ClientStats(RSS_size=int(t))
        stats_fd.AddAttribute(stats_fd.Schema.STATS(st))

        stats_fd.Close()

    stat_obj = aff4.FACTORY.Open(urn, age=aff4.ALL_TIMES, token=self.token)
    stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))
    self.assertEqual(len(stat_entries), 3)
    self.assertTrue(max_age in [e.RSS_size for e in stat_entries])

    with test_lib.FakeTime(2.5 * max_age):
      self._RunPurgeClientStats()

    stat_obj = aff4.FACTORY.Open(urn, age=aff4.ALL_TIMES, token=self.token)
    stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))
    self.assertEqual(len(stat_entries), 1)
    self.assertTrue(max_age not in [e.RSS_size for e in stat_entries])


@db_test_lib.DualDBTest
class SystemCronFlowTest(SystemCronTestMixin, flow_test_lib.FlowTestsBaseclass):
  """Test system cron flows."""

  def testGRRVersionBreakDown(self):
    """Check that all client stats cron jobs are run."""
    flow_test_lib.TestFlowHelper(
        system.GRRVersionBreakDown.__name__, token=self.token)

    self._CheckGRRVersionBreakDown()

  def testOSBreakdown(self):
    """Check that all client stats cron jobs are run."""
    flow_test_lib.TestFlowHelper(system.OSBreakDown.__name__, token=self.token)

    self._CheckOSBreakdown()

  def testLastAccessStats(self):
    """Check that all client stats cron jobs are run."""
    flow_test_lib.TestFlowHelper(
        system.LastAccessStats.__name__, token=self.token)

    self._CheckLastAccessStats()

  def _RunPurgeClientStats(self):
    flow_test_lib.TestFlowHelper(
        system.PurgeClientStats.__name__, None, token=self.token)


class SystemCronJobTest(SystemCronTestMixin, test_lib.GRRBaseTest):
  """Test system cron jobs."""

  def testGRRVersionBreakDown(self):
    """Check that all client stats cron jobs are run."""
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    system.GRRVersionBreakDownCronJob(run, job).Run()

    self._CheckGRRVersionBreakDown()

  def testOSBreakdown(self):
    """Check that all client stats cron jobs are run."""
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    system.OSBreakDownCronJob(run, job).Run()

    self._CheckOSBreakdown()

  def testLastAccessStats(self):
    """Check that all client stats cron jobs are run."""
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    system.LastAccessStatsCronJob(run, job).Run()

    self._CheckLastAccessStats()

  def _RunPurgeClientStats(self):
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    system.PurgeClientStatsCronJob(run, job).Run()


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
