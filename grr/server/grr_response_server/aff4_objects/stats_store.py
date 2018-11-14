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
every time we write a new set of statistics data to the datastore. Metrics'
values themselves are stored as datastore row attributes.

Statistics is written to the data store by StatsStoreWorker. It periodically
fetches values for all the metrics and writes them to corresponding
object on AFF4.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store


class StatsStoreProcessData(aff4.AFF4Object):
  """Stores stats data for a particular process."""

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """Schema for StatsStoreProcessData."""

  def WriteStats(self, timestamp=None):
    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.StatsWriteMetrics(self.urn, timestamp=timestamp)
    self.Flush()  # Update indexes.

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

    subjects = [
        self.DATA_STORE_ROOT.Add(process_id) for process_id in process_ids
    ]
    return data_store.DB.StatsReadDataForProcesses(
        subjects, metric_name, timestamp=timestamp, limit=limit)

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


# Global StatsStore object
STATS_STORE = None


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
