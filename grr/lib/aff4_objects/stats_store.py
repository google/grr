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



import re
import threading
import time


import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import timeseries

from grr.lib.rdfvalues import structs

from grr.proto import jobs_pb2


class StatsStoreFieldValue(structs.RDFProtoStruct):
  """RDFValue definition for fields values to be stored in the data store."""

  protobuf = jobs_pb2.StatsStoreFieldValue

  @property
  def value(self):
    if self.field_type == stats.MetricFieldDefinition.FieldType.INT:
      value = self.int_value
    elif self.field_type == stats.MetricFieldDefinition.FieldType.STR:
      value = self.str_value
    else:
      raise ValueError("Internal inconsistency, invalid "
                       "field type %d." % self.field_type)

    return value

  def SetValue(self, value, field_type):
    if field_type == stats.MetricFieldDefinition.FieldType.INT:
      self.int_value = value
    elif field_type == stats.MetricFieldDefinition.FieldType.STR:
      self.str_value = value
    else:
      raise ValueError("Invalid field type %d." % field_type)

    self.field_type = field_type


class StatsStoreValue(structs.RDFProtoStruct):
  """RDFValue definition for stats values to be stored in the data store."""
  protobuf = jobs_pb2.StatsStoreValue

  @property
  def value(self):
    if self.value_type == stats.MetricMetadata.ValueType.INT:
      value = self.int_value
    elif self.value_type == stats.MetricMetadata.ValueType.FLOAT:
      value = self.float_value
    elif self.value_type == stats.MetricMetadata.ValueType.STR:
      value = self.str_value
    elif self.value_type == stats.MetricMetadata.ValueType.DISTRIBUTION:
      value = self.distribution_value
    else:
      raise ValueError("Internal inconsistency, invalid "
                       "value type %d." % self.value_type)

    return value

  def SetValue(self, value, value_type):
    if value_type == stats.MetricMetadata.ValueType.INT:
      self.int_value = value
    elif value_type == stats.MetricMetadata.ValueType.FLOAT:
      self.float_value = value
    elif value_type == stats.MetricMetadata.ValueType.STR:
      self.str_value = value
    elif value_type == stats.MetricMetadata.ValueType.DISTRIBUTION:
      self.distribution_value = value
    else:
      raise ValueError("Invalid value type %d." % value_type)

    self.value_type = value_type


class StatsStoreMetricsMetadata(structs.RDFProtoStruct):
  """Container with metadata for all the metrics in a given process."""

  protobuf = jobs_pb2.StatsStoreMetricsMetadata

  def AsDict(self):
    result = {}
    for metric in self.metrics:
      result[metric.varname] = metric

    return result


