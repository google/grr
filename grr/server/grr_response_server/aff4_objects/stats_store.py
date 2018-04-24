#!/usr/bin/env python
"""Storage implementation for gathered statistics.

Statistics collected by StatsCollector (see lib/stats.py) is stored in AFF4
space. Statistics data for different parts of the system is separated by
process ids. For example, for the frontend, process id may be "frontend",
for worker - "worker", etc.

On the AFF4 statistics data is stored under aff4:/stats_store.
aff4:/stats_store itself is a URN of a StatsStore object that can be used
for querying stored data and saving new stats.

For every process id, aff4:/stats_store/<process id> object of type
StatsStoreProcessData is created. This object stores metadata of all
the metrics in the METRICS_METADATA field. All the collected statistics
data are written as aff4:stats_store/<metric name> attributes to the
aff4:/stats_store/<process id> row. This way we can easily and efficiently
query statistics data for a given set of metrics for a given process id
for a given time range.

Metrics metadata are stored separately from the values themselves for
efficiency reasons. Metadata objects are created when metrics are registered.
They carry extensive information about the metrics, like metric name and
docstring, metric type, etc. This information does not change (unless changes
GRR's source code changes) and so it doesn't make sense to duplicate it
every time we write a new set of statistics data to the datastore. Therefore
metadata for all the metrics is stored in
StatsStoreProcessData.METRICS_METADATA. Metrics' values themselves are
stored as datastore row attributes.

Statistics is written to the data store by StatsStoreWorker. It periodically
fetches values for all the metrics and writes them to corresponding
object on AFF4.
"""


import logging
import re
import threading
import time


from grr import config
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import stats_values
from grr.server.grr_response_server import timeseries


class StatsStoreProcessData(aff4.AFF4Object):
  """Stores stats data for a particular process."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for StatsStoreProcessData."""

    METRICS_METADATA = aff4.Attribute(
        "aff4:stats_store_process_data/metrics_metadata",
        stats_values.StatsStoreMetricsMetadata,
        creates_new_object_version=False,
        versioned=False)

  def WriteMetadataDescriptors(self, metrics_metadata, timestamp=None):
    current_metadata = self.Get(
        self.Schema.METRICS_METADATA,
        default=stats_values.StatsStoreMetricsMetadata())

    if current_metadata.AsDict() != metrics_metadata:
      store_metadata = stats_values.StatsStoreMetricsMetadata(
          metrics=metrics_metadata.values())
      self.AddAttribute(
          self.Schema.METRICS_METADATA, store_metadata, age=timestamp)
      self.Flush()

  def WriteStats(self, timestamp=None):
    metrics_metadata = stats.STATS.GetAllMetricsMetadata()
    self.WriteMetadataDescriptors(metrics_metadata, timestamp=timestamp)
    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.StatsWriteMetrics(
          self.urn, metrics_metadata, timestamp=timestamp)

  def DeleteStats(self, timestamp=data_store.DataStore.ALL_TIMESTAMPS):
    """Deletes all stats in the given time range."""
    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.StatsDeleteStatsInRange(self.urn, timestamp)


