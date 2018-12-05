#!/usr/bin/env python
"""MySQL implementation of DB methods for handling server metrics."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from future.builtins import int

from typing import Iterable, Optional, Text, Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_server import stats_values

# Type alias representing a time-range.
_TimeRange = Tuple[rdfvalue.RDFDatetime, rdfvalue.RDFDatetime]



# TODO(user): Implement methods for this mixin.
class MySQLDBStatsMixin(object):
  """Mixin providing an F1 implementation of stats-related DB logic."""

  def WriteStatsStoreEntries(
      self, stats_entries):
    """See db.Database."""
    raise NotImplementedError()

  def ReadStatsStoreEntries(
      self,
      process_id_prefix,
      metric_name,
      time_range = None,
      max_results = 0):
    """See db.Database."""
    raise NotImplementedError()

  def DeleteStatsStoreEntriesOlderThan(self, cutoff,
                                       limit):
    """See db.Database."""
    raise NotImplementedError()