class StatsStoreProcessData(aff4.AFF4Object):
  """Stores stats data for a particular process."""

  STATS_STORE_PREFIX = "aff4:stats_store/"

  ALL_TIMESTAMPS = data_store.DataStore.ALL_TIMESTAMPS
  NEWEST_TIMESTAMP = data_store.DataStore.NEWEST_TIMESTAMP

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for StatsStoreProcessData."""

    METRICS_METADATA = aff4.Attribute(
        "aff4:stats_store_process_data/metrics_metadata",
        StatsStoreMetricsMetadata,
        creates_new_object_version=False,
        versioned=False)

  def WriteMetadataDescriptors(self,
                               metrics_metadata,
                               sync=False,
                               timestamp=None):
    current_metadata = self.Get(self.Schema.METRICS_METADATA,
                                default=StatsStoreMetricsMetadata())

    if current_metadata.AsDict() != metrics_metadata:
      store_metadata = StatsStoreMetricsMetadata(
          metrics=metrics_metadata.values())
      self.AddAttribute(self.Schema.METRICS_METADATA,
                        store_metadata,
                        age=timestamp)
      self.Flush(sync=sync)

  def WriteStats(self, timestamp=None, sync=False):
    to_set = {}
    metrics_metadata = stats.STATS.GetAllMetricsMetadata()
    self.WriteMetadataDescriptors(metrics_metadata,
                                  timestamp=timestamp,
                                  sync=sync)

    for name, metadata in metrics_metadata.iteritems():
      if metadata.fields_defs:
        for fields_values in stats.STATS.GetMetricFields(name):
          value = stats.STATS.GetMetricValue(name, fields=fields_values)

          store_value = StatsStoreValue()
          store_fields_values = []
          for field_def, field_value in zip(metadata.fields_defs,
                                            fields_values):
            store_field_value = StatsStoreFieldValue()
            store_field_value.SetValue(field_value, field_def.field_type)
            store_fields_values.append(store_field_value)

          store_value.fields_values = store_fields_values
          store_value.SetValue(value, metadata.value_type)

          to_set.setdefault(self.STATS_STORE_PREFIX + name,
                            []).append(store_value)
      else:
        value = stats.STATS.GetMetricValue(name)
        store_value = StatsStoreValue()
        store_value.SetValue(value, metadata.value_type)

        to_set[self.STATS_STORE_PREFIX + name] = [store_value]

    # Write actual data
    data_store.DB.MultiSet(self.urn,
                           to_set,
                           replace=False,
                           token=self.token,
                           timestamp=timestamp,
                           sync=sync)

  def DeleteStats(self, timestamp=ALL_TIMESTAMPS, sync=False):
    """Deletes all stats in the given time range."""

    if timestamp == self.NEWEST_TIMESTAMP:
      raise ValueError("Can't use NEWEST_TIMESTAMP in DeleteStats.")

    predicates = []
    for key in stats.STATS.GetAllMetricsMetadata().keys():
      predicates.append(self.STATS_STORE_PREFIX + key)

    start = None
    end = None
    if timestamp and timestamp != self.ALL_TIMESTAMPS:
      start, end = timestamp

    data_store.DB.DeleteAttributes(self.urn,
                                   predicates,
                                   start=start,
                                   end=end,
                                   token=self.token,
                                   sync=sync)


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

  def WriteStats(self, process_id=None, timestamp=None, sync=False):
    """Writes current stats values to the data store with a given timestamp."""
    if not process_id:
      raise ValueError("process_id can't be None")

    process_data = aff4.FACTORY.Create(
        self.urn.Add(process_id),
        StatsStoreProcessData,
        mode="rw",
        token=self.token)
    process_data.WriteStats(timestamp=timestamp, sync=sync)

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

    subjects = [self.DATA_STORE_ROOT.Add(process_id)
                for process_id in process_ids]
    subjects_data = aff4.FACTORY.MultiOpen(subjects,
                                           mode="r",
                                           token=self.token,
                                           aff4_type=StatsStoreProcessData)

    results = {}
    for subject_data in subjects_data:
      results[subject_data.urn.Basename()] = subject_data.Get(
          subject_data.Schema.METRICS_METADATA).AsDict()

    for process_id in process_ids:
      results.setdefault(process_id, {})

    return results

  def ReadStats(self,
                process_id=None,
                metric_name=None,
                timestamp=ALL_TIMESTAMPS,
                limit=10000):
    """Reads stats values from the data store for the current process."""
    if not process_id:
      raise ValueError("process_id can't be None")

    results = self.MultiReadStats(process_ids=[process_id],
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

    subjects = [self.DATA_STORE_ROOT.Add(process_id)
                for process_id in process_ids]

    multi_query_results = data_store.DB.MultiResolvePrefix(
        subjects,
        StatsStoreProcessData.STATS_STORE_PREFIX + (metric_name or ""),
        token=self.token,
        timestamp=timestamp,
        limit=limit)

    results = {}
    for subject, subject_results in multi_query_results:
      subject = rdfvalue.RDFURN(subject)
      subject_results = sorted(subject_results, key=lambda x: x[2])
      subject_metadata = multi_metadata.get(subject.Basename(), {})

      part_results = {}
      for predicate, value_string, timestamp in subject_results:
        metric_name = predicate[len(StatsStoreProcessData.STATS_STORE_PREFIX):]

        try:
          metadata = subject_metadata[metric_name]
        except KeyError:
          continue

        stored_value = StatsStoreValue(value_string)

        fields_values = []
        if metadata.fields_defs:
          for stored_field_value in stored_value.fields_values:
            fields_values.append(stored_field_value.value)

          current_dict = part_results.setdefault(metric_name, {})
          for field_value in fields_values[:-1]:
            new_dict = {}
            current_dict.setdefault(field_value, new_dict)
            current_dict = new_dict

          result_values_list = current_dict.setdefault(fields_values[-1], [])
        else:
          result_values_list = part_results.setdefault(metric_name, [])

        result_values_list.append((stored_value.value, timestamp))

      results[subject.Basename()] = part_results

    return results

  def DeleteStats(self, process_id=None, timestamp=ALL_TIMESTAMPS, sync=False):
    """Deletes all stats in the given time range."""

    if not process_id:
      raise ValueError("process_id can't be None")

    process_data = aff4.FACTORY.Create(
        self.urn.Add(process_id),
        StatsStoreProcessData,
        mode="w",
        token=self.token)
    process_data.DeleteStats(timestamp=timestamp, sync=sync)


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
          raise ValueError("Can't treat complext type as simple value: %s" %
                           value)
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
    self.sleep = sleep or config_lib.CONFIG["StatsStore.write_interval"]

  def _RunLoop(self):
    while True:
      logging.debug("Writing stats to stats store.")

      try:
        self.stats_store.WriteStats(process_id=self.process_id, sync=False)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("StatsStore exception caught during WriteStats(): %s",
                          e)

      logging.debug("Removing old stats from stats store." "")
      try:
        now = rdfvalue.RDFDatetime().Now().AsMicroSecondsFromEpoch()
        self.stats_store.DeleteStats(
            process_id=self.process_id,
            timestamp=(0, now - config_lib.CONFIG["StatsStore.ttl"] * 1000000),
            sync=False)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "StatsStore exception caught during DeleteStats(): %s", e)

      time.sleep(self.sleep)

  def Run(self):
    self.RunAsync().join()

  def RunAsync(self):
    self.running_thread = threading.Thread(name=self.thread_name,
                                           target=self._RunLoop)
    self.running_thread.daemon = True
    self.running_thread.start()
    return self.running_thread


class StatsStoreInit(registry.InitHook):
  """Hook that inits global STATS_STORE object and stats store worker."""
  pre = ["AFF4InitHook"]

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
    stats_process_id = config_lib.CONFIG["StatsStore.process_id"]
    if not stats_process_id:
      return

    stats_store_worker = StatsStoreWorker(STATS_STORE, stats_process_id)
    stats_store_worker.RunAsync()
