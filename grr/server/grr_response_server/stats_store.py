#!/usr/bin/env python
"""Components for storing and managing server stats."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import re
import threading
import time

from future.utils import iteritems

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import timeseries
from grr_response_server.aff4_objects import stats_store as aff4_stats_store


def ReadStats(process_id_prefix, metric_name, time_range=None, token=None):
  """Reads past values for a given metric from the data-store.

  Args:
    process_id_prefix: String prefix used for matching process ids to query for.
    metric_name: Name of the metric to read past entries for.
    time_range: An optional tuple of RDFDateTime objects representing the range
      of timestamps to query for.
    token: Database token to use for querying the data.

  Returns:
    A nested dict containing all past values for a metric in a given time
    range. The dict is organized in the format expected by the
    StatsStoreDataQuery class:
      - The outermost level (first tier) maps process ids to dicts containing
        metric values for the processes.
      - For single dimensional metrics, dicts at the second tier have a single
        entry mapping the metric name to a list of (metric-value, timestamp)
        tuples. The tuples are sorted by timestamp (increasing).
      - For multi-dimensional metrics, dicts at the n-th tier will have
        keys corresponding to field-values for the (n-1)-th field appearing
        in the metadata definition for the metric. The last tier will have
        dicts mapping the last field name to a list of
        (metric-value, timestamp) tuples (also sorted by timestamp).
  """
  if time_range is None:
    time_range = data_store.DataStore.ALL_TIMESTAMPS

  stats_store_obj = aff4.FACTORY.Create(
      aff4_stats_store.StatsStore.DATA_STORE_ROOT,
      aff4_type=aff4_stats_store.StatsStore,
      mode="r",
      token=token)
  process_ids = stats_store_obj.ListUsedProcessIds()
  filtered_ids = [
      pid for pid in process_ids if pid.startswith(process_id_prefix)
  ]
  return stats_store_obj.MultiReadStats(
      process_ids=filtered_ids,
      metric_name=metric_name,
      timestamp=time_range)


class StatsStoreDataQuery(object):
  """Query class used to results from StatsStore.ReadStats/MultiReadStats.

  NOTE: this class is mutable. Although it's designed with call-chaining in
  mind, you have to create new query object for every new query.
  I.e. - this *will not* work:
    query = stats_store.StatsStoreDataQuery(stats_data)
    counter1 = query.In("pid1").In("counter").SeriesCount()
    counter2 = query.In("pidw").In("counter").SeriesCount()

  But this *will* work:
    query = stats_store.StatsStoreDataQuery(stats_data)
    counter1 = query.In("pid1").In("counter").SeriesCount()
    query = stats_store.StatsStoreDataQuery(stats_data)
    counter2 = query.In("pidw").In("counter").SeriesCount()
  """

  VALUE_QUERY = "value"
  DISTRIBUTION_SUM_QUERY = "distribution_sum"
  DISTRIBUTION_COUNT_QUERY = "distribution_count"

  def __init__(self, stats_data):
    super(StatsStoreDataQuery, self).__init__()
    self.current_dicts = [stats_data]
    self.time_series = None
    self.path = []
    self.query_type = None
    self.aggregate_via = None
    self.sample_interval = None

  def _TimeSeriesFromData(self, data, attr=None):
    """Build time series from StatsStore data."""

    series = timeseries.Timeseries()

    for value, timestamp in data:
      if attr:
        try:
          series.Append(getattr(value, attr), timestamp)
        except AttributeError:
          raise ValueError(
              "Can't find attribute %s in value %s." % (attr, value))
      else:
        if hasattr(value, "sum") or hasattr(value, "count"):
          raise ValueError(
              "Can't treat complext type as simple value: %s" % value)
        series.Append(value, timestamp)

    return series

  @property
  def ts(self):
    """Return single timeseries.Timeseries built by this query."""

    if self.time_series is None:
      raise RuntimeError("Time series weren't built yet.")

    if not self.time_series:
      return timeseries.Timeseries()

    return self.time_series[0]

  def In(self, regex):
    """Narrow query's scope."""

    self.path.append(regex)

    new_current_dicts = []
    for current_dict in self.current_dicts:
      for key, value in iteritems(current_dict):
        m = re.match(regex, key)
        if m and m.string == m.group(0):
          new_current_dicts.append(value)

    self.current_dicts = new_current_dicts
    return self

  def _GetNestedValues(self, dicts):
    """Get all values nested in the given dictionaries.

    Args:
      dicts: List of dictionaries to go through.

    Returns:
      ([nested values], status) where status is True if nested values are
      dictionaries and False otherwise.

    Raises:
      RuntimeError: if some nested values are dictionaries and some are not.
    """
    new_dicts = []
    for current_dict in dicts:
      for _, value in iteritems(current_dict):
        new_dicts.append(value)

    sub_dicts = [x for x in new_dicts if hasattr(x, "iteritems")]
    if not sub_dicts:
      return (new_dicts, False)
    elif len(sub_dicts) == len(new_dicts):
      return (new_dicts, True)
    else:
      raise RuntimeError("Inconsistent values hierarchy.")

  def InAll(self):
    """Use all metrics in the current scope."""

    self.path.append(":all")

    while True:
      self.current_dicts, status = self._GetNestedValues(self.current_dicts)
      if not status:
        break

    return self

  def MakeIncreasing(self):
    """Fixes the time series so that it does not decrement."""
    if self.time_series is None:
      raise RuntimeError("MakeIncreasing must be called after Take*().")

    for time_serie in self.time_series:
      time_serie.MakeIncreasing()
    return self

  def Normalize(self, period, start_time, stop_time, **kwargs):
    """Resample the query with given sampling interval."""
    if self.time_series is None:
      raise RuntimeError("Normalize must be called after Take*().")

    self.sample_interval = period
    self.start_time = start_time
    self.stop_time = stop_time

    for time_serie in self.time_series:
      time_serie.Normalize(period, start_time, stop_time, **kwargs)

    return self

  def InTimeRange(self, range_start, range_end):
    """Only use data points within the given time range."""

    if self.time_series is None:
      raise RuntimeError("InTimeRange must be called after Take*().")

    if range_start is None:
      raise ValueError("range_start can't be None")

    if range_end is None:
      raise ValueError("range_end can't be None")

    for time_serie in self.time_series:
      time_serie.FilterRange(start_time=range_start, stop_time=range_end)

    return self

  def TakeValue(self):
    """Assume metrics in this query are plain values."""

    self.query_type = self.VALUE_QUERY

    self.time_series = []
    for current_dict in self.current_dicts:
      self.time_series.append(self._TimeSeriesFromData(current_dict))

    return self

  def TakeDistributionSum(self):
    """Assume metrics in this query are distributions. Use their sums."""

    self.query_type = self.DISTRIBUTION_SUM_QUERY

    self.time_series = []
    for current_dict in self.current_dicts:
      self.time_series.append(self._TimeSeriesFromData(current_dict, "sum"))

    return self

  def TakeDistributionCount(self):
    """Assume metrics in this query are distributions. Use their counts."""

    self.query_type = self.DISTRIBUTION_COUNT_QUERY

    self.time_series = []
    for current_dict in self.current_dicts:
      self.time_series.append(self._TimeSeriesFromData(current_dict, "count"))

    return self

  def AggregateViaSum(self):
    """Aggregate multiple time series into one by summing them."""
    if self.time_series is None:
      raise RuntimeError("AggregateViaSum must be called after Take*().")

    if self.sample_interval is None:
      raise RuntimeError("Resample() must be called prior to "
                         "AggregateViaSum().")

    if not self.time_series:
      return self

    if len(self.time_series) == 1:
      return self

    current_serie = self.time_series[0]
    for serie in self.time_series[1:]:
      current_serie.Add(serie)

    self.time_series = [current_serie]
    return self

  def AggregateViaMean(self):
    """Aggregate multiple time series into one by calculating mean value."""

    num_time_series = len(self.time_series)
    self.AggregateViaSum()
    self.ts.Rescale(1.0 / num_time_series)

    return self

  def SeriesCount(self):
    """Return number of time series the query was narrowed to."""

    if not self.time_series:
      if not self.current_dicts:
        return 0
      else:
        return len(self.current_dicts)
    else:
      return len(self.time_series)

  def Rate(self):
    """Apply rate function to all time series in this query."""

    if self.time_series is None:
      raise RuntimeError("Rate must be called after Take*().")

    if self.sample_interval is None:
      raise RuntimeError("Normalize() must be called prior to Rate().")

    for time_serie in self.time_series:
      time_serie.ToDeltas()
      time_serie.Rescale(1.0 / self.sample_interval.seconds)

    return self

  def Scale(self, multiplier):
    """Scale value in all time series in this query."""

    if self.time_series is None:
      raise RuntimeError("Scale must be called after Take*().")

    for time_serie in self.time_series:
      time_serie.Rescale(multiplier)

    return self

  def Mean(self):
    """Calculate mean value of a single time serie in this query."""

    if self.time_series is None:
      raise RuntimeError("Mean must be called after Take*().")

    if not self.time_series:
      return 0

    if len(self.time_series) != 1:
      raise RuntimeError("Can only return mean for a single time serie.")

    return self.time_series[0].Mean()


