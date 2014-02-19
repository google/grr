#!/usr/bin/env python
"""Storage implementation for gathered statistics."""



import threading
import time


import logging

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats


config_lib.DEFINE_string("StatsStore.process_id", default="",
                         help="Id used to identify stats data of the current "
                         "process. This should be different for different GRR "
                         "processes. I.e. if you have 4 workers, for every "
                         "worker the subject should be different. For example: "
                         "worker_1, worker_2, worker_3, worker_4.")

config_lib.DEFINE_integer("StatsStore.write_interval", default=60,
                          help="Time in seconds between the dumps of stats "
                          "data into the stats store.")

config_lib.DEFINE_integer("StatsStore.ttl", default=60 * 60 * 24 * 7,
                          help="Maximum lifetime (in seconds) of data in the "
                          "stats store. Default is one week.")


class StatsStore(object):
  """Implementation of the long-term storage of collected stats data.

  This class allows to write current stats data to the data store, read
  and delete them. StatsStore uses data_store to store the data.
  All historical stats data are stored in a single data store subject per
  process. By process we mean, for example: "admin UI", "worker #1",
  "worker #3", etc. Stats data are stored as subject's attributes.
  """

  DATA_STORE_ROOT = rdfvalue.RDFURN("aff4:/stats_store")
  STATS_STORE_PREFIX = "aff4:stats_store/"

  ALL_TIMESTAMPS = data_store.DataStore.ALL_TIMESTAMPS
  NEWEST_TIMESTAMP = data_store.DataStore.NEWEST_TIMESTAMP

  def __init__(self, token=None):
    """Constructor."""
    if not token:
      raise ValueError("token can't be None")

    self.token = token

  def WriteStats(self, process_id=None, timestamp=None, sync=False):
    """Writes current stats values to the data store with a given timestamp."""
    if not process_id:
      raise ValueError("process_id can't be None")

    subject = self.DATA_STORE_ROOT.Add(process_id)

    to_set = {}
    metrics_metadata = stats.STATS.GetAllMetricsMetadata()
    for name, metadata in metrics_metadata.iteritems():
      if metadata.fields_defs:
        # TODO(user): implement support for metrics with fields
        continue
      if metadata.metric_type == stats.MetricType.EVENT:
        # TODO(user): implement support for distributions
        continue

      to_set[self.STATS_STORE_PREFIX + name] = [
          stats.STATS.GetMetricValue(name)]

    # Write this to mark that this process_id was used
    data_store.DB.Set(
        self.DATA_STORE_ROOT, self.STATS_STORE_PREFIX + process_id,
        timestamp or rdfvalue.RDFDatetime().Now().AsMicroSecondsFromEpoch(),
        sync=sync, token=self.token)
    # Write actual data
    data_store.DB.MultiSet(subject, to_set, replace=False,
                           token=self.token, timestamp=timestamp, sync=sync)

  def ListUsedProcessIds(self):
    """List process ids that were used when saving data to stats store."""
    results = data_store.DB.ResolveRegex(self.DATA_STORE_ROOT,
                                         self.STATS_STORE_PREFIX + ".*",
                                         token=self.token)
    return [predicate[len(self.STATS_STORE_PREFIX):]
            for predicate, _, _ in results]

  def ReadStats(self, process_id=None, predicate_regex=".*",
                timestamp=ALL_TIMESTAMPS, limit=10000):
    """Reads stats values from the data store for the current process."""
    if not process_id:
      raise ValueError("process_id can't be None")

    results = self.MultiReadStats(process_ids=[process_id],
                                  predicate_regex=predicate_regex,
                                  timestamp=timestamp, limit=limit)
    try:
      return results[process_id]
    except KeyError:
      return {}

  def MultiReadStats(self, process_ids=None, predicate_regex=".*",
                     timestamp=ALL_TIMESTAMPS, limit=10000):
    """Reads historical data for multiple process ids at once."""
    if not process_ids:
      process_ids = self.ListUsedProcessIds()

    subjects = [self.DATA_STORE_ROOT.Add(process_id)
                for process_id in process_ids]

    results = {}
    multi_query_results = data_store.DB.MultiResolveRegex(
        subjects, self.STATS_STORE_PREFIX + predicate_regex,
        token=self.token, timestamp=timestamp, limit=limit)
    for subject, subject_results in multi_query_results:
      subject_results = sorted(subject_results, key=lambda x: x[2])

      part_results = {}
      metrics_metadata = stats.STATS.GetAllMetricsMetadata()
      for predicate, value_string, timestamp in subject_results:
        metric_name = predicate[len(self.STATS_STORE_PREFIX):]

        try:
          metadata = metrics_metadata[metric_name]
        except KeyError:
          continue

        part_results.setdefault(metric_name, []).append(
            (metadata.value_type(value_string), timestamp))

      results[rdfvalue.RDFURN(subject).Basename()] = part_results

    return results

  def DeleteStats(self, process_id=None, timestamp=ALL_TIMESTAMPS,
                  sync=False):
    """Deletes all stats in the given time range."""
    if not process_id:
      raise ValueError("process_id can't be None")
    if timestamp == self.NEWEST_TIMESTAMP:
      raise ValueError("Can't use NEWEST_TIMESTAMP in DeleteStats.")

    subject = self.DATA_STORE_ROOT.Add(process_id)

    predicates = [self.STATS_STORE_PREFIX + key
                  for key in stats.STATS.GetAllMetricsMetadata().keys()]
    start = None
    end = None
    if timestamp and timestamp != self.ALL_TIMESTAMPS:
      start, end = timestamp

    data_store.DB.DeleteAttributes(subject, predicates, start=start,
                                   end=end, token=self.token, sync=sync)

  def RemoveEmptyProcessIds(self):
    to_delete = []
    for process_id in self.ListUsedProcessIds():
      data = self.ReadStats(process_id=process_id)
      if not data:
        to_delete.append(self.STATS_STORE_PREFIX + process_id)

    data_store.DB.DeleteAttributes(self.DATA_STORE_ROOT, to_delete, sync=True,
                                   token=self.token)


