#!/usr/bin/env python
"""System cron flows tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import range  # pylint: disable=redefined-builtin
import mock

from google.protobuf import timestamp_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import compatibility
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_test_utils
from grr_response_core.stats import stats_utils
from grr_response_server import aff4
from grr_response_server import client_report_utils
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import stats_store
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.flows.cron import system
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class SystemCronTestMixin(object):

  def setUp(self):
    super(SystemCronTestMixin, self).setUp()

    recent_ping = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("8d")
    # Simulate Fleetspeak clients with last-ping timestamps in the GRR DB
    # that haven't been updated in a while. Last-contact timestamps reported
    # by Fleetspeak should be used instead of this value.
    ancient_ping = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("999d")
    self.SetupClientsWithIndices(
        range(0, 10), system="Windows", ping=recent_ping)
    self.SetupClientsWithIndices(
        range(10, 20), system="Linux", ping=recent_ping)
    fs_urns = self.SetupClientsWithIndices(
        range(20, 22),
        system="Darwin",
        fleetspeak_enabled=True,
        ping=ancient_ping)

    for i in range(0, 10):
      client_id = u"C.1%015x" % i
      with aff4.FACTORY.Open(client_id, mode="rw", token=self.token) as client:
        client.AddLabels([u"Label1", u"Label2"], owner=u"GRR")
        client.AddLabel(u"UserLabel", owner=u"jim")

      data_store.REL_DB.AddClientLabels(client_id, u"GRR",
                                        [u"Label1", u"Label2"])
      data_store.REL_DB.AddClientLabels(client_id, u"jim", [u"UserLabel"])

    fs_connector_patcher = mock.patch.object(fleetspeak_connector, "CONN")
    self._fs_conn = fs_connector_patcher.start()
    self.addCleanup(fs_connector_patcher.stop)
    last_fs_contact = timestamp_pb2.Timestamp()
    # Have Fleetspeak report that the last contact with the Fleetspeak clients
    # happened an hour ago.
    last_ping_rdf = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1h")
    last_fs_contact.FromMicroseconds(last_ping_rdf.AsMicrosecondsSinceEpoch())
    fs_clients = [
        admin_pb2.Client(
            client_id=fleetspeak_utils.GRRIDToFleetspeakID(
                fs_urns[0].Basename()),
            last_contact_time=last_fs_contact),
        admin_pb2.Client(
            client_id=fleetspeak_utils.GRRIDToFleetspeakID(
                fs_urns[1].Basename()),
            last_contact_time=last_fs_contact),
    ]
    self._fs_conn.outgoing.ListClients.return_value = (
        admin_pb2.ListClientsResponse(clients=fs_clients))

  def _CheckVersionGraph(self, graph, expected_title, expected_count):
    self.assertEqual(graph.title, expected_title)
    if expected_count == 0:
      self.assertEmpty(graph)
      return
    sample = graph[0]
    self.assertEqual(sample.label,
                     "GRR Monitor %s" % config.CONFIG["Source.version_numeric"])
    self.assertEqual(sample.y_value, expected_count)

  def _CheckVersionStats(self, label, report_type, counts):
    # We expect to have 1, 7, 14 and 30-day graphs for every label.
    graph_series = client_report_utils.FetchMostRecentGraphSeries(
        label, report_type)

    self._CheckVersionGraph(graph_series.graphs[0],
                            "1 day actives for %s label" % label, counts[0])
    self._CheckVersionGraph(graph_series.graphs[1],
                            "7 day actives for %s label" % label, counts[1])
    self._CheckVersionGraph(graph_series.graphs[2],
                            "14 day actives for %s label" % label, counts[2])
    self._CheckVersionGraph(graph_series.graphs[3],
                            "30 day actives for %s label" % label, counts[3])

  def _CheckGRRVersionBreakDown(self):
    """Checks the result of the GRRVersionBreakDown cron job."""
    self._fs_conn.outgoing.ListClients.assert_called_once()
    # All machines should be in All once. Windows machines should be in Label1
    # and Label2. There should be no stats for UserLabel.
    report_type = rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION
    self._CheckVersionStats(u"All", report_type, [2, 2, 22, 22])
    self._CheckVersionStats(u"Label1", report_type, [0, 0, 10, 10])
    self._CheckVersionStats(u"Label2", report_type, [0, 0, 10, 10])

  def _CheckOSGraph(self, graph, expected_title, expected_counts):
    actual_counts = {s.label: s.y_value for s in graph}
    self.assertEqual(graph.title, expected_title)
    self.assertDictEqual(actual_counts, expected_counts)

  def _CheckOSStats(self, label, report_type, counts):
    self._fs_conn.outgoing.ListClients.assert_called_once()
    # We expect to have 1, 7, 14 and 30-day graphs for every label.
    graph_series = client_report_utils.FetchMostRecentGraphSeries(
        label, report_type)

    self._CheckOSGraph(graph_series.graphs[0],
                       "1 day actives for %s label" % label, counts[0])
    self._CheckOSGraph(graph_series.graphs[1],
                       "7 day actives for %s label" % label, counts[1])
    self._CheckOSGraph(graph_series.graphs[2],
                       "14 day actives for %s label" % label, counts[2])
    self._CheckOSGraph(graph_series.graphs[3],
                       "30 day actives for %s label" % label, counts[3])

  def _CheckOSBreakdown(self):
    self._fs_conn.outgoing.ListClients.assert_called_once()
    report_type = rdf_stats.ClientGraphSeries.ReportType.OS_TYPE
    all_stats = [
        {
            "Darwin": 2
        },
        {
            "Darwin": 2
        },
        {
            "Linux": 10,
            "Windows": 10,
            "Darwin": 2
        },
        {
            "Linux": 10,
            "Windows": 10,
            "Darwin": 2
        },
    ]
    label_stats = [{}, {}, {"Windows": 10}, {"Windows": 10}]
    self._CheckOSStats(u"All", report_type, all_stats)
    self._CheckOSStats(u"Label1", report_type, label_stats)
    self._CheckOSStats(u"Label2", report_type, label_stats)

  def _CheckAccessStats(self, label, expected):
    graph_series = client_report_utils.FetchMostRecentGraphSeries(
        label, rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE)

    histogram = graph_series.graphs[0]

    data = [(x.x_value, x.y_value) for x in histogram]

    self.assertEqual(data, expected)

  def _ToMicros(self, duration_str):
    return rdfvalue.Duration(duration_str).microseconds

  def _CheckLastAccessStats(self):
    self._fs_conn.outgoing.ListClients.assert_called_once()

    # pyformat: disable
    all_counts = [
        (self._ToMicros("1d"), 2),
        (self._ToMicros("2d"), 2),
        (self._ToMicros("3d"), 2),
        (self._ToMicros("7d"), 2),
        (self._ToMicros("14d"), 22),
        (self._ToMicros("30d"), 22),
        (self._ToMicros("60d"), 22)
    ]
    label_counts = [
        (self._ToMicros("1d"), 0),
        (self._ToMicros("2d"), 0),
        (self._ToMicros("3d"), 0),
        (self._ToMicros("7d"), 0),
        (self._ToMicros("14d"), 10),
        (self._ToMicros("30d"), 10),
        (self._ToMicros("60d"), 10)
    ]
    # pyformat: enable

    # All our clients appeared at the same time (and did not appear since).
    self._CheckAccessStats(u"All", expected=all_counts)

    # All our clients appeared at the same time but this label is only half.
    self._CheckAccessStats(u"Label1", expected=label_counts)

    # All our clients appeared at the same time but this label is only half.
    self._CheckAccessStats(u"Label2", expected=label_counts)

  def testPurgeClientStats(self):
    client_id = test_lib.TEST_CLIENT_ID
    max_age = db.CLIENT_STATS_RETENTION.seconds

    for t in [1 * max_age, 1.5 * max_age, 2 * max_age]:
      with test_lib.FakeTime(t):
        urn = client_id.Add("stats")

        stats_fd = aff4.FACTORY.Create(
            urn, aff4_stats.ClientStats, token=self.token, mode="rw")
        st = rdf_client_stats.ClientStats(RSS_size=int(t))
        stats_fd.AddAttribute(stats_fd.Schema.STATS(st))

        stats_fd.Close()

        if data_store.RelationalDBWriteEnabled():
          data_store.REL_DB.WriteClientStats(client_id.Basename(), st)

    if data_store.RelationalDBReadEnabled("client_stats"):
      stat_entries = data_store.REL_DB.ReadClientStats(
          client_id=client_id.Basename(),
          min_timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))
    else:
      stat_obj = aff4.FACTORY.Open(urn, age=aff4.ALL_TIMES, token=self.token)
      stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))

    self.assertCountEqual([1 * max_age, 1.5 * max_age, 2 * max_age],
                          [e.RSS_size for e in stat_entries])

    with test_lib.FakeTime(2.51 * max_age):
      self._RunPurgeClientStats()

    if data_store.RelationalDBReadEnabled("client_stats"):
      stat_entries = data_store.REL_DB.ReadClientStats(
          client_id=client_id.Basename(),
          min_timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))
    else:
      stat_obj = aff4.FACTORY.Open(urn, age=aff4.ALL_TIMES, token=self.token)
      stat_entries = list(stat_obj.GetValuesForAttribute(stat_obj.Schema.STATS))
    self.assertLen(stat_entries, 1)
    self.assertNotIn(max_age, [e.RSS_size for e in stat_entries])


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


@db_test_lib.DualDBTest
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

  def testPurgeServerStats(self):
    if not data_store.RelationalDBReadEnabled():
      self.skipTest("Test is only for the relational DB. Skipping...")
    fake_stats_collector = default_stats_collector.DefaultStatsCollector([
        stats_utils.CreateCounterMetadata("fake_counter"),
    ])
    timestamp0 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)
    timestamp1 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)
    timestamp2 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3600)
    timestamp3 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4800)
    config_overrides = {
        "Database.useForReads.stats": True,
        "StatsStore.stats_ttl_hours": 1
    }
    zero_duration = rdfvalue.Duration(0)
    # Backslash continuation is explicitly allowed by Google's style guide for
    # nested context manager expressions spanning 3 or more lines.
    # pylint: disable=g-backslash-continuation
    with test_lib.ConfigOverrider(config_overrides), \
         stats_test_utils.FakeStatsContext(fake_stats_collector), \
         mock.patch.object(system, "_STATS_DELETION_BATCH_SIZE", 1), \
         mock.patch.object(system, "_stats_checkpoint_period", zero_duration):
      with test_lib.FakeTime(rdfvalue.RDFDatetime(timestamp0)):
        stats_store._WriteStats(process_id="fake_process_id")
      with test_lib.FakeTime(rdfvalue.RDFDatetime(timestamp1)):
        stats_collector_instance.Get().IncrementCounter("fake_counter")
        stats_store._WriteStats(process_id="fake_process_id")
        expected_results = {
            "fake_process_id": {
                "fake_counter": [(0, timestamp0), (1, timestamp1)]
            }
        }
        self.assertDictEqual(
            stats_store.ReadStats("f", "fake_counter"), expected_results)
      with test_lib.FakeTime(timestamp2):
        stats_store._WriteStats(process_id="fake_process_id")
        expected_results = {
            "fake_process_id": {
                "fake_counter": [(0, timestamp0), (1, timestamp1),
                                 (1, timestamp2)]
            }
        }
        self.assertDictEqual(
            stats_store.ReadStats("f", "fake_counter"), expected_results)
      with test_lib.FakeTime(timestamp3):
        cron_name = compatibility.GetName(system.PurgeServerStatsCronJob)
        cronjobs.ScheduleSystemCronJobs(names=[cron_name])
        job_data = data_store.REL_DB.ReadCronJobs([cron_name])[0]
        cron_run = rdf_cronjobs.CronJobRun(cron_job_id=cron_name)
        cron_run.GenerateRunId()
        cron_run.started_at = rdfvalue.RDFDatetime.Now()
        cron = system.PurgeServerStatsCronJob(cron_run, job_data)
        cron.Run()
        # timestamp0 and timestamp1 are older than 1h, so they should get
        # deleted.
        expected_results = {
            "fake_process_id": {
                "fake_counter": [(1, timestamp2)]
            }
        }
        self.assertDictEqual(
            stats_store.ReadStats("f", "fake_counter"), expected_results)
        self.assertEqual("Deleted 2 stats entries.\nDeleted 1 stats entries.",
                         cron.run_state.log_message)

  def _RunPurgeClientStats(self):
    run = rdf_cronjobs.CronJobRun()
    job = rdf_cronjobs.CronJob()
    system.PurgeClientStatsCronJob(run, job).Run()


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
