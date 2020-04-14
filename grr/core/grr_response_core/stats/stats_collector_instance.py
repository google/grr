#!/usr/bin/env python
# Lint as: python3
"""Contains a stats-collector singleton shared across a GRR process."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading

from grr_response_core.stats import stats_collector

_stats_singleton = None
_init_lock = threading.Lock()
_metadatas = []


class StatsNotInitializedError(Exception):

  def __init__(self):
    super().__init__("No StatsCollector has been initialized yet.")


def Set(collector: stats_collector.StatsCollector):
  """Initializes the StatsCollector singleton and registers metrics with it."""
  global _stats_singleton

  with _init_lock:
    if _stats_singleton is None:
      _stats_singleton = collector
      for metadata in _metadatas:
        _stats_singleton.RegisterMetric(metadata)
    else:
      # TODO(user): Throw an exception instead, once it is confirmed that it
      # is ok to do so.
      logging.warning("Tried to re-initialize global stats collector.")


def Get() -> stats_collector.StatsCollector:
  """Returns an initialized stats-collector.

  Raises:
    StatsNotInitializedError: If no stats-collector has been initialized yet.
  """
  if _stats_singleton is None:
    raise StatsNotInitializedError()
  return _stats_singleton


def RegisterMetric(metadata):
  """Registers a Metric with the StatsCollector."""
  with _init_lock:
    _metadatas.append(metadata)
    if _stats_singleton is not None:
      _stats_singleton.RegisterMetric(metadata)
