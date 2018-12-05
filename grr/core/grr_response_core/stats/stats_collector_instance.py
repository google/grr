#!/usr/bin/env python
"""Contains a stats-collector singleton shared across a GRR process."""

from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import logging
import threading

from grr_response_core.stats import stats_collector

_stats_singleton = None
_init_lock = threading.Lock()


class StatsNotInitialized(Exception):

  def __init__(self):
    super(StatsNotInitialized,
          self).__init__("No stats-collector has been initialized yet.")


def Set(collector):
  """Initializes the stats-collector singleton."""
  global _stats_singleton

  with _init_lock:
    if _stats_singleton is None:
      _stats_singleton = collector
    else:
      # TODO(user): Throw an exception instead, once it is confirmed that it
      # is ok to do so.
      logging.warning("Tried to re-initialize global stats collector.")


def Get():
  """Returns an initialized stats-collector.

  Raises:
    StatsNotInitialized: If no stats-collector has been initialized yet.
  """
  if _stats_singleton is None:
    raise StatsNotInitialized()
  return _stats_singleton
