#!/usr/bin/env python
"""In-memory implementation of DB methods for handling server metrics."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from future.builtins import int
from future.utils import iteritems
from future.utils import itervalues

from typing import Iterable, Optional, Text, Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_server import db
from grr_response_server import db_utils
from grr_response_server import stats_values

# Type alias representing a time-range.
_TimeRange = Tuple[rdfvalue.RDFDatetime, rdfvalue.RDFDatetime]



def _IsOutsideTimeRange(timestamp,
                        time_range = None):
  """Returns a boolean indicating whether a timestamp is in a given range."""
  return time_range is not None and (timestamp < time_range[0] or
                                     timestamp > time_range[1])


class InMemoryDBStatsMixin(object):
  """Mixin providing an in-memory implementation of stats-related DB logic.

  Attributes:
    stats_store_entries: A dict mapping stats-entry ids to serialized
      StatsStoreEntries. This field is initialized in mem.py, for consistency
      with other in-memory DB mixins.
  """

  @utils.Synchronized
  def WriteStatsStoreEntries(
      self, stats_entries):
    """See db.Database."""
    for stats_entry in stats_entries:
      entry_id = db_utils.GenerateStatsEntryId(stats_entry)
      if entry_id in self.stats_store_entries:
        raise db.DuplicateMetricValueError()
      self.stats_store_entries[entry_id] = stats_entry.SerializeToString()

  @utils.Synchronized
  def ReadStatsStoreEntries(
      self,
      process_id_prefix,
      metric_name,
      time_range = None,
      max_results = 0):
    """See db.Database."""
    stats_entries = []
    for serialized_stats_entry in itervalues(self.stats_store_entries):
      stats_entry = stats_values.StatsStoreEntry.FromSerializedString(
          serialized_stats_entry)
      if (not stats_entry.process_id.startswith(process_id_prefix) or
          stats_entry.metric_name != metric_name or
          _IsOutsideTimeRange(stats_entry.timestamp, time_range)):
        continue

      stats_entries.append(stats_entry)
      if max_results and len(stats_entries) >= max_results:
        break
    return stats_entries

  @utils.Synchronized
  def DeleteStatsStoreEntriesOlderThan(self, cutoff,
                                       limit):
    """See db.Database."""
    entries_to_delete = []
    for entry_id, serialized_stats_entry in iteritems(self.stats_store_entries):
      stats_entry = stats_values.StatsStoreEntry.FromSerializedString(
          serialized_stats_entry)
      if stats_entry.timestamp < cutoff:
        entries_to_delete.append(entry_id)
      if len(entries_to_delete) >= limit:
        break
    for entry_id in entries_to_delete:
      del self.stats_store_entries[entry_id]
    return len(entries_to_delete)
