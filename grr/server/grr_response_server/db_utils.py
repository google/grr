#!/usr/bin/env python
"""Utility functions/decorators for DB implementations."""

import functools
import logging
import time

from grr.core.grr_response_core.lib import registry
from grr.core.grr_response_core.lib import stats
from grr.core.grr_response_core.lib import utils
from grr_response_server import db


def CallLoggedAndAccounted(f):
  """Decorator to log and account for a DB call."""

  @functools.wraps(f)
  def Decorator(*args, **kwargs):
    try:
      start_time = time.time()
      result = f(*args, **kwargs)
      latency = time.time() - start_time

      stats.STATS.RecordEvent(
          "db_request_latency", latency, fields=[f.__name__])
      logging.debug("DB request %s SUCCESS (%.3fs)", f.__name__, latency)

      return result
    except db.Error as e:
      stats.STATS.IncrementCounter(
          "db_request_errors", fields=[f.__name__, "grr"])
      logging.debug("DB request %s GRR ERROR: %s", f.__name__,
                    utils.SmartStr(e))
      raise
    except Exception as e:
      stats.STATS.IncrementCounter(
          "db_request_errors", fields=[f.__name__, "db"])
      logging.debug("DB request %s INTERNAL DB ERROR : %s", f.__name__,
                    utils.SmartStr(e))
      raise

  return Decorator


def ClientIdFromGrrMessage(m):
  if m.queue:
    return m.queue.Split()[0]
  if m.source:
    return m.source.Basename()


class DBMetricsInit(registry.InitHook):
  """Install database metrics."""

  def RunOnce(self):
    stats.STATS.RegisterEventMetric(
        "db_request_latency",
        fields=[("call", str)],
        bins=[0.05 * 1.2**x for x in range(30)])  # 50ms to ~10 seconds
    stats.STATS.RegisterCounterMetric(
        "db_request_errors", fields=[("call", str), ("type", str)])
