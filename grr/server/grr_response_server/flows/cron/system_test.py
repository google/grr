#!/usr/bin/env python
"""System cron flows tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from absl import app
from future.builtins import range
import mock

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_server import aff4
from grr_response_server import client_report_utils
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.flows.cron import system
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2


class SystemCronTestMixin(object):

  def setUp(self):
    super(SystemCronTestMixin, self).setUp()

    one_hour_ping = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1h")
    eight_day_ping = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("8d")
    ancient_ping = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("61d")
    self.SetupClientsWithIndices(
        range(0, 10), system="Windows", ping=eight_day_ping)
    self.SetupClientsWithIndices(
        range(10, 20), system="Linux", ping=eight_day_ping)
    self.SetupClientsWithIndices(
        range(20, 22),
        system="Darwin",
        fleetspeak_enabled=True,
        ping=one_hour_ping)
    # These clients shouldn't be analyzed by any of the stats cronjobs.
    self.SetupClientsWithIndices(
        range(22, 24), system="Linux", ping=ancient_ping)

    for i in range(0, 10):
      client_id = u"C.1%015x" % i
      if data_store.AFF4Enabled():
        with aff4.FACTORY.Open(
            client_id, mode="rw", token=self.token) as client:
          client.AddLabels([u"Label1", u"Label2"], owner=u"GRR")
          client.AddLabel(u"UserLabel", owner=u"jim")

      data_store.REL_DB.AddClientLabels(client_id, u"GRR",
                                        [u"Label1", u"Label2"])
      data_store.REL_DB.AddClientLabels(client_id, u"jim", [u"UserLabel"])

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
        st = rdf_client_stats.ClientStats(RSS_size=int(t))

        if data_store.AFF4Enabled():
          with aff4.FACTORY.Create(
              urn, aff4_stats.ClientStats, token=self.token,
              mode="rw") as stats_fd:
            stats_fd.AddAttribute(stats_fd.Schema.STATS(st))

        if data_store.RelationalDBWriteEnabled():
          data_store.REL_DB.WriteClientStats(client_id.Basename(), st)

    if data_store.RelationalDBReadEnabled():
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

    if data_store.RelationalDBReadEnabled():
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
    cron_run = rdf_cronjobs.CronJobRun()
    job_data = rdf_cronjobs.CronJob()
    cron = system.GRRVersionBreakDownCronJob(cron_run, job_data)
    cron.Run()

    self._CheckGRRVersionBreakDown()
    self.assertEqual(cron.run_state.log_message, "Processed 22 clients.")

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


@db_test_lib.DualDBTest
class UpdateFSLastPingTimestampsTest(test_lib.GRRBaseTest):

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testCronJob(self, fs_conn_mock):
    if not data_store.RelationalDBReadEnabled():
      self.skipTest("Test is only for the relational DB. Skipping...")

    client_id1 = "C.0000000000000001"
    client_id2 = "C.0000000000000002"
    client_id3 = "C.0000000000000003"
    client_id4 = "C.0000000000000004"
    client_id5 = "C.0000000000000005"
    client_id6 = "C.0000000000000006"
    client_id7 = "C.0000000000000007"

    data_store.REL_DB.WriteClientMetadata(client_id1, fleetspeak_enabled=False)
    data_store.REL_DB.WriteClientMetadata(client_id2, fleetspeak_enabled=True)
    data_store.REL_DB.WriteClientMetadata(
        client_id3,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3),
        fleetspeak_enabled=True)
    data_store.REL_DB.WriteClientMetadata(
        client_id4,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(41),
        fleetspeak_enabled=True)
    data_store.REL_DB.WriteClientMetadata(
        client_id5,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5),
        fleetspeak_enabled=True)
    data_store.REL_DB.WriteClientMetadata(
        client_id6,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(61),
        fleetspeak_enabled=True)
    data_store.REL_DB.WriteClientMetadata(
        client_id7,
        last_ping=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(68),
        fleetspeak_enabled=True)

    fs_enabled_ids = [
        client_id2, client_id3, client_id4, client_id5, client_id6, client_id7
    ]
    fs_clients = {}
    for i, client_id in enumerate(fs_enabled_ids):
      client_number = i + 2
      fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
      fs_client = admin_pb2.Client(client_id=fs_client_id)
      fs_client.last_contact_time.FromSeconds(client_number * 10)
      fs_clients[fs_client_id] = fs_client

    def FakeListClients(list_request):
      clients = []
      for fs_client_id in list_request.client_ids:
        clients.append(fs_clients[fs_client_id])
      return admin_pb2.ListClientsResponse(clients=clients)

    fs_conn_mock.outgoing.ListClients = FakeListClients

    cron_run = rdf_cronjobs.CronJobRun()
    job_data = rdf_cronjobs.CronJob()
    cron = system.UpdateFSLastPingTimestamps(cron_run, job_data)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)):
      with test_lib.ConfigOverrider({
          "Server.fleetspeak_last_ping_threshold": "35s",
          "Server.fleetspeak_list_clients_batch_size": 2,
      }):
        cron.Run()

    actual_timestamps = data_store.REL_DB.ReadClientLastPings()
    expected_timestamps = {
        # Skipped because not a Fleetspeak client.
        client_id1: None,
        client_id2: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(20),
        client_id3: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(30),
        # Skipped because FS timestamp is old.
        client_id4: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(41),
        client_id5: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(50),
        # Skipped because FS timestamp is old.
        client_id6: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(61),
        # Skipped because existing GRR timestamp is too recent.
        client_id7: rdfvalue.RDFDatetime.FromSecondsSinceEpoch(68),
    }
    self.assertEqual(actual_timestamps, expected_timestamps)
    self.assertMultiLineEqual(cron._log_messages.popleft(),
                              "Updated timestamps for 3 clients.")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
