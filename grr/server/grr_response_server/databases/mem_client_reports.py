#!/usr/bin/env python
"""In-memory implementation of DB methods for handling client report data."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from future.utils import iteritems
from typing import Dict, Optional, Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import time_utils
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs


# TODO(user): Remove this pytype exception when DB mixins are refactored to
# be more self-contained (self.client_graph_series is not initialized
# in the mixin's __init__ method, as it should be).
# pytype: disable=attribute-error
class InMemoryDBClientReportsMixin(object):
  """Mixin providing an in-memory implementation of client reports DB logic.

  Attributes:
    client_graph_series: A dict mapping (client-label, report-type, timestamp)
      tuples to rdf_stats.ClientGraphSeries. This field is initialized in
      mem.py, for consistency with other in-memory DB mixins.
  """

  @utils.Synchronized
  def WriteClientGraphSeries(self, graph_series,
                             client_label,
                             timestamp):
    """See db.Database."""
    series_key = (client_label, graph_series.report_type, timestamp.Copy())
    self.client_graph_series[series_key] = graph_series.Copy()

  @utils.Synchronized
  def ReadAllClientGraphSeries(
      self,
      client_label,
      report_type,
      time_range = None,
  ):
    """See db.Database."""
    series_with_timestamps = {}
    for series_key, series in iteritems(self.client_graph_series):
      series_label, series_type, timestamp = series_key
      if series_label == client_label and series_type == report_type:
        if time_range is not None and not time_range.Includes(timestamp):
          continue
        series_with_timestamps[timestamp.Copy()] = series.Copy()
    return series_with_timestamps

  @utils.Synchronized
  def ReadMostRecentClientGraphSeries(self, client_label,
                                      report_type
                                     ):
    """See db.Database."""
    series_with_timestamps = self.ReadAllClientGraphSeries(
        client_label, report_type)
    if not series_with_timestamps:
      return None
    _, latest_series = list(sorted(iteritems(series_with_timestamps)))[-1]
    return latest_series


# pytype: enable=attribute-error
