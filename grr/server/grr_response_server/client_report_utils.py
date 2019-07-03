#!/usr/bin/env python
"""Utilities for managing client-report data."""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function
from __future__ import unicode_literals

from typing import Dict, Optional, Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import time_utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server.aff4_objects import stats as aff4_stats


class AFF4AttributeTypeError(TypeError):

  def __init__(self, attr_type):
    super(AFF4AttributeTypeError, self).__init__(
        "Expected AFF4 attribute to be of type GraphSeries or type Graph, "
        "but it was of type %s." % attr_type.__name__)


def GetAFF4ClientReportsURN():
  return rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")


def _GetAFF4AttributeForReportType(report_type
                                  ):
  """Returns the corresponding AFF4 attribute for the given report type."""
  if report_type == rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION:
    return aff4_stats.ClientFleetStats.SchemaCls.GRRVERSION_HISTOGRAM
  elif report_type == rdf_stats.ClientGraphSeries.ReportType.OS_TYPE:
    return aff4_stats.ClientFleetStats.SchemaCls.OS_HISTOGRAM
  elif report_type == rdf_stats.ClientGraphSeries.ReportType.OS_RELEASE:
    return aff4_stats.ClientFleetStats.SchemaCls.RELEASE_HISTOGRAM
  elif report_type == rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE:
    return aff4_stats.ClientFleetStats.SchemaCls.LAST_CONTACTED_HISTOGRAM
  else:
    raise ValueError("Unknown report type %s." % report_type)


def WriteGraphSeries(graph_series,
                     label,
                     token = None):
  """Writes graph series for a particular client label to the DB.

  Args:
    graph_series: A series of rdf_stats.Graphs containing aggregated data for a
      particular report-type.
    label: Client label by which data in the graph_series was aggregated.
    token: ACL token to use for writing to the legacy (non-relational)
      datastore.

  Raises:
    AFF4AttributeTypeError: If, when writing to the legacy DB, an unexpected
    report-data type is encountered.
  """
  if data_store.RelationalDBEnabled():
    data_store.REL_DB.WriteClientGraphSeries(graph_series, label)

  if _ShouldUseLegacyDatastore():
    # We need to use the __call__() method of the aff4.Attribute class
    # to instantiate Graph and GraphSeries objects, or AFF4Object.AddAttribute()
    # won't work.
    aff4_attr = _GetAFF4AttributeForReportType(graph_series.report_type)()

    if isinstance(aff4_attr, rdf_stats.GraphSeries):
      for graph in graph_series.graphs:
        aff4_attr.Append(graph)
    elif isinstance(aff4_attr, rdf_stats.Graph):
      for sample in graph_series.graphs[0]:
        aff4_attr.Append(x_value=sample.x_value, y_value=sample.y_value)
    else:
      raise AFF4AttributeTypeError(aff4_attr.__class__)

    with aff4.FACTORY.Create(
        GetAFF4ClientReportsURN().Add(label),
        aff4_type=aff4_stats.ClientFleetStats,
        mode="w",
        token=token) as stats_for_label:
      stats_for_label.AddAttribute(aff4_attr)


def FetchAllGraphSeries(
    label,
    report_type,
    period = None,
    token = None
):
  """Fetches graph series for the given label and report-type from the DB.

  Args:
    label: Client label to fetch data for.
    report_type: rdf_stats.ClientGraphSeries.ReportType to fetch data for.
    period: rdfvalue.Duration specifying how far back in time to fetch data. If
      not provided, all data for the given label and report-type will be
      returned.
    token: ACL token to use for reading from the legacy (non-relational)
      datastore.

  Raises:
    AFF4AttributeTypeError: If, when reading to the legacy DB, an unexpected
    report-data type is encountered.

  Returns:
    A dict mapping timestamps to graph-series. The timestamps
    represent when the graph-series were written to the datastore.
  """
  if _ShouldUseLegacyDatastore():
    return _FetchAllGraphSeriesFromTheLegacyDB(
        label, report_type, period=period, token=token)

  if period is None:
    time_range = None
  else:
    range_end = rdfvalue.RDFDatetime.Now()
    time_range = time_utils.TimeRange(range_end - period, range_end)
  return data_store.REL_DB.ReadAllClientGraphSeries(
      label, report_type, time_range=time_range)


