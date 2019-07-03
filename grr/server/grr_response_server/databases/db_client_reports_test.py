#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for client-reports DB functionality."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import time_utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_server.databases import db
from grr.test_lib import test_lib

# Client label used by tests in this file.
_TEST_LABEL = "test-🚀-label"


def _CreateGRRVersionGraphSeries(num_graph_series):
  """Creates GRR_VERSION graphs for use in tests in this file.

  Args:
    num_graph_series: The number of graph series to create.

  Returns:
    A list of rdf_stats.GraphSeries of type GRR_VERSION containing realistic
    test data.
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


# 'db' attribute and assert methods aren't defined in this mixin's ancestry.
# pytype: disable=attribute-error
class DatabaseTestClientReportsMixin(object):
  """Mixin that adds tests for client-reports DB functionality."""

  def testReadAllClientGraphSeries(self):
    graph_series_list = _CreateGRRVersionGraphSeries(2)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)):
      self.db.WriteClientGraphSeries(graph_series_list[0], _TEST_LABEL)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)):
      self.db.WriteClientGraphSeries(graph_series_list[1], _TEST_LABEL)
    fetched_data = self.db.ReadAllClientGraphSeries(
        _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION)
    expected_data = {
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1): graph_series_list[0],
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2): graph_series_list[1],
    }
    self.assertDictEqual(fetched_data, expected_data)

  def testReadAllClientGraphSeries_NonExistentLabel(self):
    self.assertEmpty(
        self.db.ReadAllClientGraphSeries(
            "nonexistent", rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION))

  def testReadAllClientGraphSeries_MissingType(self):
    graph_series = _CreateGRRVersionGraphSeries(1)[0]
    self.db.WriteClientGraphSeries(graph_series, _TEST_LABEL)
    self.assertNotEmpty(
        self.db.ReadAllClientGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION))
    self.assertEmpty(
        self.db.ReadAllClientGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.OS_TYPE))

  def testReadAllClientGraphSeries_InTimeRange(self):
    date = rdfvalue.RDFDatetime.FromHumanReadable("2017-10-02")

    graph_series_list = _CreateGRRVersionGraphSeries(10)
    for i, graph_series in enumerate(graph_series_list):
      with test_lib.FakeTime(date + rdfvalue.Duration.FromDays(i)):
        self.db.WriteClientGraphSeries(graph_series, _TEST_LABEL)

    time_range = time_utils.TimeRange(date + rdfvalue.Duration.FromDays(6),
                                      date + rdfvalue.Duration.FromDays(10))
    fetched_data = self.db.ReadAllClientGraphSeries(
        _TEST_LABEL,
        rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION,
        time_range=time_range)
    expected_data = {
        date + rdfvalue.Duration.FromDays(6): graph_series_list[6],
        date + rdfvalue.Duration.FromDays(7): graph_series_list[7],
        date + rdfvalue.Duration.FromDays(8): graph_series_list[8],
        date + rdfvalue.Duration.FromDays(9): graph_series_list[9],
    }
    self.assertDictEqual(fetched_data, expected_data)

  def testOverwriteClientGraphSeries(self):
    graph_series = _CreateGRRVersionGraphSeries(1)[0]
    timestamp = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)
    with test_lib.FakeTime(timestamp):
      self.db.WriteClientGraphSeries(graph_series, _TEST_LABEL)
    self.db.WriteClientGraphSeries(
        graph_series, _TEST_LABEL, timestamp=timestamp)
    fetched_data = self.db.ReadAllClientGraphSeries(
        _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION)
    self.assertDictEqual(fetched_data, {timestamp: graph_series})

  def testReadMostRecentClientGraphSeries(self):
    graph_series_list = _CreateGRRVersionGraphSeries(5)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1000)):
      self.db.WriteClientGraphSeries(graph_series_list[0], _TEST_LABEL)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2000)):
      self.db.WriteClientGraphSeries(graph_series_list[1], _TEST_LABEL)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3000)):
      self.db.WriteClientGraphSeries(graph_series_list[2], _TEST_LABEL)
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4000)):
      self.db.WriteClientGraphSeries(graph_series_list[3], "custom-label")
    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(5000)):
      self.db.WriteClientGraphSeries(graph_series_list[4], "custom-label")
    self.assertEqual(
        self.db.ReadMostRecentClientGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION),
        graph_series_list[2])
    self.assertEqual(
        self.db.ReadMostRecentClientGraphSeries(
            "custom-label", rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION),
        graph_series_list[4])

  def testMostRecentGraphSeries_NonExistentLabel(self):
    self.assertIsNone(
        self.db.ReadMostRecentClientGraphSeries(
            "nonexistent", rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION))

  def testReadMostRecentClientGraphSeries_MissingType(self):
    graph_series = _CreateGRRVersionGraphSeries(1)[0]
    self.db.WriteClientGraphSeries(graph_series, _TEST_LABEL)
    self.assertIsNotNone(
        self.db.ReadMostRecentClientGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION))
    self.assertIsNone(
        self.db.ReadMostRecentClientGraphSeries(
            _TEST_LABEL, rdf_stats.ClientGraphSeries.ReportType.OS_TYPE))

  def testWriteAndReadLongLabel(self):
    label = "🚀" * db.MAX_LABEL_LENGTH
    graph_series = _CreateGRRVersionGraphSeries(1)[0]
    self.db.WriteClientGraphSeries(graph_series, label)
    self.assertIsNotNone(
        self.db.ReadMostRecentClientGraphSeries(
            label, rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION))

  def testWriteTooLongLabelRaises(self):
    label = "a" * (db.MAX_LABEL_LENGTH + 1)
    graph_series = _CreateGRRVersionGraphSeries(1)[0]
    with self.assertRaises(ValueError):
      self.db.WriteClientGraphSeries(graph_series, label)


# pytype: enable=attribute-error
# This file is a test library and thus does not require a __main__ block.