class _StatsStoreWorker(object):
  """_StatsStoreWorker periodically dumps stats data into the stats store."""

  def __init__(self, process_id, thread_name="grr_stats_saver", sleep=None):
    super(_StatsStoreWorker, self).__init__()

    self.process_id = process_id
    self.thread_name = thread_name
    self.sleep = sleep or config.CONFIG["StatsStore.write_interval"]

  def _RunLoop(self):
    """Periodically dumps metric values for the current process to the db."""
    while True:
      logging.debug("Writing stats to stats store.")

      try:
        aff4_stats_store.STATS_STORE.WriteStats(process_id=self.process_id)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("StatsStore exception caught during WriteStats(): %s",
                          e)

      logging.debug("Removing old stats from stats store." "")
      # Maximum time we keep stats store data is three days.
      stats_store_ttl = 60 * 60 * 24 * 3
      try:
        now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
        aff4_stats_store.STATS_STORE.DeleteStats(
            process_id=self.process_id,
            timestamp=(0, now - stats_store_ttl * 1000000))
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "StatsStore exception caught during DeleteStats(): %s", e)

      time.sleep(self.sleep)

  def Run(self):
    self.RunAsync().join()

  def RunAsync(self):
    # pytype: disable=wrong-arg-types
    self.running_thread = threading.Thread(
        name=self.thread_name, target=self._RunLoop)
    # pytype: enable=wrong-arg-types
    self.running_thread.daemon = True
    self.running_thread.start()
    return self.running_thread


class StatsStoreWorkerInit(registry.InitHook):
  """Hook that initializes a _StatsStoreWorker at startup."""
  pre = [aff4_stats_store.StatsStoreInit]

  def RunOnce(self):
    """Initializes a _StatsStoreWorker."""
    # We don't need StatsStoreWorker if there's no StatsStore.process_id in
    # the config.
    stats_process_id = config.CONFIG["StatsStore.process_id"]
    if not stats_process_id:
      return

    stats_store_worker = _StatsStoreWorker(stats_process_id)
    stats_store_worker.RunAsync()