def _FetchAllGraphSeriesFromTheLegacyDB(
    label,
    report_type,
    period = None,
    token = None
):
  """Fetches graph-series from the legacy DB [see FetchAllGraphSeries()]."""
  if period is None:
    time_range = aff4.ALL_TIMES
  else:
    range_end = rdfvalue.RDFDatetime.Now()
    time_range = (range_end - period, range_end)
  series_with_timestamps = {}
  try:
    stats_for_label = aff4.FACTORY.Open(
        GetAFF4ClientReportsURN().Add(label),
        aff4_type=aff4_stats.ClientFleetStats,
        mode="r",
        age=time_range,
        token=token)
  except aff4.InstantiationError:
    # Nothing to return for the given label and report-type.
    return series_with_timestamps
  aff4_attr = _GetAFF4AttributeForReportType(report_type)
  if aff4_attr.attribute_type == rdf_stats.GraphSeries:
    for graphs in stats_for_label.GetValuesForAttribute(aff4_attr):
      graph_series = rdf_stats.ClientGraphSeries(report_type=report_type)
      for graph in graphs:
        graph_series.graphs.Append(graph)
      series_with_timestamps[graphs.age] = graph_series
  elif aff4_attr.attribute_type == rdf_stats.Graph:
    for graph in stats_for_label.GetValuesForAttribute(aff4_attr):
      graph_series = rdf_stats.ClientGraphSeries(report_type=report_type)
      graph_series.graphs.Append(graph)
      series_with_timestamps[graph.age] = graph_series
  else:
    raise AFF4AttributeTypeError(aff4_attr.attribute_type)
  return series_with_timestamps


def FetchMostRecentGraphSeries(label,
                               report_type,
                               token = None
                              ):
  """Fetches the latest graph series for a client label from the DB.

  Args:
    label: Client label to fetch data for.
    report_type: rdf_stats.ClientGraphSeries.ReportType to fetch data for.
    token: ACL token to use for reading from the legacy (non-relational)
      datastore.

  Raises:
    AFF4AttributeTypeError: If, when reading to the legacy DB, an unexpected
    report-data type is encountered.

  Returns:
    The graph series for the given label and report type that was last
    written to the DB, or None if no series for that label and report-type
    exist.
  """
  if _ShouldUseLegacyDatastore():
    return _FetchMostRecentGraphSeriesFromTheLegacyDB(
        label, report_type, token=token)

  return data_store.REL_DB.ReadMostRecentClientGraphSeries(label, report_type)


def _FetchMostRecentGraphSeriesFromTheLegacyDB(
    label,
    report_type,
    token = None
):
  """Fetches the latest graph-series for a client label from the legacy DB.

  Args:
    label: Client label to fetch data for.
    report_type: rdf_stats.ClientGraphSeries.ReportType to fetch data for.
    token: ACL token to use for reading from the DB.

  Raises:
    AFF4AttributeTypeError: If an unexpected report-data type is encountered.

  Returns:
    The graph series for the given label and report type that was last
    written to the DB, or None if no series for that label and report-type
    exist.
  """
  try:
    stats_for_label = aff4.FACTORY.Open(
        GetAFF4ClientReportsURN().Add(label),
        aff4_type=aff4_stats.ClientFleetStats,
        mode="r",
        token=token)
  except aff4.InstantiationError:
    # Nothing to return for the given label and report-type.
    return None
  aff4_attr = _GetAFF4AttributeForReportType(report_type)
  graph_series = rdf_stats.ClientGraphSeries(report_type=report_type)
  if aff4_attr.attribute_type == rdf_stats.GraphSeries:
    graphs = stats_for_label.Get(aff4_attr)
    if graphs is None:
      return None
    for graph in graphs:
      graph_series.graphs.Append(graph)
  elif aff4_attr.attribute_type == rdf_stats.Graph:
    graph = stats_for_label.Get(aff4_attr)
    if graph is None:
      return None
    graph_series.graphs.Append(graph)
  else:
    raise AFF4AttributeTypeError(aff4_attr.attribute_type)
  return graph_series


def _ShouldUseLegacyDatastore():
  """Returns a boolean indicating whether we should use the legacy datastore.

  If a relational DB implementation is available, report data will get saved to
  the relational DB, in addition to the legacy DB. However, we will still be
  reading from the legacy DB until a config option specific to client reports
  is enabled. When that happens, we will also stop writing to the legacy DB.
  """
  return not data_store.RelationalDBEnabled()