# Global StatsStore object
STATS_STORE = None


class StatsStoreWorker(object):
  """StatsStoreWorker periodically dumps stats data into the stats store."""

  def __init__(self, stats_store, process_id, thread_name="grr_stats_saver",
               sleep=None):
    super(StatsStoreWorker, self).__init__()

    self.stats_store = stats_store
    self.process_id = process_id
    self.thread_name = thread_name
    self.sleep = sleep or config_lib.CONFIG["StatsStore.write_interval"]

  def _RunLoop(self):
    self.stats_store.RemoveEmptyProcessIds()

    while True:
      logging.debug("Writing stats to stats store.")

      try:
        self.stats_store.WriteStats(process_id=self.process_id, sync=False)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "StatsStore exception caught during WriteStats(): %s", e)

      logging.debug("Removing old stats from stats store.""")
      try:
        now = rdfvalue.RDFDatetime().Now().AsMicroSecondsFromEpoch()
        self.stats_store.DeleteStats(
            process_id=self.process_id,
            timestamp=(0, now -
                       config_lib.CONFIG["StatsStore.ttl"] * 1000),
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
  pre = ["DataStoreInit", "StatsInit"]

  def RunOnce(self):
    """Initializes StatsStore and StatsStoreWorker."""

    # We don't need StatsStore and StatsStoreWorker if there's no
    # StatsStore.process_id in the config.
    stats_process_id = config_lib.CONFIG["StatsStore.process_id"]
    if not stats_process_id:
      return

    global STATS_STORE
    STATS_STORE = StatsStore(token=access_control.ACLToken(
        username="grr-stats-store"))

    stats_store_worker = StatsStoreWorker(STATS_STORE, stats_process_id)
    stats_store_worker.RunAsync()
