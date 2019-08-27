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
from grr_response_server import data_store


def WriteGraphSeries(graph_series, label):
  """Writes graph series for a particularb client label to the DB.

  Args:
    graph_series: A series of rdf_stats.Graphs containing aggregated data for a
      particular report-type.
    label: Client label by which data in the graph_series was aggregated.
  """
  data_store.REL_DB.WriteClientGraphSeries(graph_series, label)


def FetchAllGraphSeries(
    label,
    report_type,
    period = None,
):
  """Fetches graph series for the given label and report-type from the DB.

  Args:
    label: Client label to fetch data for.
    report_type: rdf_stats.ClientGraphSeries.ReportType to fetch data for.
    period: rdfvalue.Duration specifying how far back in time to fetch
      data. If not provided, all data for the given label and report-type will
      be returned.

  Returns:
    A dict mapping timestamps to graph-series. The timestamps
    represent when the graph-series were written to the datastore.
  """
  if period is None:
    time_range = None
  else:
    range_end = rdfvalue.RDFDatetime.Now()
    time_range = time_utils.TimeRange(range_end - period, range_end)
  return data_store.REL_DB.ReadAllClientGraphSeries(
      label, report_type, time_range=time_range)


def FetchMostRecentGraphSeries(label,
                               report_type,
                              ):
  """Fetches the latest graph series for a client label from the DB.

  Args:
    label: Client label to fetch data for.
    report_type: rdf_stats.ClientGraphSeries.ReportType to fetch data for.

  Returns:
    The graph series for the given label and report type that was last
    written to the DB, or None if no series for that label and report-type
    exist.
  """
  return data_store.REL_DB.ReadMostRecentClientGraphSeries(label, report_type)