class StatsStore(aff4.AFF4Volume):
  """Implementation of the long-term storage of collected stats data.

  This class allows to write current stats data to the data store, read
  and delete them. StatsStore uses data_store to store the data.
  All historical stats data are stored in a single data store subject per
  process. By process we mean, for example: "admin UI", "worker #1",
  "worker #3", etc. Stats data are stored as subject's attributes.
  """

  DATA_STORE_ROOT = rdfvalue.RDFURN("aff4:/stats_store")

  ALL_TIMESTAMPS = data_store.DataStore.ALL_TIMESTAMPS
  NEWEST_TIMESTAMP = data_store.DataStore.NEWEST_TIMESTAMP

  def Initialize(self):
    super(StatsStore, self).Initialize()
    if self.urn is None:
      self.urn = self.DATA_STORE_ROOT

  def WriteStats(self, process_id=None, timestamp=None):
    """Writes current stats values to the data store with a given timestamp."""
    if not process_id:
      raise ValueError("process_id can't be None")

    process_data = aff4.FACTORY.Create(
        self.urn.Add(process_id),
        StatsStoreProcessData,
        mode="rw",
        token=self.token)
    process_data.WriteStats(timestamp=timestamp)

  def ListUsedProcessIds(self):
    """List process ids that were used when saving data to stats store."""
    return [urn.Basename() for urn in self.ListChildren()]

  def ReadMetadata(self, process_id=None):
    """Reads metadata of stored values for the given process."""

    if not process_id:
      raise ValueError("process_id can't be None")

    results = self.MultiReadMetadata(process_ids=[process_id])

    try:
      return results[process_id]
    except KeyError:
      return {}

  def MultiReadMetadata(self, process_ids=None):
    """Reads metadata of stored values for multiple given processes."""

    if not process_ids:
      process_ids = self.ListUsedProcessIds()

    subjects = [
        self.DATA_STORE_ROOT.Add(process_id) for process_id in process_ids
    ]
    subjects_data = aff4.FACTORY.MultiOpen(
        subjects, mode="r", token=self.token, aff4_type=StatsStoreProcessData)

    results = {}
    for subject_data in subjects_data:
      results[subject_data.urn.Basename()] = subject_data.Get(
          subject_data.Schema.METRICS_METADATA)

    for process_id in process_ids:
      results.setdefault(process_id, stats_values.StatsStoreMetricsMetadata())

    return results

  def ReadStats(self,
                process_id=None,
                metric_name=None,
                timestamp=ALL_TIMESTAMPS,
                limit=10000):
    """Reads stats values from the data store for the current process."""
    if not process_id:
      raise ValueError("process_id can't be None")

    results = self.MultiReadStats(
        process_ids=[process_id],
        metric_name=metric_name,
        timestamp=timestamp,
        limit=limit)
    try:
      return results[process_id]
    except KeyError:
      return {}

  def MultiReadStats(self,
                     process_ids=None,
                     metric_name=None,
                     timestamp=ALL_TIMESTAMPS,
                     limit=10000):
    """Reads historical data for multiple process ids at once."""
    if not process_ids:
      process_ids = self.ListUsedProcessIds()

    multi_metadata = self.MultiReadMetadata(process_ids=process_ids)

    subjects = [
        self.DATA_STORE_ROOT.Add(process_id) for process_id in process_ids
    ]
    return data_store.DB.StatsReadDataForProcesses(
        subjects, metric_name, multi_metadata, timestamp=timestamp, limit=limit)

  def DeleteStats(self, process_id=None, timestamp=ALL_TIMESTAMPS):
    """Deletes all stats in the given time range."""

    if not process_id:
      raise ValueError("process_id can't be None")

    process_data = aff4.FACTORY.Create(
        self.urn.Add(process_id),
        StatsStoreProcessData,
        mode="w",
        token=self.token)
    process_data.DeleteStats(timestamp=timestamp)


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
          raise ValueError("Can't find attribute %s in value %s." % (attr,
                                                                     value))
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
      for key, value in current_dict.iteritems():
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
      for _, value in current_dict.iteritems():
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
    """Only use data points withing given time range."""

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


# Global StatsStore object
STATS_STORE = None


class StatsStoreWorker(object):
  """StatsStoreWorker periodically dumps stats data into the stats store."""

  def __init__(self,
               stats_store,
               process_id,
               thread_name="grr_stats_saver",
               sleep=None):
    super(StatsStoreWorker, self).__init__()

    self.stats_store = stats_store
    self.process_id = process_id
    self.thread_name = thread_name
    self.sleep = sleep or config.CONFIG["StatsStore.write_interval"]

  def _RunLoop(self):
    while True:
      logging.debug("Writing stats to stats store.")

      try:
        self.stats_store.WriteStats(process_id=self.process_id)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("StatsStore exception caught during WriteStats(): %s",
                          e)

      logging.debug("Removing old stats from stats store." "")
      # Maximum time we keep stats store data is three days.
      stats_store_ttl = 60 * 60 * 24 * 3
      try:
        now = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
        self.stats_store.DeleteStats(
            process_id=self.process_id,
            timestamp=(0, now - stats_store_ttl * 1000000))
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "StatsStore exception caught during DeleteStats(): %s", e)

      time.sleep(self.sleep)

  def Run(self):
    self.RunAsync().join()

  def RunAsync(self):
    self.running_thread = threading.Thread(
        name=self.thread_name, target=self._RunLoop)
    self.running_thread.daemon = True
    self.running_thread.start()
    return self.running_thread


class StatsStoreInit(registry.InitHook):
  """Hook that inits global STATS_STORE object and stats store worker."""
  pre = [aff4.AFF4InitHook]

  def RunOnce(self):
    """Initializes StatsStore and StatsStoreWorker."""

    # SetUID is required to create and write to aff4:/stats_store
    token = access_control.ACLToken(username="GRRStatsStore").SetUID()

    global STATS_STORE
    STATS_STORE = aff4.FACTORY.Create(None, StatsStore, mode="w", token=token)
    try:
      STATS_STORE.Flush()
    except access_control.UnauthorizedAccess:
      logging.info("Not writing aff4:/stats_store due to lack of permissions.")

    # We don't need StatsStoreWorker if there's no StatsStore.process_id in
    # the config.
    stats_process_id = config.CONFIG["StatsStore.process_id"]
    if not stats_process_id:
      return

    stats_store_worker = StatsStoreWorker(STATS_STORE, stats_process_id)
    stats_store_worker.RunAsync()
