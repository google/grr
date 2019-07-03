#!/usr/bin/env python
"""Tests for client report utilities."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from future.builtins import range

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_server import client_report_utils
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib

# Client label used by tests in this file.
_TEST_LABEL = "test_label"


def _CreateGRRVersionGraphSeries(num_graph_series):
  """Creates GRR_VERSION graphs for use in tests in this file.

  Args:
    num_graph_series: The number of graph series to create.

  Returns:
    A list of rdf_stats.ClientGraphSeries of type GRR_VERSION containing
    realistic test data.
  """
  graph_series_list = []
  for series_index in range(num_graph_series):
    graph_series = rdf_stats.ClientGraphSeries(
        report_type=rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION)
    for i, period in enumerate([1, 7, 14, 30]):
      graph = rdf_stats.Graph()
      graph.title = "%s day actives for %s label" % (period, _TEST_LABEL)
      graph.Append(label="GRR linux amd64 3000", y_value=i * series_index)
      graph.Append(label="GRR linux amd64 3001", y_value=i * series_index)
      graph_series.graphs.Append(graph)
    graph_series_list.append(graph_series)
  return graph_series_list


def _CreateNDayActiveGraphSeries(num_graph_series):
  """Creates N_DAY_ACTIVE graphs for use in tests in this file.

  Args:
    num_graph_series: The number of graph series to create.

  Returns:
    A list of rdf_stats.ClientGraphSeries of type N_DAY_ACTIVE containing
    realistic test data.
  """
  graph_series_list = []
  for series_index in range(num_graph_series):
    graph_series = rdf_stats.ClientGraphSeries(
        report_type=rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE)
    graph_series.graphs.Append(rdf_stats.Graph())
    for i, period in enumerate([1, 2, 3, 7, 14, 30, 60]):
      graph_series.graphs[0].Append(x_value=period, y_value=i * series_index)
      graph_series.graphs[0].Append(x_value=period, y_value=i * series_index)
    graph_series_list.append(graph_series)
  return graph_series_list


@db_test_lib.DualDBTest
class ClientReportUtilsTest(test_lib.GRRBaseTest):

  def testWriteGraphSeries_MultipleGraphs(self):
    # Simulate two runs of the cronjob that computes GRR-version stats.
    graph_series_list = _CreateGRRVersionGraphSeries(2)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(1000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[0], _TEST_LABEL, token=self.token)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(2000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[1], _TEST_LABEL, token=self.token)
    fetched_data = client_report_utils.FetchAllGraphSeries(
        _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION)
    expected_data = {
        rdfvalue.RDFDatetime(1000): graph_series_list[0],
        rdfvalue.RDFDatetime(2000): graph_series_list[1],
    }
    self.assertDictEqual(fetched_data, expected_data)

  def testWriteGraphSeries_SingleGraph(self):
    # Simulate two runs of the cronjob that computes n-day-active stats.
    graph_series_list = _CreateNDayActiveGraphSeries(2)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(1000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[0], _TEST_LABEL, token=self.token)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(2000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[1], _TEST_LABEL, token=self.token)
    fetched_data = client_report_utils.FetchAllGraphSeries(
        _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE)
    expected_data = {
        rdfvalue.RDFDatetime(1000): graph_series_list[0],
        rdfvalue.RDFDatetime(2000): graph_series_list[1],
    }
    self.assertDictEqual(fetched_data, expected_data)

  def testFetchAllGraphSeries_NonExistentLabel(self):
    self.assertEmpty(
        client_report_utils.FetchAllGraphSeries(
            "nonexistent", rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION))

  def testFetchAllGraphSeries_MissingType(self):
    graph_series = _CreateGRRVersionGraphSeries(1)[0]
    client_report_utils.WriteGraphSeries(graph_series, _TEST_LABEL, token=None)
    self.assertNotEmpty(
        client_report_utils.FetchAllGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION))
    self.assertEmpty(
        client_report_utils.FetchAllGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.OS_TYPE))

  def testFetchAllGraphSeries_InPeriod(self):
    graph_series_list = _CreateGRRVersionGraphSeries(10)
    for i, graph_series in enumerate(graph_series_list):
      with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(i)):
        client_report_utils.WriteGraphSeries(
            graph_series, _TEST_LABEL, token=self.token)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10)):
      # It is now 1 second after the last graph-series was written. Fetch all
      # series written starting from 4 seconds ago.
      fetched_data = client_report_utils.FetchAllGraphSeries(
          _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION,
          rdfvalue.Duration("4s"))
      expected_data = {
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(6): graph_series_list[6],
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(7): graph_series_list[7],
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(8): graph_series_list[8],
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(9): graph_series_list[9],
      }
      self.assertSequenceEqual(fetched_data, expected_data)

  def testFetchMostRecentGraphSeries_MultipleGraphs(self):
    graph_series_list = _CreateGRRVersionGraphSeries(2)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(1000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[0], _TEST_LABEL, token=self.token)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(2000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[1], _TEST_LABEL, token=self.token)
    self.assertEqual(
        client_report_utils.FetchMostRecentGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION),
        graph_series_list[1])

  def testFetchMostRecentGraphSeries_SingleGraph(self):
    graph_series_list = _CreateNDayActiveGraphSeries(2)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(1000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[0], _TEST_LABEL, token=self.token)
    with test_lib.FakeTime(rdfvalue.RDFDatetime(2000)):
      client_report_utils.WriteGraphSeries(
          graph_series_list[1], _TEST_LABEL, token=self.token)
    self.assertEqual(
        client_report_utils.FetchMostRecentGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE),
        graph_series_list[1])

  def testMostRecentGraphSeries_NonExistentLabel(self):
    self.assertIsNone(
        client_report_utils.FetchMostRecentGraphSeries(
            "nonexistent", rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE))

  def testFetchMostRecentGraphSeries_MissingType(self):
    graph_series = _CreateNDayActiveGraphSeries(1)[0]
    client_report_utils.WriteGraphSeries(graph_series, _TEST_LABEL, token=None)
    self.assertIsNotNone(
        client_report_utils.FetchMostRecentGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE))
    self.assertIsNone(
        client_report_utils.FetchMostRecentGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.OS_TYPE))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
